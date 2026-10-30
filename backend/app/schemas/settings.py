from pydantic import BaseModel, EmailStr
from typing import Optional
import datetime

class EmailSettingsUpdate(BaseModel):
    caretaker_name: Optional[str] = None
    caretaker_email: Optional[str] = None
    backup_email: Optional[str] = None
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None  # Updated only if non-empty
    alert_threshold: Optional[float] = None
    cooldown_minutes: Optional[int] = None
    email_alerts_enabled: Optional[bool] = None

class EmailSettingsResponse(BaseModel):
    id: int
    caretaker_name: str
    caretaker_email: str
    backup_email: Optional[str] = ""
    smtp_host: str
    smtp_port: int
    smtp_username: str
    # Passwords must NOT be exposed in plain text in response!
    smtp_password_configured: bool
    alert_threshold: float
    cooldown_minutes: int
    email_alerts_enabled: bool
    updated_at: datetime.datetime

    class Config:
        from_attributes = True

class TestEmailRequest(BaseModel):
    recipient_email: Optional[str] = None

class SystemSettingsUpdate(BaseModel):
    default_threshold: Optional[float] = None
    default_cooldown: Optional[int] = None
    detection_fps: Optional[int] = None
    confidence_threshold: Optional[float] = None
    camera_reconnect_interval: Optional[int] = None
    demo_mode: Optional[bool] = None
    email_notification_enabled: Optional[bool] = None
    floor_litter_enabled: Optional[bool] = None
    model_path: Optional[str] = None

class SystemSettingsResponse(BaseModel):
    id: int
    default_threshold: float
    default_cooldown: int
    detection_fps: int
    confidence_threshold: float
    camera_reconnect_interval: int
    demo_mode: bool
    email_notification_enabled: bool
    floor_litter_enabled: bool
    model_path: str
    updated_at: datetime.datetime

    class Config:
        from_attributes = True
