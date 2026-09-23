"""STAGE 10 — Final Output / report.json (spec section 29)."""
from __future__ import annotations

import json
import time

from app.utils.storage import job_path
from app.utils.device import DEVICE


def generate_report(job_id: str, context: dict) -> dict:
    vm = context["video_metadata"]
    report = {
        "input": {
            "resolution": f"{vm['width']}x{vm['height']}",
            "duration_s": vm["duration"],
            "fps": vm["fps"],
            "codec": vm["codec"],
        },
        "processing": {
            "frames_extracted": context["n_frames"],
            "frames_rejected": context["n_frames"] - context["n_selected_frames"],
            "keyframes": context["n_keyframes"],
            "dynamic_objects_detected": context["n_dynamic_detected"],
            "dynamic_objects_tracked": context["n_dynamic_tracked"],
            "dynamic_objects_dynamic": context["n_dynamic_dynamic"],
        },
        "reconstruction": {
            "raw_point_count": context["n_raw_points"],
            "fused_point_count": context["n_fused_points"],
            "mesh_vertices": context["n_vertices"],
            "mesh_triangles": context["n_triangles"],
            "confidence_tier_counts": context["tier_counts"],
        },
        "georeferencing": {
            "reference_type": context["coordinates"]["reference_type"],
            "coordinate_system": context["coordinates"]["coordinate_system"],
            "gps_available": context["coordinates"]["reference_type"] == "GLOBAL",
            "rtk_available": context.get("rtk_available", False),
        },
        "performance": {
            "total_time_s": round(time.time() - context["job_start_time"], 2),
            "per_stage_time_s": context["per_stage_time"],
            "gpu": {"cuda_available": DEVICE.cuda_available, "gpu_name": DEVICE.gpu_name},
            "cpu": DEVICE.cpu,
        },
        "demo_mode_components": context.get("demo_mode_components", []),
    }
    out_dir = job_path(job_id, "final")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "report.json").write_text(json.dumps(report, indent=2))
    return report
