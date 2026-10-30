import os
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.alert import Alert
from app.schemas.alert import AlertResponse
from app.config import settings

router = APIRouter(prefix="/alerts", tags=["Alerts"])

@router.get("", response_model=List[AlertResponse])
def get_alerts(
    status_filter: Optional[str] = Query(None, description="ALL, SENT, FAILED, SIMULATED"),
    bin_id: Optional[int] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    query = db.query(Alert)
    if bin_id:
        query = query.filter(Alert.bin_id == bin_id)
    if status_filter and status_filter.upper() != "ALL":
        query = query.filter(Alert.status == status_filter.upper())
    
    alerts = query.order_by(Alert.sent_at.desc()).limit(limit).all()
    return alerts

@router.get("/{id}/snapshot")
def get_alert_snapshot(id: int, db: Session = Depends(get_db)):
    alert = db.query(Alert).filter(Alert.id == id).first()
    if not alert or not alert.snapshot_path:
        raise HTTPException(status_code=404, detail="Alert snapshot not found")

    filepath = os.path.join(settings.SNAPSHOTS_DIR, alert.snapshot_path)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Snapshot file missing on disk")

    return FileResponse(filepath, media_type="image/jpeg")
