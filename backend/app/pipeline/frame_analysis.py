"""
STAGE 2 — Frame Analysis.

Real per-frame quality scoring using OpenCV:
  - blur: variance of Laplacian
  - exposure: histogram-based over/under-exposure penalty
  - contrast: std-dev of grayscale intensities
  - compression/artifact: blockiness estimate from 8x8 DCT-grid gradient discontinuities

All scores are computed directly from pixel data -- nothing here is a stub.
"""
from __future__ import annotations

import csv
import json

import cv2
import numpy as np

from app.config import settings
from app.services.stage_tracker import StageTracker
from app.utils.storage import job_path


def _blur_score(gray: np.ndarray) -> float:
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def _exposure_score(gray: np.ndarray) -> float:
    hist = cv2.calcHist([gray], [0], None, [256], [0, 256]).flatten()
    hist = hist / (hist.sum() + 1e-9)
    underexposed = hist[:10].sum()
    overexposed = hist[246:].sum()
    penalty = underexposed + overexposed
    return float(max(0.0, 1.0 - penalty * 4))


def _contrast_score(gray: np.ndarray) -> float:
    return float(gray.std())


def _compression_score(gray: np.ndarray) -> float:
    """Blockiness heuristic: mean gradient discontinuity at 8-pixel block boundaries
    vs. interior gradients. Lower ratio (closer to 1) = fewer compression artifacts."""
    h, w = gray.shape
    gx = np.abs(np.diff(gray.astype(np.float32), axis=1))
    if w < 16 or h < 16:
        return 1.0
    boundary_cols = gx[:, 7:w - 1:8]
    interior_cols = np.delete(gx, np.arange(7, w - 1, 8), axis=1)
    boundary_energy = boundary_cols.mean() if boundary_cols.size else 0.0
    interior_energy = interior_cols.mean() if interior_cols.size else 1e-6
    ratio = boundary_energy / (interior_energy + 1e-6)
    # ratio significantly > 1 indicates blocking artifacts
    score = float(max(0.0, min(1.0, 2.0 - ratio)))
    return score


def analyze_frames(job_id: str, frames: list[dict], tracker: StageTracker) -> list[dict]:
    report_rows = []
    n = len(frames)
    blur_vals = []

    for i, frame in enumerate(frames):
        path = settings.JOBS_DIR / frame["path"]
        img = cv2.imread(str(path))
        if img is None:
            continue
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        blur = _blur_score(gray)
        exposure = _exposure_score(gray)
        contrast = _contrast_score(gray)
        compression = _compression_score(gray)
        blur_vals.append(blur)

        row = {**frame, "blur_score": blur, "exposure_score": exposure,
               "contrast_score": contrast, "compression_score": compression}
        report_rows.append(row)

        if i % 20 == 0 or i == n - 1:
            tracker.progress(
                (i + 1) / max(n, 1) * 90,
                operation=f"scoring {frame['frame_id']}",
                frames_processed=i + 1,
            )

    # Normalize blur relative to this video's own distribution (blur variance scale differs per scene)
    if blur_vals:
        blur_p95 = float(np.percentile(blur_vals, 95)) or 1.0
    else:
        blur_p95 = 1.0

    for row in report_rows:
        blur_norm = min(1.0, row["blur_score"] / blur_p95)
        quality = (
            0.4 * blur_norm +
            0.25 * row["exposure_score"] +
            0.20 * min(1.0, row["contrast_score"] / 64.0) +
            0.15 * row["compression_score"]
        )
        row["quality_score"] = round(float(quality), 4)
        row["selected"] = quality >= settings.QUALITY_REJECT_THRESHOLD

    out_dir = job_path(job_id, "frames", "quality")
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "frame_quality.json", "w") as f:
        json.dump(report_rows, f, indent=2)
    with open(out_dir / "frame_quality.csv", "w", newline="") as f:
        if report_rows:
            writer = csv.DictWriter(f, fieldnames=list(report_rows[0].keys()))
            writer.writeheader()
            writer.writerows(report_rows)

    rejected = sum(1 for r in report_rows if not r["selected"])
    tracker.log(f"Frame analysis complete: {len(report_rows)} scored, {rejected} rejected below quality threshold")
    return report_rows
