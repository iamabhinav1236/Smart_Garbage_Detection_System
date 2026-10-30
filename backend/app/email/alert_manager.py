import os
import time
import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import cv2
import numpy as np
from sqlalchemy.orm import Session
from app.models.bin import Dustbin
from app.models.alert import Alert
from app.models.settings import EmailSetting
from app.email.email_service import EmailService
from app.utils.logger import logger
from app.config import settings

# A bin only counts as "emptied" once its fill is this far below the threshold...
EMPTIED_MARGIN_PCT = 10.0
# ...and has stayed there (with no overflow) for this long. Stops a one-frame dip
# from resetting the alert cycle and causing a fresh email straight away.
EMPTIED_CONFIRM_SECONDS = 30.0


class AlertManager:
    """
    State-based Alert Manager with Cooldown Controls.

    - First email when a bin becomes full / overflowing.
    - While it stays full, a reminder email every cooldown period (default 15 min).
    - Never more than one email per bin per cooldown period, even if the reading
      flickers or the server restarts.
    - The cycle resets only when the bin is genuinely emptied.
    """

    def __init__(self):
        # Maps bin_id -> last alert timestamp in seconds
        self.last_alert_time: Dict[int, float] = {}
        # Maps bin_id -> current alert state ("NORMAL" or "CRITICAL")
        self.bin_state: Dict[int, str] = {}
        # Maps bin_id -> time the bin first looked emptied (for confirmation)
        self.clear_since: Dict[int, float] = {}
        self.snapshots_dir = Path(settings.SNAPSHOTS_DIR)
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)

    def _last_alert(self, db: Session, bin_id: int) -> float:
        """Last automatic alert time; loaded from the database after a restart."""
        if bin_id not in self.last_alert_time:
            last = (
                db.query(Alert)
                .filter(Alert.bin_id == bin_id, ~Alert.message.like("Manual%"))
                .order_by(Alert.sent_at.desc())
                .first()
            )
            ts = 0.0
            if last and last.sent_at:
                ts = last.sent_at.replace(tzinfo=datetime.timezone.utc).timestamp()
            self.last_alert_time[bin_id] = ts
        return self.last_alert_time[bin_id]

    def process_bin_reading(
        self,
        db: Session,
        bin_obj: Dustbin,
        fill_percentage: float,
        annotated_frame: Optional[np.ndarray] = None,
        floor_litter_detected: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Processes real-time bin readings and enforces alerting rules:
        1. Mail is sent only if fill reaches/exceeds threshold OR if overflowing (floor litter).
        2. If the bin is NOT emptied, recurring alert mail is sent every 15 minutes.
        3. If the bin is emptied, mail transfer stops immediately and state resets to NORMAL.
        """
        bin_id = bin_obj.id
        threshold = bin_obj.threshold or 85.0
        current_state = self.bin_state.get(bin_id, "NORMAL")
        now = time.time()

        # Fetch email configuration
        email_settings = db.query(EmailSetting).first()
        cooldown_minutes = email_settings.cooldown_minutes if email_settings and email_settings.cooldown_minutes else 15
        cooldown_seconds = cooldown_minutes * 60
        recipient = (email_settings.caretaker_email if email_settings and email_settings.caretaker_email else "caretaker@campus.org")
        alerts_enabled = email_settings.email_alerts_enabled if email_settings else True

        # Check conditions:
        # Mail is sent ONLY if threshold reached/exceeded OR in case of overflowing
        is_threshold_breached = fill_percentage >= threshold
        is_overflowing = floor_litter_detected and getattr(bin_obj, "floor_litter_enabled", True)
        is_critical = is_threshold_breached or is_overflowing

        if is_critical:
            should_send = False
            is_recurring = False
            trigger_reason = ""
            self.clear_since.pop(bin_id, None)
            elapsed = now - self._last_alert(db, bin_id)

            if current_state == "NORMAL":
                # State transition: NORMAL -> CRITICAL (Initial detection)
                self.bin_state[bin_id] = "CRITICAL"
                # Still respect the cooldown, e.g. right after a restart or a brief dip
                should_send = elapsed >= cooldown_seconds
                is_recurring = False

                if is_threshold_breached and is_overflowing:
                    trigger_reason = f"Threshold reached ({fill_percentage:.1f}% >= {threshold}%) and overflowing"
                elif is_overflowing:
                    trigger_reason = f"Garbage overflow / floor litter detected around bin (Fill: {fill_percentage:.1f}%)"
                else:
                    trigger_reason = f"Threshold breached: {fill_percentage:.1f}% >= {threshold}%"

                logger.info(f"Bin {bin_obj.bin_id} state changed NORMAL -> CRITICAL: {trigger_reason}")
                if not should_send:
                    logger.info(f"Bin {bin_obj.bin_id}: last alert {elapsed / 60:.1f} min ago, next email after the {cooldown_minutes}-min cooldown.")
            else:
                # Already CRITICAL: Dustbin has NOT been emptied yet!
                # Recurring alert every cooldown period (default 15 minutes)
                if elapsed >= cooldown_seconds:
                    should_send = True
                    is_recurring = True
                    mins_elapsed = max(int(elapsed // 60), cooldown_minutes)

                    if is_threshold_breached and is_overflowing:
                        detail = f"Fill: {fill_percentage:.1f}%, Overflow: Yes"
                    elif is_overflowing:
                        detail = f"Fill: {fill_percentage:.1f}%, Overflow: Yes"
                    else:
                        detail = f"Fill: {fill_percentage:.1f}%, Overflow: No"

                    trigger_reason = f"Recurring alert ({mins_elapsed}m elapsed, bin not emptied): {detail}"
                    logger.info(f"Bin {bin_obj.bin_id} still not emptied after {mins_elapsed}m. Triggering recurring {cooldown_minutes}-minute alert.")

            if should_send and alerts_enabled:
                self.last_alert_time[bin_id] = now
                
                # Save annotated snapshot image
                snapshot_filename = f"alert_{bin_obj.bin_id}_{int(now)}.jpg"
                snapshot_filepath = str(self.snapshots_dir / snapshot_filename)
                snapshot_bytes = None

                if annotated_frame is not None and annotated_frame.size > 0:
                    try:
                        cv2.imwrite(snapshot_filepath, annotated_frame)
                        _, buf = cv2.imencode(".jpg", annotated_frame)
                        snapshot_bytes = buf.tobytes()
                    except Exception as e:
                        logger.error(f"Error saving alert snapshot: {e}")

                smtp_dict = {
                    "smtp_host": email_settings.smtp_host if email_settings else settings.SMTP_HOST,
                    "smtp_port": email_settings.smtp_port if email_settings else settings.SMTP_PORT,
                    "smtp_username": email_settings.smtp_username if email_settings else settings.SMTP_USERNAME,
                    "smtp_password": email_settings.smtp_password if email_settings else settings.SMTP_PASSWORD,
                }

                # Send email
                result = EmailService.send_alert_email(
                    recipient_email=recipient,
                    bin_id=bin_obj.bin_id,
                    bin_name=bin_obj.name,
                    location=bin_obj.location,
                    fill_percentage=fill_percentage,
                    threshold=threshold,
                    snapshot_bytes=snapshot_bytes,
                    smtp_config=smtp_dict,
                    is_overflow=is_overflowing,
                    is_recurring=is_recurring,
                    alert_reason=trigger_reason
                )

                # Store alert record in database
                alert_status = "SENT" if result.get("success") and not result.get("simulated") else ("SIMULATED" if result.get("simulated") else "FAILED")
                alert_record = Alert(
                    bin_id=bin_obj.id,
                    bin_code=bin_obj.bin_id,
                    location=bin_obj.location,
                    fill_percentage=fill_percentage,
                    threshold=threshold,
                    recipient=recipient,
                    sent_at=datetime.datetime.utcnow(),
                    status=alert_status,
                    snapshot_path=snapshot_filename if snapshot_bytes else None,
                    message=trigger_reason
                )
                db.add(alert_record)
                db.commit()

                return {
                    "alert_triggered": True,
                    "status": alert_status,
                    "recipient": recipient,
                    "reason": trigger_reason,
                    "is_recurring": is_recurring
                }

        else:
            # Below threshold and no overflow. Only treat the bin as EMPTIED when the fill is
            # clearly lower and stays that way, so flickering readings don't restart alerts.
            if current_state == "CRITICAL":
                if fill_percentage > threshold - EMPTIED_MARGIN_PCT:
                    self.clear_since.pop(bin_id, None)
                else:
                    since = self.clear_since.setdefault(bin_id, now)
                    if now - since >= EMPTIED_CONFIRM_SECONDS:
                        self.bin_state[bin_id] = "NORMAL"
                        self.clear_since.pop(bin_id, None)
                        logger.info(
                            f"Bin {bin_obj.bin_id} has been EMPTIED (Fill: {fill_percentage:.1f}%). "
                            f"Alert state reset to NORMAL. Recurring mail transfer stopped."
                        )
            # Under normal conditions or once emptied, no email is sent.
            return None

    def trigger_manual_alert(self, db: Session, bin_obj: Dustbin, annotated_frame: Optional[np.ndarray] = None) -> Dict[str, Any]:
        """
        Force-triggers an alert immediately regardless of cooldown, useful for live demonstration.
        """
        now = time.time()
        self.last_alert_time[bin_obj.id] = now
        self.bin_state[bin_obj.id] = "CRITICAL"

        email_settings = db.query(EmailSetting).first()
        recipient = (email_settings.caretaker_email if email_settings and email_settings.caretaker_email else "caretaker@campus.org")
        
        snapshot_filename = f"manual_{bin_obj.bin_id}_{int(now)}.jpg"
        snapshot_filepath = str(self.snapshots_dir / snapshot_filename)
        snapshot_bytes = None

        if annotated_frame is not None and annotated_frame.size > 0:
            try:
                cv2.imwrite(snapshot_filepath, annotated_frame)
                _, buf = cv2.imencode(".jpg", annotated_frame)
                snapshot_bytes = buf.tobytes()
            except Exception as e:
                logger.error(f"Error saving manual alert snapshot: {e}")

        smtp_dict = {
            "smtp_host": email_settings.smtp_host if email_settings else settings.SMTP_HOST,
            "smtp_port": email_settings.smtp_port if email_settings else settings.SMTP_PORT,
            "smtp_username": email_settings.smtp_username if email_settings else settings.SMTP_USERNAME,
            "smtp_password": email_settings.smtp_password if email_settings else settings.SMTP_PASSWORD,
        }

        is_overflow = getattr(bin_obj, "floor_litter_detected", False) and getattr(bin_obj, "floor_litter_enabled", True)

        result = EmailService.send_alert_email(
            recipient_email=recipient,
            bin_id=bin_obj.bin_id,
            bin_name=bin_obj.name,
            location=bin_obj.location,
            fill_percentage=bin_obj.current_fill_percentage,
            threshold=bin_obj.threshold,
            snapshot_bytes=snapshot_bytes,
            smtp_config=smtp_dict,
            is_overflow=is_overflow,
            is_recurring=False,
            alert_reason="Manual Alert Dispatched by Administrator"
        )

        alert_status = "SENT" if result.get("success") and not result.get("simulated") else ("SIMULATED" if result.get("simulated") else "FAILED")
        alert_record = Alert(
            bin_id=bin_obj.id,
            bin_code=bin_obj.bin_id,
            location=bin_obj.location,
            fill_percentage=bin_obj.current_fill_percentage,
            threshold=bin_obj.threshold,
            recipient=recipient,
            sent_at=datetime.datetime.utcnow(),
            status=alert_status,
            snapshot_path=snapshot_filename if snapshot_bytes else None,
            message="Manual Alert Dispatched by Administrator"
        )
        db.add(alert_record)
        db.commit()

        return {
            "success": result.get("success", False),
            "status": alert_status,
            "recipient": recipient,
            "message": result.get("message", "Alert dispatched successfully.")
        }

alert_manager = AlertManager()
