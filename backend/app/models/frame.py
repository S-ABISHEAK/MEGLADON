from sqlalchemy import Column, String, Integer, Float, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from app.database import Base


class Frame(Base):
    __tablename__ = "frames"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String, ForeignKey("reconstruction_jobs.id"), nullable=False)
    frame_id = Column(String, nullable=False)  # e.g. frame_000123
    timestamp = Column(Float, nullable=False)
    path = Column(String, nullable=False)

    blur_score = Column(Float)
    exposure_score = Column(Float)
    contrast_score = Column(Float)
    compression_score = Column(Float)
    quality_score = Column(Float)

    selected = Column(Boolean, default=False)  # survived quality rejection

    job = relationship("ReconstructionJob", back_populates="frames")


class Keyframe(Base):
    __tablename__ = "keyframes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String, ForeignKey("reconstruction_jobs.id"), nullable=False)
    frame_id = Column(String, nullable=False)
    path = Column(String, nullable=False)
    timestamp = Column(Float)

    similarity = Column(Float)  # similarity to previous keyframe
    motion_score = Column(Float)
    overlap_score = Column(Float)
    selection_reason = Column(String)

    job = relationship("ReconstructionJob", back_populates="keyframes")
