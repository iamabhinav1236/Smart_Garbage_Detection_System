import json
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.bin import Dustbin
from app.models.settings import EmailSetting, SystemSetting
from app.models.reading import FillReading
from app.utils.security import get_password_hash
from app.utils.logger import logger
from app.config import settings

def seed_initial_data(db: Session):
    # 1. Admin user
    admin = db.query(User).filter(User.username == settings.DEFAULT_ADMIN_USER).first()
    if not admin:
        logger.info(f"Seeding default admin user: {settings.DEFAULT_ADMIN_USER}")
        admin = User(
            username=settings.DEFAULT_ADMIN_USER,
            password_hash=get_password_hash(settings.DEFAULT_ADMIN_PASS),
            full_name="System Administrator"
        )
        db.add(admin)
        db.commit()

    # 2. Email settings
    email_setting = db.query(EmailSetting).first()
    if not email_setting:
        logger.info("Seeding default Email settings")
        email_setting = EmailSetting(
            caretaker_name=settings.CARETAKER_NAME,
            caretaker_email=settings.CARETAKER_EMAIL or "caretaker@smartcampus.org",
            backup_email="",
            smtp_host=settings.SMTP_HOST,
            smtp_port=settings.SMTP_PORT,
            smtp_username=settings.SMTP_USERNAME,
            smtp_password=settings.SMTP_PASSWORD,
            alert_threshold=settings.ALERT_THRESHOLD,
            cooldown_minutes=settings.COOLDOWN_MINUTES,
            email_alerts_enabled=True
        )
        db.add(email_setting)
        db.commit()

    # 3. System settings
    sys_setting = db.query(SystemSetting).first()
    if not sys_setting:
        logger.info("Seeding default System settings")
        sys_setting = SystemSetting(
            default_threshold=85.0,
            default_cooldown=15,
            detection_fps=settings.DETECTION_FPS,
            confidence_threshold=settings.CONFIDENCE_THRESHOLD,
            camera_reconnect_interval=5,
            demo_mode=False,
            email_notification_enabled=True,
            floor_litter_enabled=True,
            model_path=settings.YOLO_MODEL_PATH
        )
        db.add(sys_setting)
        db.commit()

    # 4. Sample Bins (if database is empty)
    bin_count = db.query(Dustbin).count()
    if bin_count == 0:
        logger.info("Seeding sample demonstration dustbins")
        
        # Default Bin 1: Main Campus Gate
        # Pixel coordinates in the 640x480 analysis frame, matching the demo camera's dustbin
        bin_roi_default = json.dumps([
            [208, 140], [432, 140], [408, 392], [232, 392]
        ])
        floor_roi_default = json.dumps([
            [20, 345], [620, 345], [630, 470], [10, 470]
        ])
        
        sample_bin_1 = Dustbin(
            bin_id="BIN-001",
            name="Main Campus Gate",
            location="Sector 4 - Administrative Zone A",
            camera_url="demo",
            camera_protocol="demo",
            threshold=85.0,
            description="Smart dustbin overlooking the primary entrance corridor. Calibrated dual-ROI active.",
            active=True,
            bin_roi=bin_roi_default,
            floor_roi=floor_roi_default,
            floor_litter_enabled=True,
            current_fill_percentage=64.5,
            current_status="NORMAL",
            floor_litter_detected=False,
            camera_online=True
        )
        
        # Default Bin 2: Cafeteria Courtyard
        sample_bin_2 = Dustbin(
            bin_id="BIN-002",
            name="Cafeteria Courtyard",
            location="Student Center - Central Lawn",
            camera_url="demo",
            camera_protocol="demo",
            threshold=85.0,
            description="High footfall recycling and mixed waste receptacle outside food court.",
            active=True,
            bin_roi=bin_roi_default,
            floor_roi=floor_roi_default,
            floor_litter_enabled=True,
            current_fill_percentage=88.2,
            current_status="CRITICAL",
            floor_litter_detected=True,
            camera_online=True
        )

        # Default Bin 3: Academic Block B
        sample_bin_3 = Dustbin(
            bin_id="BIN-003",
            name="Academic Block B Hall",
            location="Department of AIML - Floor 1",
            camera_url="demo",
            camera_protocol="demo",
            threshold=80.0,
            description="Corridor smart bin with floor litter tracking.",
            active=True,
            bin_roi=bin_roi_default,
            floor_roi=floor_roi_default,
            floor_litter_enabled=True,
            current_fill_percentage=42.0,
            current_status="NORMAL",
            floor_litter_detected=False,
            camera_online=True
        )

        db.add_all([sample_bin_1, sample_bin_2, sample_bin_3])
        db.commit()

        # Seed some historical readings for analytics visualization
        import datetime
        now = datetime.datetime.utcnow()
        readings = []
        for b_id, base_fill in [(sample_bin_1.id, 50.0), (sample_bin_2.id, 75.0), (sample_bin_3.id, 35.0)]:
            for i in range(24):
                time_point = now - datetime.timedelta(hours=24 - i)
                # realistic curve
                variation = (i % 6) * 5.5 - 7
                fill = min(100.0, max(10.0, base_fill + variation))
                readings.append(FillReading(
                    bin_id=b_id,
                    fill_percentage=round(fill, 1),
                    floor_litter_detected=(fill > 85.0 and i > 18),
                    waste_boxes_count=int(fill / 15),
                    timestamp=time_point
                ))
        db.add_all(readings)
        db.commit()
        logger.info("Sample seed completed successfully.")
