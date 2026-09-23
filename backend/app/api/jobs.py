from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.job import ReconstructionJob, VideoMetadata, JobStatus, ProcessingStage, OutputArtifact
from app.models.frame import Frame, Keyframe
from app.models.pose import Pose
from app.models.dynamic_object import DynamicObject
from app.schemas.job import JobOut, JobCreateResponse
from app.services.stage_tracker import STAGE_ORDER
from app.utils.storage import create_job_tree, job_path, safe_filename
from app.pipeline.video_processing import probe_video

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.post("", response_model=JobCreateResponse)
def create_job(db: Session = Depends(get_db)):
    job = ReconstructionJob(filename="", status=JobStatus.UPLOADED)
    db.add(job)
    db.commit()
    db.refresh(job)
    create_job_tree(job.id)
    for stage in STAGE_ORDER:
        db.add(ProcessingStage(job_id=job.id, stage=stage, status="PENDING", progress=0.0, stats={}))
    db.commit()
    return JobCreateResponse(job_id=job.id, status=job.status.value)


@router.post("/{job_id}/upload")
async def upload_video(job_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    job = db.query(ReconstructionJob).get(job_id)
    if not job:
        raise HTTPException(404, "job not found")

    ext = Path(file.filename or "").suffix.lower()
    if ext not in settings.ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(400, f"unsupported extension '{ext}'. Allowed: {settings.ALLOWED_VIDEO_EXTENSIONS}")

    name = safe_filename(file.filename or "video.mp4")
    dest = job_path(job_id, "video", name)
    dest.parent.mkdir(parents=True, exist_ok=True)

    size = 0
    with open(dest, "wb") as out:
        while chunk := await file.read(8 * 1024 * 1024):
            size += len(chunk)
            if size > settings.MAX_UPLOAD_BYTES:
                out.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(400, "file exceeds maximum upload size")
            out.write(chunk)

    job.filename = name
    job.status = JobStatus.VALIDATING
    db.commit()

    try:
        probe = probe_video(str(dest))
    except Exception as e:
        job.status = JobStatus.FAILED
        job.error = f"video validation failed: {e}"
        db.commit()
        raise HTTPException(400, f"invalid or unreadable video: {e}")

    vm = db.query(VideoMetadata).filter_by(job_id=job_id).first()
    if vm is None:
        vm = VideoMetadata(job_id=job_id)
        db.add(vm)
    vm.width = probe["width"]
    vm.height = probe["height"]
    vm.fps = probe["fps"]
    vm.duration = probe["duration"]
    vm.codec = probe["codec"]
    vm.bitrate = probe["bitrate"]
    vm.frame_count = probe["frame_count"]
    vm.has_gps_metadata = probe["has_gps_metadata"]
    job.status = JobStatus.UPLOADED
    db.commit()

    return {"job_id": job_id, "metadata": probe}


@router.post("/{job_id}/sensor-upload")
async def upload_sensor_file(job_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Optional GPS/IMU/RTK CSV or JSON upload (spec section 10)."""
    job = db.query(ReconstructionJob).get(job_id)
    if not job:
        raise HTTPException(404, "job not found")
    if Path(file.filename or "").suffix.lower() not in (".csv", ".json", ".nmea"):
        raise HTTPException(400, "sensor file must be .csv, .json or .nmea")
    name = safe_filename(file.filename or "sensors.csv")
    dest = job_path(job_id, "pose", name)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "wb") as out:
        out.write(await file.read())
    job.sensor_file_path = str(dest.relative_to(settings.JOBS_DIR))
    db.commit()
    return {"job_id": job_id, "sensor_file": job.sensor_file_path}


@router.post("/{job_id}/start")
def start_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(ReconstructionJob).get(job_id)
    if not job:
        raise HTTPException(404, "job not found")
    if not job.filename:
        raise HTTPException(400, "no video uploaded for this job")
    if job.status not in (JobStatus.UPLOADED, JobStatus.FAILED):
        raise HTTPException(400, f"job already {job.status.value}")

    job.error = None
    job.failed_stage = None
    db.commit()

    from app.workers.queue import enqueue_pipeline
    enqueue_pipeline(job_id)
    return {"job_id": job_id, "status": "queued"}


@router.post("/{job_id}/retry")
def retry_job(job_id: str, db: Session = Depends(get_db)):
    """Retry from the failed stage (spec section 21)."""
    job = db.query(ReconstructionJob).get(job_id)
    if not job:
        raise HTTPException(404, "job not found")
    if job.status != JobStatus.FAILED:
        raise HTTPException(400, "job is not in FAILED state")
    job.error = None
    db.commit()
    from app.workers.queue import enqueue_pipeline
    enqueue_pipeline(job_id, resume_from=job.failed_stage)
    return {"job_id": job_id, "status": "retrying", "resume_from": job.failed_stage}


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(ReconstructionJob).get(job_id)
    if not job:
        raise HTTPException(404, "job not found")
    return job


@router.get("/{job_id}/status")
def get_status(job_id: str, db: Session = Depends(get_db)):
    job = db.query(ReconstructionJob).get(job_id)
    if not job:
        raise HTTPException(404, "job not found")
    return {"job_id": job_id, "status": job.status.value, "error": job.error, "failed_stage": job.failed_stage}


@router.get("/{job_id}/stages")
def get_stages(job_id: str, db: Session = Depends(get_db)):
    stages = db.query(ProcessingStage).filter_by(job_id=job_id).all()
    order = {s: i for i, s in enumerate(STAGE_ORDER)}
    stages = sorted(stages, key=lambda s: order.get(s.stage, 99))
    return [
        {
            "stage": s.stage,
            "status": s.status,
            "progress": s.progress,
            "current_operation": s.current_operation,
            "stats": s.stats,
            "demo_mode": s.demo_mode,
            "log": s.log,
        }
        for s in stages
    ]


@router.get("/{job_id}/frames")
def get_frames(job_id: str, limit: int = 200, db: Session = Depends(get_db)):
    frames = db.query(Frame).filter_by(job_id=job_id).limit(limit).all()
    return [
        {
            "frame_id": f.frame_id, "timestamp": f.timestamp, "path": f.path,
            "blur_score": f.blur_score, "exposure_score": f.exposure_score,
            "contrast_score": f.contrast_score, "compression_score": f.compression_score,
            "quality_score": f.quality_score, "selected": f.selected,
        } for f in frames
    ]


@router.get("/{job_id}/keyframes")
def get_keyframes(job_id: str, db: Session = Depends(get_db)):
    kfs = db.query(Keyframe).filter_by(job_id=job_id).all()
    return [
        {
            "frame_id": k.frame_id, "path": k.path, "timestamp": k.timestamp,
            "similarity": k.similarity, "motion_score": k.motion_score,
            "overlap_score": k.overlap_score, "selection_reason": k.selection_reason,
        } for k in kfs
    ]


@router.get("/{job_id}/trajectory")
def get_trajectory(job_id: str, db: Session = Depends(get_db)):
    poses = db.query(Pose).filter_by(job_id=job_id).order_by(Pose.timestamp).all()
    return [
        {
            "timestamp": p.timestamp, "x": p.x, "y": p.y, "z": p.z,
            "roll": p.roll, "pitch": p.pitch, "yaw": p.yaw,
            "source": p.source, "confidence": p.confidence,
        } for p in poses
    ]


@router.get("/{job_id}/dynamic-objects")
def get_dynamic_objects(job_id: str, db: Session = Depends(get_db)):
    objs = db.query(DynamicObject).filter_by(job_id=job_id).all()
    return [
        {
            "object_id": o.object_id, "class": o.cls, "confidence": o.confidence,
            "motion_status": o.motion_status, "trajectory": o.trajectory,
            "first_seen": o.first_seen, "last_seen": o.last_seen,
        } for o in objs
    ]


def _artifact_by_type(db: Session, job_id: str, artifact_type: str) -> OutputArtifact | None:
    return db.query(OutputArtifact).filter_by(job_id=job_id, type=artifact_type).first()


@router.get("/{job_id}/depth")
def get_depth(job_id: str, db: Session = Depends(get_db)):
    art = _artifact_by_type(db, job_id, "depth_maps")
    if not art:
        raise HTTPException(404, "depth artifacts not available yet")
    return {"path": art.path, "metadata": art.artifact_metadata}


@router.get("/{job_id}/point-cloud")
def get_point_cloud(job_id: str, db: Session = Depends(get_db)):
    art = _artifact_by_type(db, job_id, "fused_pointcloud")
    if not art:
        raise HTTPException(404, "point cloud not available yet")
    return {"path": art.path, "metadata": art.artifact_metadata}


@router.get("/{job_id}/confidence")
def get_confidence(job_id: str, db: Session = Depends(get_db)):
    art = _artifact_by_type(db, job_id, "confidence_map")
    if not art:
        raise HTTPException(404, "confidence map not available yet")
    return {"path": art.path, "metadata": art.artifact_metadata}


@router.get("/{job_id}/model")
def get_model(job_id: str, db: Session = Depends(get_db)):
    arts = db.query(OutputArtifact).filter(
        OutputArtifact.job_id == job_id,
        OutputArtifact.type.in_(["model_glb", "model_obj", "model_ply", "final_report"]),
    ).all()
    if not arts:
        raise HTTPException(404, "final model not available yet")
    return {a.type: {"path": a.path, "metadata": a.artifact_metadata} for a in arts}


@router.get("/{job_id}/artifacts")
def get_artifacts(job_id: str, db: Session = Depends(get_db)):
    arts = db.query(OutputArtifact).filter_by(job_id=job_id).all()
    return [{"type": a.type, "path": a.path, "metadata": a.artifact_metadata} for a in arts]


@router.get("/{job_id}/download-package")
def download_package(job_id: str, db: Session = Depends(get_db)):
    job = db.query(ReconstructionJob).get(job_id)
    if not job:
        raise HTTPException(404, "job not found")
    root = job_path(job_id)
    zip_target = settings.JOBS_DIR / f"{job_id}_package"
    archive_path = shutil.make_archive(str(zip_target), "zip", root_dir=str(root))
    return FileResponse(archive_path, filename=f"megalodon_{job_id[:8]}_package.zip",
                         media_type="application/zip")


@router.get("")
def list_jobs(db: Session = Depends(get_db)):
    jobs = db.query(ReconstructionJob).order_by(ReconstructionJob.created_at.desc()).limit(50).all()
    return [{"id": j.id, "filename": j.filename, "status": j.status.value, "created_at": j.created_at} for j in jobs]
