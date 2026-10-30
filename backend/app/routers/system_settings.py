from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.settings import SystemSetting
from app.schemas.settings import SystemSettingsUpdate, SystemSettingsResponse
from app.utils.logger import logger

router = APIRouter(prefix="/system-settings", tags=["System Settings"])

@router.get("", response_model=SystemSettingsResponse)
def get_system_settings(db: Session = Depends(get_db)):
    setting = db.query(SystemSetting).first()
    if not setting:
        setting = SystemSetting()
        db.add(setting)
        db.commit()
        db.refresh(setting)
    return setting

@router.put("", response_model=SystemSettingsResponse)
def update_system_settings(update_data: SystemSettingsUpdate, db: Session = Depends(get_db)):
    setting = db.query(SystemSetting).first()
    if not setting:
        setting = SystemSetting()
        db.add(setting)

    if update_data.default_threshold is not None:
        setting.default_threshold = update_data.default_threshold
    if update_data.default_cooldown is not None:
        setting.default_cooldown = update_data.default_cooldown
    if update_data.detection_fps is not None:
        setting.detection_fps = update_data.detection_fps
    if update_data.confidence_threshold is not None:
        setting.confidence_threshold = update_data.confidence_threshold
    if update_data.camera_reconnect_interval is not None:
        setting.camera_reconnect_interval = update_data.camera_reconnect_interval
    if update_data.demo_mode is not None:
        setting.demo_mode = update_data.demo_mode
    if update_data.email_notification_enabled is not None:
        setting.email_notification_enabled = update_data.email_notification_enabled
    if update_data.floor_litter_enabled is not None:
        setting.floor_litter_enabled = update_data.floor_litter_enabled
    if update_data.model_path is not None:
        setting.model_path = update_data.model_path

    db.commit()
    db.refresh(setting)
    logger.info("Updated System settings")
    return setting
