from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.bin import Dustbin
from app.models.alert import Alert
from app.camera.camera_manager import camera_manager

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
    bins = db.query(Dustbin).all()
    total_bins = len(bins)

    online_cameras = 0
    critical_count = 0
    warning_count = 0
    normal_count = 0
    floor_litter_count = 0
    fill_sum = 0.0

    for b in bins:
        worker = camera_manager.get_worker(b.id)
        if worker:
            tel = worker.get_telemetry()
            current_fill = tel["fill_percentage"]
            is_online = tel["camera_online"]
            is_litter = tel["floor_litter_detected"]
        else:
            current_fill = b.current_fill_percentage
            is_online = b.camera_online
            is_litter = b.floor_litter_detected

        if is_online:
            online_cameras += 1
        if is_litter:
            floor_litter_count += 1

        fill_sum += current_fill
        threshold = b.threshold or 85.0
        if current_fill >= threshold:
            critical_count += 1
        elif current_fill >= 60.0:
            warning_count += 1
        else:
            normal_count += 1

    avg_fill = round(fill_sum / max(1, total_bins), 1)

    # Recent alerts
    recent_alerts = db.query(Alert).order_by(Alert.sent_at.desc()).limit(5).all()
    alerts_data = [
        {
            "id": a.id,
            "bin_id": a.bin_id,
            "bin_code": a.bin_code,
            "location": a.location,
            "fill_percentage": a.fill_percentage,
            "threshold": a.threshold,
            "recipient": a.recipient,
            "sent_at": a.sent_at.isoformat(),
            "status": a.status,
            "message": a.message
        }
        for a in recent_alerts
    ]

    return {
        "total_bins": total_bins,
        "online_cameras": online_cameras,
        "critical_bins": critical_count,
        "warning_bins": warning_count,
        "normal_bins": normal_count,
        "average_fill": avg_fill,
        "floor_litter_count": floor_litter_count,
        "recent_alerts": alerts_data
    }
