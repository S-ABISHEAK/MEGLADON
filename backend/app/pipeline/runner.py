"""
Pipeline orchestrator: chains Stage 1 -> Stage 10, persisting each stage's
output to the DB and to the job's artifact directory, and driving the
ProcessingStage state machine (spec section 21). Runs synchronously inside
an RQ worker process (see app/workers/queue.py) so the API stays responsive.
"""
from __future__ import annotations

import time
import numpy as np

from app.config import settings
from app.database import SessionLocal
from app.models.job import ReconstructionJob, VideoMetadata, JobStatus, OutputArtifact
from app.models.frame import Frame, Keyframe
from app.models.pose import Pose
from app.models.dynamic_object import DynamicObject
from app.services.stage_tracker import StageTracker
from app.services.event_bus import publish_event

from app.pipeline.video_processing import extract_frames
from app.pipeline.frame_analysis import analyze_frames
from app.pipeline.keyframe_selection import select_keyframes
from app.pipeline.pose_estimation import estimate_pose, _load_sensor_file
from app.pipeline.dynamic_objects import handle_dynamic_objects
from app.pipeline.ai_reconstruction import reconstruct
from app.pipeline.fusion_optimization import fuse_and_optimize
from app.pipeline.georeferencing import georeference
from app.pipeline.mesh_texture import generate_mesh
from app.pipeline.final_report import generate_report


def _record_artifact(db, job_id, type_, path, metadata=None):
    art = OutputArtifact(job_id=job_id, type=type_, path=path, artifact_metadata=metadata or {})
    db.add(art)
    db.commit()


def run_pipeline(job_id: str, resume_from: str | None = None):
    db = SessionLocal()
    job_start = time.time()
    per_stage_time: dict[str, float] = {}
    demo_components: list[str] = []

    try:
        job = db.query(ReconstructionJob).get(job_id)
        vm = db.query(VideoMetadata).filter_by(job_id=job_id).first()
        video_path = str(settings.job_dir(job_id) / "video" / job.filename)

        # STAGE 1 — Video Processing
        t0 = time.time()
        t = StageTracker(db, job_id, "VIDEO_PROCESSING")
        t.start("streaming frame extraction (ffmpeg)")
        frames = extract_frames(video_path, job_id, t)
        for f in frames:
            db.add(Frame(job_id=job_id, frame_id=f["frame_id"], timestamp=f["timestamp"], path=f["path"]))
        db.commit()
        t.complete(frames_extracted=len(frames))
        per_stage_time["VIDEO_PROCESSING"] = round(time.time() - t0, 2)

        # STAGE 2 — Frame Analysis
        t0 = time.time()
        t = StageTracker(db, job_id, "FRAME_ANALYSIS")
        t.start("scoring blur/exposure/contrast/compression")
        scored = analyze_frames(job_id, frames, t)
        db.query(Frame).filter_by(job_id=job_id).delete()
        for f in scored:
            db.add(Frame(job_id=job_id, frame_id=f["frame_id"], timestamp=f["timestamp"], path=f["path"],
                          blur_score=f["blur_score"], exposure_score=f["exposure_score"],
                          contrast_score=f["contrast_score"], compression_score=f["compression_score"],
                          quality_score=f["quality_score"], selected=f["selected"]))
        db.commit()
        n_selected = sum(1 for f in scored if f["selected"])
        t.complete(frames_scored=len(scored), frames_selected=n_selected)
        _record_artifact(db, job_id, "frame_quality_report", f"{job_id}/frames/quality/frame_quality.json")
        per_stage_time["FRAME_ANALYSIS"] = round(time.time() - t0, 2)

        # STAGE 3 — Keyframe Selection
        t0 = time.time()
        t = StageTracker(db, job_id, "KEYFRAME_SELECTION")
        t.start("ORB similarity + motion + overlap analysis")
        keyframes = select_keyframes(job_id, scored, t)
        if len(keyframes) < 2:
            raise RuntimeError(f"only {len(keyframes)} keyframes selected -- need >= 2 for reconstruction; "
                                f"try a longer/higher-motion source video")
        for k in keyframes:
            db.add(Keyframe(job_id=job_id, frame_id=k["frame_id"], path=k["path"], timestamp=k["timestamp"],
                             similarity=k["similarity_to_previous"], motion_score=k["motion_score"],
                             overlap_score=k["overlap_estimate"], selection_reason=k["selection_reason"]))
        db.commit()
        t.complete(keyframes_selected=len(keyframes))
        _record_artifact(db, job_id, "keyframes_manifest", f"{job_id}/keyframes/keyframes.json")
        per_stage_time["KEYFRAME_SELECTION"] = round(time.time() - t0, 2)

        # STAGE 4 — Camera Pose (Visual-Inertial SLAM + GPS/IMU/RTK)
        t0 = time.time()
        t = StageTracker(db, job_id, "POSE_ESTIMATION")
        t.start("visual odometry + sensor fusion")
        poses = estimate_pose(job_id, keyframes, job.sensor_file_path, t)
        for p in poses:
            db.add(Pose(job_id=job_id, timestamp=p["timestamp"], x=p["x"], y=p["y"], z=p["z"],
                         roll=p["roll"], pitch=p["pitch"], yaw=p["yaw"], source=p["source"],
                         confidence=p["confidence"]))
        db.commit()
        if job.sensor_file_path is None:
            demo_components.append("GPS/IMU/RTK SensorFusion (no sensor data supplied)")
        t.complete(poses_estimated=len(poses))
        _record_artifact(db, job_id, "trajectory", f"{job_id}/pose/trajectory.json")
        per_stage_time["POSE_ESTIMATION"] = round(time.time() - t0, 2)

        # STAGE 5 — Dynamic Object Handling
        t0 = time.time()
        t = StageTracker(db, job_id, "DYNAMIC_OBJECT_HANDLING")
        t.start("YOLOv8 detection -> segmentation -> tracking")
        dyn = handle_dynamic_objects(job_id, keyframes, t)
        for obj in dyn["tracks"].values():
            db.add(DynamicObject(job_id=job_id, object_id=obj["object_id"], cls=obj["class"],
                                  confidence=obj["confidence"], motion_status=obj["motion_status"],
                                  trajectory=obj["trajectory"], first_seen=obj["first_seen"],
                                  last_seen=obj["last_seen"]))
        db.commit()
        demo_components.append("SAM2 Segmenter (GrabCut-from-YOLO-box demo)")
        t.complete(objects_detected=dyn["n_detected"], objects_tracked=dyn["n_tracked"],
                   objects_dynamic=dyn["n_dynamic"])
        _record_artifact(db, job_id, "dynamic_objects", f"{job_id}/dynamic/dynamic_objects.json")
        per_stage_time["DYNAMIC_OBJECT_HANDLING"] = round(time.time() - t0, 2)

        # STAGE 6 — AI 3D Reconstruction
        t0 = time.time()
        t = StageTracker(db, job_id, "AI_RECONSTRUCTION")
        t.start("multi-view triangulation + depth priors")
        recon = reconstruct(job_id, keyframes, poses, t)
        demo_components += ["Depth Anything V2 (network-restricted)", "VGGT-O (no installable distribution)",
                             "Speed3R (no installable distribution)"]
        t.complete(raw_points=len(recon["points"]))
        _record_artifact(db, job_id, "raw_pointcloud", f"{job_id}/pointcloud/raw/mvs_raw.ply")
        per_stage_time["AI_RECONSTRUCTION"] = round(time.time() - t0, 2)

        # STAGE 7 — 3D Fusion and Optimization
        t0 = time.time()
        t = StageTracker(db, job_id, "FUSION_OPTIMIZATION")
        t.start("Open3D fusion + bundle adjustment")
        fused = fuse_and_optimize(job_id, recon, t)
        t.complete(fused_points=len(fused["points"]), **fused["tier_counts"])
        _record_artifact(db, job_id, "fused_pointcloud", f"{job_id}/pointcloud/fused/fused_pointcloud.ply",
                          {"tier_counts": fused["tier_counts"]})
        per_stage_time["FUSION_OPTIMIZATION"] = round(time.time() - t0, 2)

        # STAGE 8 — Georeferencing
        t0 = time.time()
        t = StageTracker(db, job_id, "GEOREFERENCING")
        t.start("PROJ ENU conversion + scale correction")
        sensor_rows = _load_sensor_file(job.sensor_file_path)
        georef = georeference(job_id, fused["points"], poses, sensor_rows, t)
        t.complete(reference_type=georef["coordinates"]["reference_type"])
        _record_artifact(db, job_id, "coordinates", f"{job_id}/georeference/coordinates.json")
        per_stage_time["GEOREFERENCING"] = round(time.time() - t0, 2)

        # STAGE 9 — Mesh and Texture
        t0 = time.time()
        t = StageTracker(db, job_id, "MESH_TEXTURE")
        t.start("TSDF integration -> Poisson -> texture projection")
        mesh_out = generate_mesh(job_id, georef["points"], fused["colors"], keyframes, poses, t)
        t.complete(vertices=mesh_out["n_vertices"], triangles=mesh_out["n_triangles"])
        _record_artifact(db, job_id, "model_ply", f"{job_id}/final/model.ply")
        _record_artifact(db, job_id, "model_obj", f"{job_id}/final/model.obj")
        if mesh_out["glb_path"]:
            _record_artifact(db, job_id, "model_glb", f"{job_id}/final/model.glb")
        per_stage_time["MESH_TEXTURE"] = round(time.time() - t0, 2)

        # STAGE 10 — Final Output
        t0 = time.time()
        t = StageTracker(db, job_id, "FINAL_OUTPUT")
        t.start("generating final report")
        report = generate_report(job_id, {
            "video_metadata": {"width": vm.width, "height": vm.height, "duration": vm.duration,
                                "fps": vm.fps, "codec": vm.codec},
            "n_frames": len(scored), "n_selected_frames": n_selected, "n_keyframes": len(keyframes),
            "n_dynamic_detected": dyn["n_detected"], "n_dynamic_tracked": dyn["n_tracked"],
            "n_dynamic_dynamic": dyn["n_dynamic"], "n_raw_points": len(recon["points"]),
            "n_fused_points": len(fused["points"]), "n_vertices": mesh_out["n_vertices"],
            "n_triangles": mesh_out["n_triangles"], "tier_counts": fused["tier_counts"],
            "coordinates": georef["coordinates"], "rtk_available": bool(sensor_rows),
            "job_start_time": job_start, "per_stage_time": per_stage_time,
            "demo_mode_components": demo_components,
        })
        _record_artifact(db, job_id, "final_report", f"{job_id}/final/report.json")
        t.complete(**report["reconstruction"])
        per_stage_time["FINAL_OUTPUT"] = round(time.time() - t0, 2)

        job.status = JobStatus.COMPLETED
        from datetime import datetime, timezone
        job.completed_at = datetime.now(timezone.utc)
        db.commit()
        publish_event(job_id, {"type": "job_completed", "report": report})

    except Exception as e:
        import traceback
        db.rollback()
        job = db.query(ReconstructionJob).get(job_id)
        if job:
            job.status = JobStatus.FAILED
            job.error = str(e)
            db.commit()
        publish_event(job_id, {"type": "job_failed", "error": str(e), "traceback": traceback.format_exc()})
        raise
    finally:
        db.close()
