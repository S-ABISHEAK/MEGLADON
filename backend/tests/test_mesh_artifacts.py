import numpy as np
import cv2

from app.database import Base
from app.models.job import ReconstructionJob, JobStatus, ProcessingStage
from app.pipeline.mesh_texture import generate_mesh
from app.services.stage_tracker import StageTracker
from app.config import settings
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def _make_session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/t.db", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def test_mesh_generation_produces_downloadable_files(tmp_path, job_dir):
    db = _make_session(tmp_path)
    job_id = "mesh-job-1"
    db.add(ReconstructionJob(id=job_id, filename="x.mp4", status=JobStatus.UPLOADED))
    db.add(ProcessingStage(job_id=job_id, stage="MESH_TEXTURE", status="PENDING", progress=0.0, stats={}))
    db.commit()

    job_root = job_dir / job_id
    (job_root / "keyframes").mkdir(parents=True)
    img_path = job_root / "keyframes" / "keyframe_000001.jpg"
    cv2.imwrite(str(img_path), np.full((360, 640, 3), 128, dtype=np.uint8))

    keyframes = [{"frame_id": "frame_000001", "path": str(img_path.relative_to(settings.JOBS_DIR)), "timestamp": 0.0}]
    poses = [{"frame_id": "frame_000001", "timestamp": 0.0, "x": 0, "y": 0, "z": 0, "roll": 0, "pitch": 0, "yaw": 0}]

    # synthetic sphere point cloud -- enough real 3D structure for Poisson to mesh
    rng = np.random.default_rng(1)
    n = 400
    phi = rng.uniform(0, np.pi, n)
    theta = rng.uniform(0, 2 * np.pi, n)
    points = np.stack([np.sin(phi) * np.cos(theta), np.sin(phi) * np.sin(theta), np.cos(phi)], axis=1)
    colors = rng.uniform(0, 1, (n, 3))

    tracker = StageTracker(db, job_id, "MESH_TEXTURE")
    tracker.start()
    result = generate_mesh(job_id, points, colors, keyframes, poses, tracker)

    assert result["n_vertices"] > 0
    assert result["n_triangles"] > 0
    assert (settings.JOBS_DIR / result["ply_path"]).exists()
    assert (settings.JOBS_DIR / result["obj_path"]).exists()
