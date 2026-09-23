from app.database import Base
from app.models.job import ReconstructionJob, JobStatus, ProcessingStage
from app.services.stage_tracker import StageTracker
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def _make_session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/t.db", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def test_stage_tracker_transitions_pending_running_completed(tmp_path):
    db = _make_session(tmp_path)
    job_id = "sm-job-1"
    db.add(ReconstructionJob(id=job_id, filename="x.mp4", status=JobStatus.UPLOADED))
    db.add(ProcessingStage(job_id=job_id, stage="FRAME_ANALYSIS", status="PENDING", progress=0.0, stats={}))
    db.commit()

    tracker = StageTracker(db, job_id, "FRAME_ANALYSIS")
    assert tracker.row.status == "PENDING"

    tracker.start("scoring")
    assert tracker.row.status == "RUNNING"
    job = db.query(ReconstructionJob).get(job_id)
    assert job.status == JobStatus.FRAME_ANALYSIS

    tracker.progress(42.0, operation="halfway")
    assert tracker.row.progress == 42.0

    tracker.complete(frames_scored=10)
    assert tracker.row.status == "COMPLETED"
    assert tracker.row.progress == 100.0
    assert tracker.row.stats["frames_scored"] == 10


def test_stage_failure_marks_job_failed_with_stage(tmp_path):
    db = _make_session(tmp_path)
    job_id = "sm-job-2"
    db.add(ReconstructionJob(id=job_id, filename="x.mp4", status=JobStatus.UPLOADED))
    db.add(ProcessingStage(job_id=job_id, stage="AI_RECONSTRUCTION", status="PENDING", progress=0.0, stats={}))
    db.commit()

    tracker = StageTracker(db, job_id, "AI_RECONSTRUCTION")
    tracker.start()
    tracker.fail("insufficient parallax")

    job = db.query(ReconstructionJob).get(job_id)
    assert job.status == JobStatus.FAILED
    assert job.failed_stage == "AI_RECONSTRUCTION"
    assert "insufficient parallax" in job.error


def test_demo_mode_is_recorded_and_never_silent(tmp_path):
    db = _make_session(tmp_path)
    job_id = "sm-job-3"
    db.add(ReconstructionJob(id=job_id, filename="x.mp4", status=JobStatus.UPLOADED))
    db.add(ProcessingStage(job_id=job_id, stage="DYNAMIC_OBJECT_HANDLING", status="PENDING", progress=0.0, stats={}))
    db.commit()

    tracker = StageTracker(db, job_id, "DYNAMIC_OBJECT_HANDLING")
    tracker.start()
    tracker.demo_mode("SAM2 Segmenter", "checkpoint unavailable")

    assert "SAM2 Segmenter" in tracker.row.demo_mode
    assert "DEMO ARTIFACT" in tracker.row.log
