import enum
import uuid

from sqlalchemy import Column, String, DateTime, Text, Integer, Float, Enum, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class JobStatus(str, enum.Enum):
    UPLOADED = "UPLOADED"
    VALIDATING = "VALIDATING"
    FRAME_EXTRACTION = "FRAME_EXTRACTION"
    FRAME_ANALYSIS = "FRAME_ANALYSIS"
    KEYFRAME_SELECTION = "KEYFRAME_SELECTION"
    POSE_ESTIMATION = "POSE_ESTIMATION"
    DYNAMIC_OBJECT_HANDLING = "DYNAMIC_OBJECT_HANDLING"
    AI_RECONSTRUCTION = "AI_RECONSTRUCTION"
    FUSION_OPTIMIZATION = "FUSION_OPTIMIZATION"
    GEOREFERENCING = "GEOREFERENCING"
    MESHING = "MESHING"
    TEXTURING = "TEXTURING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ReconstructionJob(Base):
    __tablename__ = "reconstruction_jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String, nullable=False)
    status = Column(Enum(JobStatus), default=JobStatus.UPLOADED, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error = Column(Text, nullable=True)
    failed_stage = Column(String, nullable=True)
    sensor_file_path = Column(String, nullable=True)  # optional GPS/IMU/RTK upload

    video_metadata = relationship("VideoMetadata", back_populates="job", uselist=False, cascade="all,delete")
    stages = relationship("ProcessingStage", back_populates="job", cascade="all,delete")
    artifacts = relationship("OutputArtifact", back_populates="job", cascade="all,delete")
    frames = relationship("Frame", back_populates="job", cascade="all,delete")
    keyframes = relationship("Keyframe", back_populates="job", cascade="all,delete")
    poses = relationship("Pose", back_populates="job", cascade="all,delete")
    dynamic_objects = relationship("DynamicObject", back_populates="job", cascade="all,delete")


class VideoMetadata(Base):
    __tablename__ = "video_metadata"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String, ForeignKey("reconstruction_jobs.id"), nullable=False, unique=True)
    width = Column(Integer)
    height = Column(Integer)
    fps = Column(Float)
    duration = Column(Float)
    codec = Column(String)
    bitrate = Column(Integer)
    frame_count = Column(Integer)
    has_gps_metadata = Column(String, default="unknown")

    job = relationship("ReconstructionJob", back_populates="video_metadata")


class ProcessingStage(Base):
    __tablename__ = "processing_stages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String, ForeignKey("reconstruction_jobs.id"), nullable=False)
    stage = Column(String, nullable=False)
    status = Column(String, default="PENDING")  # PENDING, RUNNING, COMPLETED, FAILED
    progress = Column(Float, default=0.0)
    current_operation = Column(String, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    log = Column(Text, default="")
    stats = Column(JSON, default=dict)  # frames processed, keyframes, objects, points etc
    demo_mode = Column(String, default="")  # comma-separated list of components running in DEMO MODE

    job = relationship("ReconstructionJob", back_populates="stages")


class OutputArtifact(Base):
    __tablename__ = "output_artifacts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String, ForeignKey("reconstruction_jobs.id"), nullable=False)
    type = Column(String, nullable=False)  # e.g. "keyframes.json", "model.glb", "trajectory.json"
    path = Column(String, nullable=False)  # relative to job dir
    artifact_metadata = Column(JSON, default=dict)

    job = relationship("ReconstructionJob", back_populates="artifacts")
