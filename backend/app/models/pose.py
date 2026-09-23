from sqlalchemy import Column, String, Integer, Float, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class Pose(Base):
    __tablename__ = "poses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String, ForeignKey("reconstruction_jobs.id"), nullable=False)
    timestamp = Column(Float, nullable=False)
    x = Column(Float)
    y = Column(Float)
    z = Column(Float)
    roll = Column(Float)
    pitch = Column(Float)
    yaw = Column(Float)
    source = Column(String)  # VISUAL, IMU, GPS, RTK, FUSED
    confidence = Column(Float)

    job = relationship("ReconstructionJob", back_populates="poses")
