import datetime
from sqlalchemy import Column, Integer, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class FillReading(Base):
    __tablename__ = "fill_readings"

    id = Column(Integer, primary_key=True, index=True)
    bin_id = Column(Integer, ForeignKey("bins.id", ondelete="CASCADE"), index=True, nullable=False)
    fill_percentage = Column(Float, nullable=False)
    floor_litter_detected = Column(Boolean, default=False)
    waste_boxes_count = Column(Integer, default=0)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)

    bin = relationship("Dustbin", back_populates="readings")
