import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from typing import Optional, Dict, Any
from app.utils.logger import logger
from app.config import settings

class EmailService:
    """
    SMTP Email notification service supporting Gmail App Password,
    TLS/SSL, rich HTML formatting, and embedded camera snapshot attachments.
    """

    @staticmethod
    def send_alert_email(
        recipient_email: str,
        bin_id: str,
        bin_name: str,
        location: str,
        fill_percentage: float,
        threshold: float,
        snapshot_bytes: Optional[bytes] = None,
        smtp_config: Optional[Dict[str, Any]] = None,
        is_overflow: bool = False,
        is_recurring: bool = False,
        alert_reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Sends formatted urgent alert email to the caretaker with attached annotated frame.
        Includes support for threshold breaches, overflow detection, and 15-minute recurring reminders.
        """
        # Resolve SMTP configuration from passed dict or app settings
        config = smtp_config or {}
        smtp_host = config.get("smtp_host") or settings.SMTP_HOST
        smtp_port = int(config.get("smtp_port") or settings.SMTP_PORT)
        smtp_user = config.get("smtp_username") or settings.SMTP_USERNAME
        smtp_pass = config.get("smtp_password") or settings.SMTP_PASSWORD
        sender = smtp_user or "alerts@smartgarbage.local"

        if not recipient_email:
            return {"success": False, "message": "Recipient email address not provided."}

        # Format Subject Line
        prefix = "[15-MIN RECURRING REMINDER] " if is_recurring else ""
        if is_overflow and fill_percentage >= threshold:
            subject = f"{prefix}URGENT: Bin {bin_id} FILL LEVEL CRITICAL ({fill_percentage:.1f}%) & OVERFLOWING"
        elif is_overflow:
            subject = f"{prefix}URGENT: Bin {bin_id} OVERFLOW DETECTED (Garbage Outside Bin)"
        else:
            subject = f"{prefix}URGENT: Bin {bin_id} Reached {fill_percentage:.1f}% Fill Level"

        # Badge and Status Text
        if is_recurring:
            badge_text = "15-MIN REMINDER - STILL NOT EMPTIED"
            badge_bg = "#dc2626"
            header_title = "Action Required: Dustbin Still Not Emptied"
            subtitle_text = "This dustbin has exceeded operational limits and has not been cleared for over 15 minutes."
        elif is_overflow:
            badge_text = "OVERFLOW DETECTED"
            badge_bg = "#b91c1c"
            header_title = "Dustbin Overflow / Littering Detected"
            subtitle_text = "Garbage overflow detected outside the dustbin perimeter."
        else:
            badge_text = "CRITICAL FILL LEVEL ALERT"
            badge_bg = "#ef4444"
            header_title = "Smart Dustbin Fill Level Exceeded"
            subtitle_text = "AI Powered Real-Time Waste Surveillance System"

        if is_overflow and fill_percentage >= threshold:
            status_text = "FILL LEVEL CRITICAL & OVERFLOWING"
        elif is_overflow:
            status_text = "OVERFLOW DETECTED (WASTE OUTSIDE BIN)"
        else:
            status_text = f"FILL LEVEL CRITICAL (>= {threshold}%)"

        reason_display = alert_reason or f"Fill level reached {fill_percentage:.1f}% (Threshold: {threshold}%)"

        if is_recurring:
            reminder_notice = """
            <div style="background: rgba(220, 38, 38, 0.25); border: 1px solid #ef4444; border-radius: 8px; padding: 14px 18px; margin-bottom: 20px; color: #fca5a5; font-size: 14px;">
              <strong>RECURRING REMINDER:</strong> This dustbin remains full or overflowing and has <u>not been emptied</u>. Recurring notifications will continue every 15 minutes until the dustbin is serviced and emptied.
            </div>
            """
        else:
            reminder_notice = """
            <div style="background: rgba(59, 130, 246, 0.15); border: 1px solid #3b82f6; border-radius: 8px; padding: 12px 16px; margin-bottom: 20px; color: #93c5fd; font-size: 13px;">
              <strong>AUTOMATIC COOLDOWN:</strong> If this bin is not emptied, automatic reminder emails will be sent every 15 minutes. Once emptied, emails stop immediately.
            </div>
            """

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0f172a; color: #f8fafc; margin: 0; padding: 24px; }}
            .card {{ background: #1e293b; border-radius: 12px; padding: 28px; max-width: 600px; margin: 0 auto; border: 1px solid #334155; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }}
            .header {{ display: flex; align-items: center; border-bottom: 2px solid {badge_bg}; padding-bottom: 16px; margin-bottom: 20px; }}
            .badge {{ background: {badge_bg}; color: #fff; padding: 6px 14px; border-radius: 9999px; font-weight: 700; font-size: 13px; letter-spacing: 0.05em; }}
            h2 {{ color: #ffffff; margin: 0 0 4px 0; font-size: 22px; }}
            .subtitle {{ color: #94a3b8; font-size: 14px; margin-bottom: 24px; }}
            .metric-box {{ background: #0f172a; border-radius: 8px; padding: 16px; margin-bottom: 20px; border-left: 4px solid {badge_bg}; }}
            .metric-val {{ font-size: 32px; font-weight: 800; color: #f87171; }}
            table {{ width: 100%; border-collapse: collapse; margin-bottom: 24px; }}
            th, td {{ padding: 10px 12px; text-align: left; border-bottom: 1px solid #334155; font-size: 14px; }}
            th {{ color: #94a3b8; font-weight: 600; width: 35%; }}
            td {{ color: #f1f5f9; font-weight: 500; }}
            .action {{ background: {badge_bg}; color: #ffffff; text-align: center; padding: 14px; border-radius: 8px; font-weight: bold; margin-top: 10px; }}
            .footer {{ font-size: 12px; color: #64748b; margin-top: 24px; text-align: center; }}
          </style>
        </head>
        <body>
          <div class="card">
            <div class="header">
              <span class="badge">{badge_text}</span>
            </div>
            <h2>{header_title}</h2>
            <div class="subtitle">{subtitle_text}</div>

            {reminder_notice}

            <div class="metric-box">
              <div style="font-size: 13px; color: #94a3b8; text-transform: uppercase;">Current Fill Level</div>
              <div class="metric-val">{fill_percentage:.1f}% <span style="font-size: 16px; color: #ef4444;">(Threshold: {threshold}%)</span></div>
            </div>

            <table>
              <tr><th>Bin ID</th><td>{bin_id}</td></tr>
              <tr><th>Bin Name</th><td>{bin_name}</td></tr>
              <tr><th>Location</th><td>{location}</td></tr>
              <tr><th>Status</th><td><strong style="color: #ef4444;">{status_text}</strong></td></tr>
              <tr><th>Alert Reason</th><td>{reason_display}</td></tr>
              <tr><th>Overflow Detected</th><td><strong style="color: {'#ef4444' if is_overflow else '#22c55e'};">{'YES' if is_overflow else 'NO'}</strong></td></tr>
              <tr><th>Notification Type</th><td>{'Recurring (every 15 min until emptied)' if is_recurring else 'Initial Breach Alert'}</td></tr>
              <tr><th>Timestamp</th><td>{import_datetime().strftime('%Y-%m-%d %H:%M:%S UTC')}</td></tr>
            </table>

            <div class="action">
              ACTION REQUIRED: Please dispatch sanitation staff immediately to empty this dustbin.
            </div>

            <div class="footer">
              This is an automated AI alert dispatched by the Smart Garbage Detection System.
            </div>
          </div>
        </body>
        </html>
        """

        msg = MIMEMultipart("related")
        msg["Subject"] = subject
        msg["From"] = f"Smart Garbage System <{sender}>"
        msg["To"] = recipient_email

        msg_alternative = MIMEMultipart("alternative")
        msg.attach(msg_alternative)

        # Plain text fallback
        plain_body = (
            f"{'[RECURRING 15-MIN REMINDER - STILL NOT EMPTIED] ' if is_recurring else ''}URGENT ALERT: "
            f"Bin {bin_id} ({bin_name}) at {location}. {reason_display}. Status: {status_text}. "
            f"Please service immediately. Recurring reminders will be sent every 15 minutes until the dustbin is emptied."
        )
        msg_alternative.attach(MIMEText(plain_body, "plain"))
        msg_alternative.attach(MIMEText(html_body, "html"))

        # Attach snapshot if present
        if snapshot_bytes:
            image_attachment = MIMEImage(snapshot_bytes, name=f"snapshot_{bin_id}.jpg")
            image_attachment.add_header("Content-Disposition", f'attachment; filename="snapshot_{bin_id}.jpg"')
            msg.attach(image_attachment)

        # If credentials are not set (e.g. initial setup without SMTP configured yet),
        # return informative status so user can see it in logs or simulate
        if not smtp_user or not smtp_pass:
            logger.warning(f"SMTP credentials not fully configured. Email simulated for {recipient_email}: {subject}")
            return {
                "success": True,
                "simulated": True,
                "message": "Email alert logged (SMTP password/user not set; configured in demo/simulated mode)."
            }

        try:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=12) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(smtp_user, smtp_pass)
                server.sendmail(sender, [recipient_email], msg.as_string())
            logger.info(f"Alert email sent successfully to {recipient_email} for bin {bin_id}")
            return {"success": True, "simulated": False, "message": "Email sent successfully."}
        except Exception as e:
            logger.error(f"Failed to send email to {recipient_email}: {e}")
            return {"success": False, "simulated": False, "message": str(e)}

    @staticmethod
    def send_test_email(recipient_email: str, smtp_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Sends a test verification email to confirm SMTP connectivity.
        """
        config = smtp_config or {}
        smtp_host = config.get("smtp_host") or settings.SMTP_HOST
        smtp_port = int(config.get("smtp_port") or settings.SMTP_PORT)
        smtp_user = config.get("smtp_username") or settings.SMTP_USERNAME
        smtp_pass = config.get("smtp_password") or settings.SMTP_PASSWORD
        sender = smtp_user or "test@smartgarbage.local"

        if not smtp_user or not smtp_pass:
            return {
                "success": False,
                "message": "SMTP Username or App Password is missing. Please configure credentials before sending test email."
            }

        msg = MIMEMultipart()
        msg["Subject"] = "Test Notification - Smart Garbage Detection System"
        msg["From"] = f"Smart Garbage System <{sender}>"
        msg["To"] = recipient_email

        body = (
            "Hello,\n\n"
            "This is a test notification confirming that your SMTP settings and email alerts "
            "for the Smart Garbage Detection System are configured correctly and active.\n\n"
            "System: AI-Powered Smart Garbage Detection System\n"
            "Status: Online & Operational"
        )
        msg.attach(MIMEText(body, "plain"))

        try:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(smtp_user, smtp_pass)
                server.sendmail(sender, [recipient_email], msg.as_string())
            return {"success": True, "message": "Test email sent successfully!"}
        except Exception as e:
            return {"success": False, "message": f"SMTP Connection Failed: {str(e)}"}

def import_datetime():
    import datetime
    return datetime.datetime.utcnow()
