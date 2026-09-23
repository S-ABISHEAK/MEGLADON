from app.pipeline.video_processing import probe_video, extract_frames
from app.services.stage_tracker import StageTracker
from app.database import Base
from app.models.job import ReconstructionJob, JobStatus, ProcessingStage
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def _make_session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/t.db", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def test_probe_video_extracts_real_metadata(test_video):
    meta = probe_video(test_video)
    assert meta["width"] == 640
    assert meta["height"] == 360
    assert meta["fps"] > 0
    assert meta["duration"] > 4
    assert meta["codec"] == "h264"


def test_probe_video_rejects_missing_file():
    import pytest
    with pytest.raises(Exception):
        probe_video("/nonexistent/path.mp4")


def test_frame_extraction_streams_to_disk(test_video, tmp_path, job_dir, monkeypatch):
    db = _make_session(tmp_path)
    job_id = "test-job-1"
    db.add(ReconstructionJob(id=job_id, filename="test.mp4", status=JobStatus.UPLOADED))
    db.add(ProcessingStage(job_id=job_id, stage="VIDEO_PROCESSING", status="PENDING", progress=0.0, stats={}))
    db.commit()

    (job_dir / job_id / "frames").mkdir(parents=True)
    tracker = StageTracker(db, job_id, "VIDEO_PROCESSING")
    tracker.start()
    frames = extract_frames(test_video, job_id, tracker, sample_fps=2.0)

    assert len(frames) > 0
    for f in frames:
        assert (job_dir / f["path"]).exists()
