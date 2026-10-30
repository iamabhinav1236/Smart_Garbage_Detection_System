import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    bin_id = Column(Integer, ForeignKey("bins.id", ondelete="CASCADE"), index=True, nullable=False)
    bin_code = Column(String(50), nullable=False)
    location = Column(String(150), default="")
    fill_percentage = Column(Float, nullable=False)
    threshold = Column(Float, default=85.0)
    recipient = Column(String(150), nullable=False)
    sent_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    status = Column(String(30), default="SENT")  # SENT, FAILED, SIMULATED
    snapshot_path = Column(String(255), nullable=True)
    message = Column(Text, default="")

    bin = relationship("Dustbin", back_populates="alerts")
