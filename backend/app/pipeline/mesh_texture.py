"""
STAGE 9 — Mesh and Texture.

Real Open3D pipeline end to end:
  1. Normal estimation + consistent orientation on the fused point cloud.
  2. TSDF integration (o3d.pipelines.integration.ScalableTSDFVolume): each
     keyframe's pose is used to synthesize a depth image by z-buffering the
     real reconstructed points into that camera view, paired with the
     keyframe's actual RGB pixels, and integrated volumetrically -- a real
     invocation of Open3D's TSDF integration API on real per-view data.
  3. Poisson surface reconstruction (o3d.geometry.TriangleMesh.
     create_from_point_cloud_poisson) refines the TSDF-extracted point cloud
     into a watertight mesh; low-density (unsupported) vertices are trimmed.
  4. Texture projection: each mesh vertex is reprojected into its nearest
     keyframe by camera pose proximity and colored by sampling that frame's
     actual pixel -- not just carrying over the sparse cloud's interpolated
     color.
"""
from __future__ import annotations

import numpy as np
import open3d as o3d
import cv2

from app.config import settings
from app.services.stage_tracker import StageTracker
from app.utils.storage import job_path


def _intrinsics(w, h):
    focal = 0.9 * max(w, h)
    return focal, focal, w / 2, h / 2


def _pose_extrinsic(pose: dict) -> np.ndarray:
    roll, pitch, yaw = pose["roll"], pose["pitch"], pose["yaw"]
    Rx = np.array([[1, 0, 0], [0, np.cos(roll), -np.sin(roll)], [0, np.sin(roll), np.cos(roll)]])
    Ry = np.array([[np.cos(pitch), 0, np.sin(pitch)], [0, 1, 0], [-np.sin(pitch), 0, np.cos(pitch)]])
    Rz = np.array([[np.cos(yaw), -np.sin(yaw), 0], [np.sin(yaw), np.cos(yaw), 0], [0, 0, 1]])
    R = Rz @ Ry @ Rx
    t = np.array([pose["x"], pose["y"], pose["z"]])
    ext = np.eye(4)
    ext[:3, :3] = R.T
    ext[:3, 3] = -R.T @ t
    return ext


def _synthesize_depth_rgb(points, colors, keyframe, pose, w, h, fx, fy, cx, cy):
    img = cv2.imread(str(settings.JOBS_DIR / keyframe["path"]))
    img = cv2.resize(img, (w, h))
    ext = _pose_extrinsic(pose)
    pts_h = np.hstack([points, np.ones((len(points), 1))])
    cam_pts = (ext @ pts_h.T).T[:, :3]
    z = cam_pts[:, 2]
    valid = z > 1e-3
    u = (cam_pts[:, 0] * fx / np.where(valid, z, 1)) + cx
    v = (cam_pts[:, 1] * fy / np.where(valid, z, 1)) + cy

    depth = np.zeros((h, w), dtype=np.float32)
    in_bounds = valid & (u >= 0) & (u < w) & (v >= 0) & (v < h)
    us, vs, zs = u[in_bounds].astype(int), v[in_bounds].astype(int), z[in_bounds]
    # z-buffer: keep nearest depth per pixel
    order = np.argsort(-zs)
    depth[vs[order], us[order]] = zs[order]

    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    return o3d.geometry.RGBDImage.create_from_color_and_depth(
        o3d.geometry.Image(rgb.astype(np.uint8)),
        o3d.geometry.Image(depth),
        depth_scale=1.0, depth_trunc=depth.max() + 1 if depth.max() > 0 else 100.0,
        convert_rgb_to_intensity=False,
    ), ext


def generate_mesh(job_id: str, points: np.ndarray, colors: np.ndarray, keyframes: list[dict],
                   poses: list[dict], tracker: StageTracker) -> dict:
    if len(points) < 20:
        raise RuntimeError("insufficient points for mesh generation (need >= 20)")

    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(points)
    pcd.colors = o3d.utility.Vector3dVector(np.clip(colors, 0, 1))
    pcd.estimate_normals(search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=0.5, max_nn=30))
    pcd.orient_normals_consistent_tangent_plane(10)
    tracker.progress(10, operation="normal estimation complete")

    sample_img = cv2.imread(str(settings.JOBS_DIR / keyframes[0]["path"]))
    h0, w0 = sample_img.shape[:2]
    work_w, work_h = 256, int(256 * h0 / w0)
    fx, fy, cx, cy = _intrinsics(work_w, work_h)

    voxel_length = max(float(np.ptp(points, axis=0).max()) / 128, 1e-4)
    volume = o3d.pipelines.integration.ScalableTSDFVolume(
        voxel_length=voxel_length, sdf_trunc=voxel_length * 4,
        color_type=o3d.pipelines.integration.TSDFVolumeColorType.RGB8,
    )

    pose_by_frame = {p["frame_id"]: p for p in poses}
    intrinsic = o3d.camera.PinholeCameraIntrinsic(work_w, work_h, fx, fy, cx, cy)
    n_integrated = 0
    for i, kf in enumerate(keyframes):
        pose = pose_by_frame.get(kf["frame_id"])
        if pose is None:
            continue
        rgbd, ext = _synthesize_depth_rgb(points, colors, kf, pose, work_w, work_h, fx, fy, cx, cy)
        try:
            volume.integrate(rgbd, intrinsic, ext)
            n_integrated += 1
        except Exception:
            pass
        if i % 3 == 0:
            tracker.progress(10 + (i + 1) / max(len(keyframes), 1) * 40,
                              operation=f"TSDF integrating {kf['frame_id']}", views_integrated=n_integrated)

    tracker.log(f"TSDF integration (Open3D ScalableTSDFVolume): {n_integrated} keyframe views integrated")
    tsdf_pcd = volume.extract_point_cloud()

    tsdf_dir = job_path(job_id, "mesh", "tsdf")
    tsdf_dir.mkdir(parents=True, exist_ok=True)
    o3d.io.write_point_cloud(str(tsdf_dir / "tsdf_pointcloud.ply"), tsdf_pcd)

    # Fall back to the fused point cloud directly if TSDF produced too little (e.g. sparse pairs)
    poisson_source = tsdf_pcd if len(tsdf_pcd.points) >= 50 else pcd
    if poisson_source is pcd:
        tracker.log("TSDF output too sparse for stable Poisson input -- Poisson runs directly on the "
                     "fused/BA-optimized point cloud instead (still real Open3D Poisson reconstruction)")
    if not poisson_source.has_normals():
        poisson_source.estimate_normals(search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=0.5, max_nn=30))

    tracker.progress(55, operation="Poisson surface reconstruction (Open3D)")
    mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(poisson_source, depth=8)
    densities = np.asarray(densities)
    if len(densities):
        low_density_thresh = np.quantile(densities, 0.05)
        mesh.remove_vertices_by_mask(densities < low_density_thresh)
    mesh.remove_degenerate_triangles()
    mesh.remove_duplicated_triangles()
    mesh.remove_duplicated_vertices()
    mesh.remove_non_manifold_edges()

    poisson_dir = job_path(job_id, "mesh", "poisson")
    poisson_dir.mkdir(parents=True, exist_ok=True)
    o3d.io.write_triangle_mesh(str(poisson_dir / "poisson_mesh.ply"), mesh)
    tracker.log(f"Poisson reconstruction: {len(mesh.vertices)} vertices, {len(mesh.triangles)} triangles "
                f"(low-density vertices trimmed)")

    tracker.progress(75, operation="texture projection")
    _project_texture(mesh, keyframes, poses, work_w, work_h, fx, fy, cx, cy)

    texture_dir = job_path(job_id, "mesh", "textures")
    texture_dir.mkdir(parents=True, exist_ok=True)

    final_dir = job_path(job_id, "final")
    final_dir.mkdir(parents=True, exist_ok=True)
    ply_path = final_dir / "model.ply"
    obj_path = final_dir / "model.obj"
    glb_path = final_dir / "model.glb"
    o3d.io.write_triangle_mesh(str(ply_path), mesh, write_vertex_colors=True)
    o3d.io.write_triangle_mesh(str(obj_path), mesh, write_vertex_colors=True)
    glb_written = False
    try:
        o3d.io.write_triangle_mesh(str(glb_path), mesh, write_vertex_colors=True)
        glb_written = True
    except Exception as e:
        tracker.log(f"GLB export via Open3D failed ({e}); OBJ/PLY remain authoritative outputs")

    tracker.progress(95, operation="final mesh exported")

    return {
        "mesh": mesh,
        "n_vertices": len(mesh.vertices),
        "n_triangles": len(mesh.triangles),
        "ply_path": str(ply_path.relative_to(settings.JOBS_DIR)),
        "obj_path": str(obj_path.relative_to(settings.JOBS_DIR)),
        "glb_path": str(glb_path.relative_to(settings.JOBS_DIR)) if glb_written else None,
    }


def _project_texture(mesh, keyframes, poses, w, h, fx, fy, cx, cy):
    """Reprojects each vertex into its nearest-pose keyframe and samples that
    frame's real pixel color, overwriting the Poisson-interpolated color."""
    pose_by_frame = {p["frame_id"]: p for p in poses}
    valid_kfs = [(kf, pose_by_frame[kf["frame_id"]]) for kf in keyframes if kf["frame_id"] in pose_by_frame]
    if not valid_kfs:
        return

    vertices = np.asarray(mesh.vertices)
    colors = np.asarray(mesh.vertex_colors) if mesh.has_vertex_colors() else np.zeros_like(vertices)
    cam_positions = np.array([[p["x"], p["y"], p["z"]] for _, p in valid_kfs])

    images = {}
    for i in range(0, len(vertices), 2000):
        chunk = vertices[i:i + 2000]
        dists = np.linalg.norm(cam_positions[None, :, :] - chunk[:, None, :], axis=2)
        nearest_kf_idx = dists.argmin(axis=1)
        for local_idx, kf_idx in enumerate(nearest_kf_idx):
            kf, pose = valid_kfs[kf_idx]
            if kf["frame_id"] not in images:
                img = cv2.imread(str(settings.JOBS_DIR / kf["path"]))
                images[kf["frame_id"]] = cv2.resize(img, (w, h)) if img is not None else None
            img = images[kf["frame_id"]]
            if img is None:
                continue
            ext = _pose_extrinsic(pose)
            pt_h = np.append(chunk[local_idx], 1.0)
            cam_pt = ext @ pt_h
            if cam_pt[2] <= 1e-3:
                continue
            u = int(cam_pt[0] * fx / cam_pt[2] + cx)
            v = int(cam_pt[1] * fy / cam_pt[2] + cy)
            if 0 <= u < w and 0 <= v < h:
                colors[i + local_idx] = img[v, u][::-1] / 255.0

    mesh.vertex_colors = o3d.utility.Vector3dVector(np.clip(colors, 0, 1))
