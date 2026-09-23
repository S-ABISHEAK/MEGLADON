"""Central configuration for the MEGALODON backend."""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "MEGALODON"

    # Storage — local dev now, swappable for S3/GCS later via storage backend interface
    JOBS_DIR: Path = Path(__file__).resolve().parent.parent.parent / "jobs"

    # Database
    DATABASE_URL: str = "sqlite:///./megalodon.db"

    # Queue
    REDIS_URL: str = "redis://localhost:6379/0"

    # Upload constraints
    MAX_UPLOAD_BYTES: int = 8 * 1024 * 1024 * 1024  # 8 GB
    ALLOWED_VIDEO_EXTENSIONS: tuple[str, ...] = (".mp4", ".mov", ".avi", ".mkv")

    # Frame extraction defaults
    DEFAULT_FRAME_SAMPLE_FPS: float = 2.0  # extract 2 frames/sec by default
    INFERENCE_WORKING_RESOLUTION: int = 1024  # long-edge px for expensive inference
    KEYFRAME_SIMILARITY_THRESHOLD: float = 0.75
    QUALITY_REJECT_THRESHOLD: float = 0.35

    # GPU / device
    FORCE_CPU: bool = False

    def job_dir(self, job_id: str) -> Path:
        return self.JOBS_DIR / job_id


settings = Settings()
settings.JOBS_DIR.mkdir(parents=True, exist_ok=True)
