"""Helper used by every pipeline stage to record real progress to the DB and event bus."""
from __future__ import annotations

import time
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.job import ProcessingStage, ReconstructionJob, JobStatus
from app.services.event_bus import publish_event

STAGE_ORDER = [
    "VIDEO_PROCESSING",
    "FRAME_ANALYSIS",
    "KEYFRAME_SELECTION",
    "POSE_ESTIMATION",
    "DYNAMIC_OBJECT_HANDLING",
    "AI_RECONSTRUCTION",
    "FUSION_OPTIMIZATION",
    "GEOREFERENCING",
    "MESH_TEXTURE",
    "FINAL_OUTPUT",
]

STAGE_TO_JOB_STATUS = {
    "VIDEO_PROCESSING": JobStatus.FRAME_EXTRACTION,
    "FRAME_ANALYSIS": JobStatus.FRAME_ANALYSIS,
    "KEYFRAME_SELECTION": JobStatus.KEYFRAME_SELECTION,
    "POSE_ESTIMATION": JobStatus.POSE_ESTIMATION,
    "DYNAMIC_OBJECT_HANDLING": JobStatus.DYNAMIC_OBJECT_HANDLING,
    "AI_RECONSTRUCTION": JobStatus.AI_RECONSTRUCTION,
    "FUSION_OPTIMIZATION": JobStatus.FUSION_OPTIMIZATION,
    "GEOREFERENCING": JobStatus.GEOREFERENCING,
    "MESH_TEXTURE": JobStatus.MESHING,
    "FINAL_OUTPUT": JobStatus.COMPLETED,
}


class StageTracker:
    """Bound to one (job_id, stage) pair for the duration of that stage's execution."""

    def __init__(self, db: Session, job_id: str, stage: str):
        self.db = db
        self.job_id = job_id
        self.stage = stage
        self._t0 = time.time()
        row = (
            db.query(ProcessingStage)
            .filter_by(job_id=job_id, stage=stage)
            .first()
        )
        if row is None:
            row = ProcessingStage(job_id=job_id, stage=stage, status="PENDING", progress=0.0, stats={})
            db.add(row)
            db.commit()
            db.refresh(row)
        self.row = row

    def start(self, operation: str = "starting"):
        self.row.status = "RUNNING"
        self.row.started_at = datetime.now(timezone.utc)
        self.row.current_operation = operation
        self.row.progress = 0.0
        self.db.commit()

        job = self.db.query(ReconstructionJob).get(self.job_id)
        if job and self.stage in STAGE_TO_JOB_STATUS:
            job.status = STAGE_TO_JOB_STATUS[self.stage]
            if job.started_at is None:
                job.started_at = datetime.now(timezone.utc)
            self.db.commit()

        publish_event(self.job_id, {
            "type": "stage_started",
            "stage": self.stage,
            "operation": operation,
        })

    def progress(self, pct: float, operation: str | None = None, **stats):
        self.row.progress = max(0.0, min(100.0, pct))
        if operation:
            self.row.current_operation = operation
        if stats:
            self.row.stats = {**(self.row.stats or {}), **stats}
        self.db.commit()
        publish_event(self.job_id, {
            "type": "stage_progress",
            "stage": self.stage,
            "progress": self.row.progress,
            "operation": self.row.current_operation,
            "elapsed_s": round(time.time() - self._t0, 2),
            "stats": self.row.stats,
        })

    def log(self, message: str):
        self.row.log = (self.row.log or "") + f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n"
        self.db.commit()
        publish_event(self.job_id, {"type": "log", "stage": self.stage, "message": message})

    def demo_mode(self, component: str, reason: str):
        existing = set(filter(None, (self.row.demo_mode or "").split(",")))
        existing.add(component)
        self.row.demo_mode = ",".join(sorted(existing))
        self.db.commit()
        self.log(f"{component}: DEMO ARTIFACT — {reason}")
        publish_event(self.job_id, {
            "type": "demo_mode",
            "stage": self.stage,
            "component": component,
            "reason": reason,
        })

    def complete(self, **stats):
        self.row.status = "COMPLETED"
        self.row.progress = 100.0
        self.row.completed_at = datetime.now(timezone.utc)
        if stats:
            self.row.stats = {**(self.row.stats or {}), **stats}
        self.db.commit()
        publish_event(self.job_id, {
            "type": "stage_completed",
            "stage": self.stage,
            "elapsed_s": round(time.time() - self._t0, 2),
            "stats": self.row.stats,
        })

    def fail(self, error: str):
        self.row.status = "FAILED"
        self.row.completed_at = datetime.now(timezone.utc)
        self.db.commit()
        job = self.db.query(ReconstructionJob).get(self.job_id)
        if job:
            job.status = JobStatus.FAILED
            job.error = error
            job.failed_stage = self.stage
            self.db.commit()
        self.log(f"ERROR: {error}")
        publish_event(self.job_id, {"type": "stage_failed", "stage": self.stage, "error": error})
