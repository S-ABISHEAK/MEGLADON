import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db


@pytest.fixture()
def client(tmp_path, job_dir):
    engine = create_engine(f"sqlite:///{tmp_path}/api_test.db", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_create_job_creates_pending_stages(client):
    r = client.post("/api/jobs")
    assert r.status_code == 200
    job_id = r.json()["job_id"]
    assert r.json()["status"] == "UPLOADED"

    stages = client.get(f"/api/jobs/{job_id}/stages").json()
    assert len(stages) == 10
    assert all(s["status"] == "PENDING" for s in stages)


def test_upload_rejects_unsupported_extension(client, tmp_path):
    r = client.post("/api/jobs")
    job_id = r.json()["job_id"]

    bad_file = tmp_path / "malware.exe"
    bad_file.write_bytes(b"not a video")
    with open(bad_file, "rb") as f:
        resp = client.post(f"/api/jobs/{job_id}/upload", files={"file": ("malware.exe", f, "application/octet-stream")})
    assert resp.status_code == 400


def test_upload_sanitizes_path_traversal_filename(client, tmp_path, job_dir):
    from app.pipeline.video_processing import probe_video
    import subprocess

    video_path = tmp_path / "clip.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=size=320x240:rate=10:duration=1",
                     str(video_path)], check=True, capture_output=True)

    r = client.post("/api/jobs")
    job_id = r.json()["job_id"]

    with open(video_path, "rb") as f:
        resp = client.post(
            f"/api/jobs/{job_id}/upload",
            files={"file": ("../../../etc/passwd.mp4", f, "video/mp4")},
        )
    assert resp.status_code == 200
    saved_path = job_dir / job_id / "video"
    saved_files = list(saved_path.iterdir())
    assert len(saved_files) == 1
    assert ".." not in str(saved_files[0])
    assert saved_files[0].parent == saved_path


def test_get_nonexistent_job_404s(client):
    r = client.get("/api/jobs/does-not-exist")
    assert r.status_code == 404


def test_start_without_upload_fails(client):
    r = client.post("/api/jobs")
    job_id = r.json()["job_id"]
    resp = client.post(f"/api/jobs/{job_id}/start")
    assert resp.status_code == 400
