import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import Base, init_db  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402


@pytest.fixture(scope="session")
def test_video(tmp_path_factory):
    out_dir = tmp_path_factory.mktemp("video")
    path = out_dir / "test.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", "mandelbrot=size=640x360:rate=24,zoompan=z='min(zoom+0.003,1.4)':d=1:s=640x360",
        "-t", "5", "-pix_fmt", "yuv420p", str(path),
    ], check=True, capture_output=True)
    return str(path)


@pytest.fixture()
def db_session(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture()
def job_dir(tmp_path, monkeypatch):
    from app import config as config_module
    monkeypatch.setattr(config_module.settings, "JOBS_DIR", tmp_path / "jobs")
    config_module.settings.JOBS_DIR.mkdir(parents=True, exist_ok=True)
    return config_module.settings.JOBS_DIR
