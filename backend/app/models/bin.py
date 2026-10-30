import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, DateTime
from sqlalchemy.orm import relationship
from app.database import Base

class Dustbin(Base):
    __tablename__ = "bins"

    id = Column(Integer, primary_key=True, index=True)
    bin_id = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    location = Column(String(150), nullable=False)
    camera_url = Column(String(255), default="demo")
    camera_protocol = Column(String(20), default="http")  # http, rtsp, mjpeg, demo
    threshold = Column(Float, default=85.0)
    description = Column(Text, default="")
    active = Column(Boolean, default=True)
    
    # Dual ROI coordinates stored as JSON strings
    # e.g. "[[120, 180], [480, 180], [520, 560], [80, 560]]" or normalized "[0.2, 0.3, 0.8, 0.9]"
    bin_roi = Column(Text, default="")
    floor_roi = Column(Text, default="")
    floor_litter_enabled = Column(Boolean, default=True)
    
    # Real-time state cache
    current_fill_percentage = Column(Float, default=0.0)
    current_status = Column(String(20), default="NORMAL")  # NORMAL, WARNING, CRITICAL
    floor_litter_detected = Column(Boolean, default=False)
    camera_online = Column(Boolean, default=False)
    last_reading_time = Column(DateTime, nullable=True)
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    readings = relationship("FillReading", back_populates="bin", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="bin", cascade="all, delete-orphan")
