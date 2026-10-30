from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.settings import EmailSetting
from app.schemas.settings import EmailSettingsUpdate, EmailSettingsResponse, TestEmailRequest
from app.email.email_service import EmailService
from app.utils.logger import logger

router = APIRouter(prefix="/email-settings", tags=["Email & Caretaker Settings"])

@router.get("", response_model=EmailSettingsResponse)
def get_email_settings(db: Session = Depends(get_db)):
    setting = db.query(EmailSetting).first()
    if not setting:
        raise HTTPException(status_code=404, detail="Email settings not found")

    return EmailSettingsResponse(
        id=setting.id,
        caretaker_name=setting.caretaker_name,
        caretaker_email=setting.caretaker_email,
        backup_email=setting.backup_email or "",
        smtp_host=setting.smtp_host,
        smtp_port=setting.smtp_port,
        smtp_username=setting.smtp_username,
        smtp_password_configured=bool(setting.smtp_password),
        alert_threshold=setting.alert_threshold,
        cooldown_minutes=setting.cooldown_minutes,
        email_alerts_enabled=setting.email_alerts_enabled,
        updated_at=setting.updated_at
    )

@router.put("", response_model=EmailSettingsResponse)
def update_email_settings(update_data: EmailSettingsUpdate, db: Session = Depends(get_db)):
    setting = db.query(EmailSetting).first()
    if not setting:
        setting = EmailSetting()
        db.add(setting)

    if update_data.caretaker_name is not None:
        setting.caretaker_name = update_data.caretaker_name
    if update_data.caretaker_email is not None:
        setting.caretaker_email = update_data.caretaker_email
    if update_data.backup_email is not None:
        setting.backup_email = update_data.backup_email
    if update_data.smtp_host is not None:
        setting.smtp_host = update_data.smtp_host
    if update_data.smtp_port is not None:
        setting.smtp_port = update_data.smtp_port
    if update_data.smtp_username is not None:
        setting.smtp_username = update_data.smtp_username
    if update_data.smtp_password is not None and update_data.smtp_password.strip() != "":
        setting.smtp_password = update_data.smtp_password.strip()
    if update_data.alert_threshold is not None:
        setting.alert_threshold = update_data.alert_threshold
    if update_data.cooldown_minutes is not None:
        setting.cooldown_minutes = update_data.cooldown_minutes
    if update_data.email_alerts_enabled is not None:
        setting.email_alerts_enabled = update_data.email_alerts_enabled

    db.commit()
    db.refresh(setting)
    logger.info("Updated Email & Caretaker settings")

    return EmailSettingsResponse(
        id=setting.id,
        caretaker_name=setting.caretaker_name,
        caretaker_email=setting.caretaker_email,
        backup_email=setting.backup_email or "",
        smtp_host=setting.smtp_host,
        smtp_port=setting.smtp_port,
        smtp_username=setting.smtp_username,
        smtp_password_configured=bool(setting.smtp_password),
        alert_threshold=setting.alert_threshold,
        cooldown_minutes=setting.cooldown_minutes,
        email_alerts_enabled=setting.email_alerts_enabled,
        updated_at=setting.updated_at
    )

@router.post("/test")
def test_email(req: TestEmailRequest, db: Session = Depends(get_db)):
    setting = db.query(EmailSetting).first()
    recipient = req.recipient_email or (setting.caretaker_email if setting else None)
    if not recipient:
        raise HTTPException(status_code=400, detail="Recipient email must be provided or configured.")

    smtp_config = {
        "smtp_host": setting.smtp_host if setting else "smtp.gmail.com",
        "smtp_port": setting.smtp_port if setting else 587,
        "smtp_username": setting.smtp_username if setting else "",
        "smtp_password": setting.smtp_password if setting else "",
    }

    result = EmailService.send_test_email(recipient, smtp_config)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message", "Failed to send test email."))

    return {"message": "Test email sent successfully.", "recipient": recipient}
