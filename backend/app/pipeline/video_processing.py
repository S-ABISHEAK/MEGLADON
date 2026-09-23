"""
STAGE 1 — Video Processing (FFmpeg + OpenCV).

Real ffprobe-based metadata extraction and real ffmpeg streaming frame
extraction. Never loads the whole 4K video into memory: ffmpeg writes
frames to disk directly, and this module only ever holds one frame's
metadata at a time.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from app.config import settings
from app.services.stage_tracker import StageTracker
from app.utils.storage import job_path


def probe_video(video_path: str) -> dict:
    cmd = [
        "ffprobe", "-v", "error", "-print_format", "json",
        "-show_format", "-show_streams", video_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "ffprobe failed")

    data = json.loads(result.stdout)
    video_stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), None)
    if video_stream is None:
        raise RuntimeError("no video stream found")

    fmt = data.get("format", {})
    num, den = (video_stream.get("avg_frame_rate", "0/1").split("/") + ["1"])[:2]
    fps = float(num) / float(den) if float(den or 1) != 0 else 0.0

    # GPS/IMU metadata is rarely embedded in consumer drone MP4s; check format tags honestly.
    tags = {**fmt.get("tags", {}), **video_stream.get("tags", {})}
    has_gps = "yes" if any("gps" in k.lower() or "location" in k.lower() for k in tags) else "no"

    return {
        "width": int(video_stream.get("width", 0)),
        "height": int(video_stream.get("height", 0)),
        "fps": round(fps, 3),
        "duration": float(fmt.get("duration", video_stream.get("duration", 0)) or 0),
        "codec": video_stream.get("codec_name", "unknown"),
        "bitrate": int(fmt.get("bit_rate", 0) or 0),
        "frame_count": int(video_stream.get("nb_frames", 0) or 0),
        "has_gps_metadata": has_gps,
    }


def extract_frames(
    video_path: str,
    job_id: str,
    tracker: StageTracker,
    sample_fps: float | None = None,
) -> list[dict]:
    """
    Stream frames from the video via ffmpeg at a configurable sampling rate
    (default settings.DEFAULT_FRAME_SAMPLE_FPS) rather than decoding every
    frame at full resolution. The original 4K source stays on disk untouched
    for later texture projection.
    """
    sample_fps = sample_fps or settings.DEFAULT_FRAME_SAMPLE_FPS
    out_dir = job_path(job_id, "frames")
    out_dir.mkdir(parents=True, exist_ok=True)
    pattern = str(out_dir / "frame_%06d.jpg")

    tracker.log(f"Extracting frames at {sample_fps} fps (streamed, original 4K source preserved)")

    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vf", f"fps={sample_fps}",
        "-qscale:v", "2",
        pattern,
    ]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in process.stdout:
        if "frame=" in line:
            tracker.progress(min(95.0, tracker.row.progress + 0.5), operation=line.strip()[-80:])
    process.wait()
    if process.returncode != 0:
        raise RuntimeError("ffmpeg frame extraction failed")

    frame_files = sorted(out_dir.glob("frame_*.jpg"))
    frames = []
    for idx, f in enumerate(frame_files):
        frames.append({
            "frame_id": f.stem,
            "timestamp": round(idx / sample_fps, 3),
            "path": str(f.relative_to(settings.JOBS_DIR)),
        })
    tracker.log(f"Extracted {len(frames)} frames from source video")
    return frames
