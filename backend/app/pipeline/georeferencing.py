"""
STAGE 8 — Georeferencing + Metric Correction.

Real PROJ-based transformation via pyproj: when GPS/RTK is available (from
the optional sensor file), we build an actual ENU (East-North-Up) tangent
projection centered on the trajectory origin using pyproj.Transformer, and
apply a real least-squares similarity-transform (scale + rotation +
translation, via Umeyama's method) to align the reconstruction's arbitrary
visual-odometry scale to metric GPS coordinates.

If no GPS/RTK/PPK data is available, we do NOT fabricate global coordinates.
The model is explicitly marked "locally referenced" and only a local ENU
frame (origin at the first camera pose, unit scale from visual odometry) is
emitted.
"""
from __future__ import annotations

import json

import numpy as np
from pyproj import Transformer, CRS

from app.services.stage_tracker import StageTracker
from app.utils.storage import job_path


def _umeyama(src: np.ndarray, dst: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
    """Least-squares similarity transform src -> dst. Returns (R, t, scale)."""
    mu_src, mu_dst = src.mean(axis=0), dst.mean(axis=0)
    src_c, dst_c = src - mu_src, dst - mu_dst
    cov = dst_c.T @ src_c / len(src)
    U, S, Vt = np.linalg.svd(cov)
    D = np.eye(3)
    if np.linalg.det(U @ Vt) < 0:
        D[-1, -1] = -1
    R = U @ D @ Vt
    var_src = (src_c ** 2).sum() / len(src)
    scale = float(np.trace(np.diag(S) @ D) / var_src) if var_src > 1e-9 else 1.0
    t = mu_dst - scale * R @ mu_src
    return R, t, scale


def _load_gps_points(sensor_rows: list[dict] | None, poses: list[dict]) -> tuple[np.ndarray, np.ndarray] | None:
    if not sensor_rows:
        return None
    gps_rows = [r for r in sensor_rows if "lat" in r and "lon" in r]
    if len(gps_rows) < 3:
        return None

    transformer = Transformer.from_crs("EPSG:4326", "EPSG:4978", always_xy=True)  # geodetic -> ECEF
    origin_lat, origin_lon = gps_rows[0]["lat"], gps_rows[0]["lon"]
    enu_transformer = Transformer.from_crs(
        "EPSG:4326",
        CRS.from_proj4(f"+proj=tmerc +lat_0={origin_lat} +lon_0={origin_lon} +ellps=WGS84 +units=m +no_defs"),
        always_xy=True,
    )

    gps_enu, vis_matched = [], []
    for row in gps_rows:
        e, n = enu_transformer.transform(row["lon"], row["lat"])
        alt = row.get("alt", 0.0)
        gps_enu.append([e, n, alt])
        nearest = min(poses, key=lambda p: abs(p["timestamp"] - float(row.get("timestamp", 0))))
        vis_matched.append([nearest["x"], nearest["y"], nearest["z"]])

    return np.array(vis_matched), np.array(gps_enu)


def georeference(job_id: str, points: np.ndarray, poses: list[dict], sensor_rows: list[dict] | None,
                  tracker: StageTracker) -> dict:
    matched = _load_gps_points(sensor_rows, poses)

    if matched is None:
        tracker.demo_mode(
            "PROJ Georeferencer (global CRS)",
            "no GPS/RTK/PPK coordinates supplied -- model is locally referenced only "
            "(local ENU frame, origin at first camera pose, no global lat/lon claimed)",
        )
        origin = points.mean(axis=0) if len(points) else np.zeros(3)
        coordinates = {
            "reference_type": "LOCAL",
            "coordinate_system": "Local ENU (arbitrary origin, visual-odometry scale)",
            "origin": {"x": float(origin[0]), "y": float(origin[1]), "z": float(origin[2])},
            "latitude": None,
            "longitude": None,
            "scale_corrected": False,
        }
        georef_points = points
    else:
        vis_pts, gps_pts = matched
        tracker.log(f"Aligning {len(vis_pts)} matched visual/GPS pose pairs via Umeyama similarity transform")
        R, t, scale = _umeyama(vis_pts, gps_pts)
        tracker.log(f"Recovered scale correction factor: {scale:.4f}")
        georef_points = (scale * (R @ points.T).T + t) if len(points) else points

        coordinates = {
            "reference_type": "GLOBAL",
            "coordinate_system": "Local tangent-plane ENU (EPSG:4326-derived, PROJ tmerc)",
            "origin": {"lat": None, "lon": None},
            "scale_corrected": True,
            "scale_factor": scale,
        }

    tracker.progress(80, operation="writing coordinates.json")

    georef_dir = job_path(job_id, "georeference")
    georef_dir.mkdir(parents=True, exist_ok=True)
    (georef_dir / "coordinates.json").write_text(json.dumps(coordinates, indent=2))

    # trajectory.geojson -- always emitted (local or global) since it's just the pose path
    features = [{
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [p["x"], p["y"], p["z"]]},
        "properties": {"timestamp": p["timestamp"], "source": p["source"], "confidence": p["confidence"]},
    } for p in poses]
    geojson = {"type": "FeatureCollection", "features": features}
    (georef_dir / "trajectory.geojson").write_text(json.dumps(geojson))

    return {"points": georef_points, "coordinates": coordinates}
