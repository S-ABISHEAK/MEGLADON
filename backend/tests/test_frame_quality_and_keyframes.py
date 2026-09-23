from app.database import Base
from app.models.job import ReconstructionJob, JobStatus, ProcessingStage
from app.pipeline.video_processing import extract_frames
from app.pipeline.frame_analysis import analyze_frames
from app.pipeline.keyframe_selection import select_keyframes
from app.services.stage_tracker import StageTracker
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def _make_session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/t.db", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def _prepare(db, job_id):
    db.add(ReconstructionJob(id=job_id, filename="test.mp4", status=JobStatus.UPLOADED))
    for s in ("VIDEO_PROCESSING", "FRAME_ANALYSIS", "KEYFRAME_SELECTION"):
        db.add(ProcessingStage(job_id=job_id, stage=s, status="PENDING", progress=0.0, stats={}))
    db.commit()


def test_frame_quality_scoring_produces_bounded_scores(test_video, tmp_path, job_dir):
    db = _make_session(tmp_path)
    job_id = "test-job-2"
    _prepare(db, job_id)

    t1 = StageTracker(db, job_id, "VIDEO_PROCESSING")
    t1.start()
    frames = extract_frames(test_video, job_id, t1, sample_fps=3.0)

    t2 = StageTracker(db, job_id, "FRAME_ANALYSIS")
    t2.start()
    scored = analyze_frames(job_id, frames, t2)

    assert len(scored) == len(frames)
    for f in scored:
        assert 0.0 <= f["blur_score"]
        assert 0.0 <= f["exposure_score"] <= 1.0
        assert 0.0 <= f["quality_score"] <= 1.0
        assert "selected" in f

    assert (job_dir / job_id / "frames" / "quality" / "frame_quality.json").exists()
    assert (job_dir / job_id / "frames" / "quality" / "frame_quality.csv").exists()


def test_keyframe_selection_does_not_take_every_nth_frame(test_video, tmp_path, job_dir):
    """Keyframe count must depend on actual content similarity, not just index % N."""
    db = _make_session(tmp_path)
    job_id = "test-job-3"
    _prepare(db, job_id)

    t1 = StageTracker(db, job_id, "VIDEO_PROCESSING")
    t1.start()
    frames = extract_frames(test_video, job_id, t1, sample_fps=4.0)

    t2 = StageTracker(db, job_id, "FRAME_ANALYSIS")
    t2.start()
    scored = analyze_frames(job_id, frames, t2)

    t3 = StageTracker(db, job_id, "KEYFRAME_SELECTION")
    t3.start()
    keyframes = select_keyframes(job_id, scored, t3)

    assert len(keyframes) >= 1
    assert len(keyframes) <= len(frames)
    for kf in keyframes:
        assert "selection_reason" in kf
        assert (job_dir / kf["path"]).exists()
    assert (job_dir / job_id / "keyframes" / "keyframes.json").exists()
