"""Artifact directory layout for a reconstruction job (see docs/ARCHITECTURE.md section 22)."""
from pathlib import Path

from app.config import settings

ARTIFACT_SUBDIRS = [
    "video",
    "metadata",
    "frames",
    "frames/quality",
    "keyframes",
    "pose",
    "dynamic/detections",
    "dynamic/masks",
    "dynamic/tracks",
    "dynamic/dynamic_layer",
    "depth",
    "vggt",
    "speed3r",
    "mvs",
    "pointcloud/raw",
    "pointcloud/fused",
    "optimization/bundle_adjustment",
    "optimization/factor_graph",
    "georeference",
    "mesh/tsdf",
    "mesh/poisson",
    "mesh/textures",
    "confidence",
    "final",
    "logs",
]


def create_job_tree(job_id: str) -> Path:
    root = settings.job_dir(job_id)
    for sub in ARTIFACT_SUBDIRS:
        (root / sub).mkdir(parents=True, exist_ok=True)
    return root


def job_path(job_id: str, *parts: str) -> Path:
    return settings.job_dir(job_id).joinpath(*parts)


def safe_filename(filename: str) -> str:
    """Strip path components / unsafe characters to prevent path traversal."""
    name = Path(filename).name
    name = "".join(c for c in name if c.isalnum() or c in "._-")
    return name or "upload"
