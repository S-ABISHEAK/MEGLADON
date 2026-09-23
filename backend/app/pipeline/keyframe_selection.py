"""
STAGE 3 — Keyframe Selection.

Uses ORB feature descriptors (per spec: "ORB or SuperPoint only as
feature-analysis mechanisms") for real image-similarity comparison, plus
optical-flow-derived motion magnitude for motion analysis, and descriptor
inlier-ratio as an overlap proxy. Never blindly takes every Nth frame --
each candidate is evaluated against the *actually selected* previous
keyframe's content.
"""
from __future__ import annotations

import json

import cv2
import numpy as np

from app.config import settings
from app.services.stage_tracker import StageTracker
from app.utils.storage import job_path

_orb = cv2.ORB_create(nfeatures=800)
_bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)


def _load_gray(path):
    img = cv2.imread(str(path))
    if img is None:
        return None, None
    small = cv2.resize(img, (960, int(960 * img.shape[0] / img.shape[1])))
    return small, cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)


def _similarity_and_overlap(gray_a, gray_b) -> tuple[float, float]:
    """Returns (similarity 0..1, overlap 0..1) from ORB matches between two frames."""
    kp_a, des_a = _orb.detectAndCompute(gray_a, None)
    kp_b, des_b = _orb.detectAndCompute(gray_b, None)
    if des_a is None or des_b is None or len(kp_a) < 8 or len(kp_b) < 8:
        return 0.0, 0.0
    matches = _bf.match(des_a, des_b)
    if not matches:
        return 0.0, 0.0
    good = [m for m in matches if m.distance < 50]
    match_ratio = len(good) / max(len(kp_a), len(kp_b), 1)
    similarity = float(min(1.0, match_ratio * 2.0))
    overlap = float(min(1.0, len(good) / max(min(len(kp_a), len(kp_b)), 1)))
    return similarity, overlap


def _motion_score(gray_a, gray_b) -> float:
    """Dense optical flow magnitude between consecutive candidate frames."""
    flow = cv2.calcOpticalFlowFarneback(gray_a, gray_b, None, 0.5, 3, 15, 3, 5, 1.2, 0)
    mag, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
    return float(mag.mean())


def select_keyframes(job_id: str, scored_frames: list[dict], tracker: StageTracker) -> list[dict]:
    candidates = [f for f in scored_frames if f.get("selected")]
    candidates.sort(key=lambda f: f["timestamp"])

    keyframes = []
    prev_gray = None
    prev_small = None
    out_dir = job_path(job_id, "keyframes")
    out_dir.mkdir(parents=True, exist_ok=True)

    n = len(candidates)
    for i, cand in enumerate(candidates):
        path = settings.JOBS_DIR / cand["path"]
        small, gray = _load_gray(path)
        if gray is None:
            continue

        if prev_gray is None:
            reason = "first_keyframe"
            similarity, overlap, motion = 0.0, 0.0, 0.0
            keep = True
        else:
            similarity, overlap = _similarity_and_overlap(prev_gray, gray)
            motion = _motion_score(prev_gray, gray)
            # keep when scene has changed enough (low similarity) but still has
            # sufficient overlap for reconstruction, or when motion indicates
            # meaningful viewpoint change (temporal-redundancy reduction)
            too_similar = similarity > settings.KEYFRAME_SIMILARITY_THRESHOLD
            insufficient_overlap = overlap < 0.05
            keep = (not too_similar) and (not insufficient_overlap)
            if too_similar:
                reason = "rejected_redundant"
            elif insufficient_overlap:
                reason = "rejected_insufficient_overlap"
            else:
                reason = "viewpoint_change" if motion > 1.0 else "quality_and_overlap_ok"

        if keep:
            dest = out_dir / f"keyframe_{len(keyframes) + 1:06d}.jpg"
            cv2.imwrite(str(dest), cv2.imread(str(path)))
            keyframes.append({
                "frame_id": cand["frame_id"],
                "timestamp": cand["timestamp"],
                "quality_score": cand["quality_score"],
                "similarity_to_previous": round(similarity, 4),
                "motion_score": round(motion, 4),
                "overlap_estimate": round(overlap, 4),
                "selection_reason": reason,
                "path": str(dest.relative_to(settings.JOBS_DIR)),
            })
            prev_gray, prev_small = gray, small

        if i % 10 == 0 or i == n - 1:
            tracker.progress(
                (i + 1) / max(n, 1) * 95,
                operation=f"evaluating {cand['frame_id']}",
                frames_processed=i + 1,
                keyframes_selected=len(keyframes),
            )

    with open(out_dir / "keyframes.json", "w") as f:
        json.dump(keyframes, f, indent=2)

    tracker.log(f"Selected {len(keyframes)} keyframes from {len(candidates)} quality-passed frames "
                f"using ORB similarity + Farneback motion + overlap analysis")
    return keyframes
