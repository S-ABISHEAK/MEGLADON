from sqlalchemy import Column, String, Integer, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.database import Base


class DynamicObject(Base):
    __tablename__ = "dynamic_objects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String, ForeignKey("reconstruction_jobs.id"), nullable=False)
    object_id = Column(String, nullable=False)  # tracker-assigned id
    cls = Column("class", String, nullable=False)
    confidence = Column(Float)
    motion_status = Column(String)  # STATIC, DYNAMIC, UNCERTAIN
    trajectory = Column(JSON, default=list)  # list of {frame_id, bbox, timestamp}
    first_seen = Column(Float)
    last_seen = Column(Float)

    job = relationship("ReconstructionJob", back_populates="dynamic_objects")
