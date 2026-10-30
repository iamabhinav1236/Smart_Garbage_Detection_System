import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from app.database import Base

class EmailSetting(Base):
    __tablename__ = "email_settings"

    id = Column(Integer, primary_key=True, index=True)
    caretaker_name = Column(String(100), default="Campus Caretaker")
    caretaker_email = Column(String(150), default="caretaker@campus.edu")
    backup_email = Column(String(150), default="")
    smtp_host = Column(String(100), default="smtp.gmail.com")
    smtp_port = Column(Integer, default=587)
    smtp_username = Column(String(150), default="")
    smtp_password = Column(String(255), default="")  # Stored password/App password
    alert_threshold = Column(Float, default=85.0)
    cooldown_minutes = Column(Integer, default=15)
    email_alerts_enabled = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class SystemSetting(Base):
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True)
    default_threshold = Column(Float, default=85.0)
    default_cooldown = Column(Integer, default=15)
    detection_fps = Column(Integer, default=5)
    confidence_threshold = Column(Float, default=0.25)
    camera_reconnect_interval = Column(Integer, default=5)
    demo_mode = Column(Boolean, default=False)
    email_notification_enabled = Column(Boolean, default=True)
    floor_litter_enabled = Column(Boolean, default=True)
    model_path = Column(String(255), default="models/yolov8n.onnx")
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
