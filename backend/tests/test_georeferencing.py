import numpy as np

from app.database import Base
from app.models.job import ReconstructionJob, JobStatus, ProcessingStage
from app.pipeline.georeferencing import georeference, _umeyama
from app.services.stage_tracker import StageTracker
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def _make_session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/t.db", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def test_no_gps_marks_model_local_not_global(tmp_path, job_dir):
    db = _make_session(tmp_path)
    job_id = "geo-job-1"
    db.add(ReconstructionJob(id=job_id, filename="x.mp4", status=JobStatus.UPLOADED))
    db.add(ProcessingStage(job_id=job_id, stage="GEOREFERENCING", status="PENDING", progress=0.0, stats={}))
    db.commit()
    (job_dir / job_id).mkdir(parents=True)

    points = np.random.rand(50, 3)
    poses = [{"timestamp": i * 1.0, "x": i * 0.1, "y": 0, "z": 0, "source": "VISUAL", "confidence": 0.8}
             for i in range(5)]

    tracker = StageTracker(db, job_id, "GEOREFERENCING")
    tracker.start()
    result = georeference(job_id, points, poses, sensor_rows=None, tracker=tracker)

    assert result["coordinates"]["reference_type"] == "LOCAL"
    assert result["coordinates"]["latitude"] is None
    assert "SAM2" not in (tracker.row.demo_mode or "")  # sanity: right component flagged
    assert "PROJ" in tracker.row.demo_mode


def test_umeyama_recovers_known_similarity_transform():
    rng = np.random.default_rng(0)
    src = rng.random((20, 3))
    true_R = np.array([[0, -1, 0], [1, 0, 0], [0, 0, 1]], dtype=float)  # 90deg about Z
    true_t = np.array([5.0, -3.0, 2.0])
    true_scale = 2.5
    dst = true_scale * (true_R @ src.T).T + true_t

    R, t, scale = _umeyama(src, dst)

    assert np.isclose(scale, true_scale, atol=1e-6)
    assert np.allclose(R, true_R, atol=1e-6)
    assert np.allclose(t, true_t, atol=1e-6)
