import cv2
import json
import numpy as np
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.bin import Dustbin
from app.models.reading import FillReading
from app.schemas.bin import (
    BinCreate, BinUpdate, BinResponse, RoiUpdate,
    CameraTestRequest, CameraTestResponse, ReadingResponse
)
from app.camera.camera_manager import camera_manager
from app.camera.capture_device import CameraSourceManager
from app.email.alert_manager import alert_manager
from app.ai.reference_store import ReferenceStore
from app.utils.logger import logger

router = APIRouter(prefix="/bins", tags=["Dustbins"])

class OverrideRequest(BaseModel):
    fill_percentage: Optional[float] = None

@router.get("", response_model=List[BinResponse])
def get_all_bins(db: Session = Depends(get_db)):
    bins = db.query(Dustbin).all()
    results = []
    for b in bins:
        worker = camera_manager.get_worker(b.id)
        if worker:
            telemetry = worker.get_telemetry()
            b.current_fill_percentage = telemetry["fill_percentage"]
            b.current_status = telemetry["status"]
            b.floor_litter_detected = telemetry["floor_litter_detected"]
            b.camera_online = telemetry["camera_online"]
        results.append(b)
    return results

@router.post("", response_model=BinResponse, status_code=status.HTTP_201_CREATED)
def create_bin(bin_data: BinCreate, db: Session = Depends(get_db)):
    existing = db.query(Dustbin).filter(Dustbin.bin_id == bin_data.bin_id).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"A dustbin with ID '{bin_data.bin_id}' already exists.")

    # Automatically normalize camera URL
    canonical_url, _ = CameraSourceManager.normalize_url(bin_data.camera_url)

    new_bin = Dustbin(
        bin_id=bin_data.bin_id,
        name=bin_data.name,
        location=bin_data.location,
        camera_url=str(canonical_url),
        camera_protocol=bin_data.camera_protocol,
        threshold=bin_data.threshold,
        description=bin_data.description or "",
        active=bin_data.active,
        floor_litter_enabled=bin_data.floor_litter_enabled,
        current_fill_percentage=0.0,
        current_status="NORMAL",
        floor_litter_detected=False,
        camera_online=False
    )
    db.add(new_bin)
    db.commit()
    db.refresh(new_bin)

    if new_bin.active:
        camera_manager.start_bin_worker(new_bin.id, new_bin.bin_id)

    logger.info(f"Created new dustbin: {new_bin.bin_id} ({new_bin.name}) with camera URL '{new_bin.camera_url}'")
    return new_bin

@router.get("/{id}", response_model=BinResponse)
def get_bin(id: int, db: Session = Depends(get_db)):
    bin_obj = db.query(Dustbin).filter(Dustbin.id == id).first()
    if not bin_obj:
        raise HTTPException(status_code=404, detail="Dustbin not found")

    worker = camera_manager.get_worker(bin_obj.id)
    if worker:
        telemetry = worker.get_telemetry()
        bin_obj.current_fill_percentage = telemetry["fill_percentage"]
        bin_obj.current_status = telemetry["status"]
        bin_obj.floor_litter_detected = telemetry["floor_litter_detected"]
        bin_obj.camera_online = telemetry["camera_online"]

    return bin_obj

@router.put("/{id}", response_model=BinResponse)
def update_bin(id: int, update_data: BinUpdate, db: Session = Depends(get_db)):
    bin_obj = db.query(Dustbin).filter(Dustbin.id == id).first()
    if not bin_obj:
        raise HTTPException(status_code=404, detail="Dustbin not found")

    url_changed = False
    if update_data.name is not None:
        bin_obj.name = update_data.name
    if update_data.location is not None:
        bin_obj.location = update_data.location
    if update_data.camera_url is not None:
        canonical_url, _ = CameraSourceManager.normalize_url(update_data.camera_url)
        canonical_str = str(canonical_url)
        if canonical_str != bin_obj.camera_url:
            bin_obj.camera_url = canonical_str
            url_changed = True
    if update_data.camera_protocol is not None:
        bin_obj.camera_protocol = update_data.camera_protocol
    if update_data.threshold is not None:
        bin_obj.threshold = update_data.threshold
    if update_data.description is not None:
        bin_obj.description = update_data.description
    if update_data.floor_litter_enabled is not None:
        bin_obj.floor_litter_enabled = update_data.floor_litter_enabled
    if update_data.active is not None:
        bin_obj.active = update_data.active

    db.commit()
    db.refresh(bin_obj)

    # Manage worker
    if not bin_obj.active:
        camera_manager.stop_bin_worker(bin_obj.id)
    elif url_changed or bin_obj.id not in camera_manager.workers:
        camera_manager.start_bin_worker(bin_obj.id, bin_obj.bin_id)

    logger.info(f"Updated dustbin {bin_obj.bin_id}")
    return bin_obj

@router.delete("/{id}")
def delete_bin(id: int, db: Session = Depends(get_db)):
    bin_obj = db.query(Dustbin).filter(Dustbin.id == id).first()
    if not bin_obj:
        raise HTTPException(status_code=404, detail="Dustbin not found")

    camera_manager.stop_bin_worker(bin_obj.id)
    ReferenceStore.delete(bin_obj.id)
    db.delete(bin_obj)
    db.commit()

    logger.info(f"Deleted dustbin ID {id}")
    return {"message": "Dustbin deleted successfully", "id": id}

@router.post("/test-camera-url", response_model=CameraTestResponse)
def test_camera_url(test_req: CameraTestRequest):
    result = camera_manager.test_camera_connection(test_req.camera_url, test_req.camera_protocol)
    return CameraTestResponse(**result)

@router.post("/{id}/test-camera", response_model=CameraTestResponse)
def test_bin_camera(id: int, db: Session = Depends(get_db)):
    bin_obj = db.query(Dustbin).filter(Dustbin.id == id).first()
    if not bin_obj:
        raise HTTPException(status_code=404, detail="Dustbin not found")
    result = camera_manager.test_camera_connection(bin_obj.camera_url, bin_obj.camera_protocol)
    return CameraTestResponse(**result)

@router.post("/{id}/start")
def start_bin_monitoring(id: int, db: Session = Depends(get_db)):
    bin_obj = db.query(Dustbin).filter(Dustbin.id == id).first()
    if not bin_obj:
        raise HTTPException(status_code=404, detail="Dustbin not found")
    bin_obj.active = True
    db.commit()
    camera_manager.start_bin_worker(bin_obj.id, bin_obj.bin_id)
    return {"message": f"Monitoring started for bin {bin_obj.bin_id}", "active": True}

@router.post("/{id}/stop")
def stop_bin_monitoring(id: int, db: Session = Depends(get_db)):
    bin_obj = db.query(Dustbin).filter(Dustbin.id == id).first()
    if not bin_obj:
        raise HTTPException(status_code=404, detail="Dustbin not found")
    bin_obj.active = False
    db.commit()
    camera_manager.stop_bin_worker(bin_obj.id)
    return {"message": f"Monitoring stopped for bin {bin_obj.bin_id}", "active": False}

@router.get("/{id}/status")
def get_bin_live_status(id: int):
    worker = camera_manager.get_worker(id)
    if not worker:
        return {"online": False, "status": "OFFLINE", "fill_percentage": 0.0}
    return worker.get_telemetry()

@router.get("/{id}/readings", response_model=List[ReadingResponse])
def get_bin_readings(id: int, limit: int = 50, db: Session = Depends(get_db)):
    readings = db.query(FillReading).filter(FillReading.bin_id == id).order_by(FillReading.timestamp.desc()).limit(limit).all()
    return list(reversed(readings))

@router.post("/{id}/roi")
def update_bin_roi(id: int, roi_data: RoiUpdate, db: Session = Depends(get_db)):
    bin_obj = db.query(Dustbin).filter(Dustbin.id == id).first()
    if not bin_obj:
        raise HTTPException(status_code=404, detail="Dustbin not found")
    if roi_data.bin_roi is not None:
        bin_obj.bin_roi = roi_data.bin_roi
    if roi_data.floor_roi is not None:
        bin_obj.floor_roi = roi_data.floor_roi
    db.commit()
    return {"message": "ROI calibrated successfully", "bin_roi": bin_obj.bin_roi, "floor_roi": bin_obj.floor_roi}

@router.get("/{id}/frame")
def get_bin_calibration_frame(id: int, db: Session = Depends(get_db)):
    worker = camera_manager.get_worker(id)
    raw_frame = None
    if worker:
        raw_frame = worker.get_latest_raw_frame()

    if raw_frame is None or raw_frame.size == 0:
        raw_frame = np.full((480, 640, 3), (35, 42, 48), dtype=np.uint8)
        cv2.putText(raw_frame, "CONNECTING TO CAMERA...", (150, 240),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)

    _, jpeg = cv2.imencode(".jpg", raw_frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return Response(content=jpeg.tobytes(), media_type="image/jpeg")

@router.get("/{id}/empty-reference")
def get_empty_reference_info(id: int):
    return ReferenceStore.info(id)

@router.post("/{id}/empty-reference")
def capture_empty_reference(id: int, db: Session = Depends(get_db)):
    """Saves the current camera frame as the 'empty bin' baseline used by the fill estimator."""
    if not db.query(Dustbin).filter(Dustbin.id == id).first():
        raise HTTPException(status_code=404, detail="Dustbin not found")
    worker = camera_manager.get_worker(id)
    frame = worker.get_latest_raw_frame() if worker else None
    if frame is None or frame.size == 0:
        raise HTTPException(status_code=409, detail="No live camera frame available. Start monitoring and wait for the camera to connect.")
    ReferenceStore.save(id, frame)
    logger.info(f"Captured empty-bin reference for bin {id}")
    return {"message": "Empty-bin reference captured", **ReferenceStore.info(id)}

@router.delete("/{id}/empty-reference")
def clear_empty_reference(id: int):
    ReferenceStore.delete(id)
    return {"message": "Empty-bin reference cleared", **ReferenceStore.info(id)}

@router.post("/{id}/override")
def override_fill_level(id: int, req: OverrideRequest):
    worker = camera_manager.get_worker(id)
    if not worker:
        raise HTTPException(status_code=404, detail="Stream worker not active")
    worker.set_override(req.fill_percentage)
    return {"message": "Override applied", "fill_percentage": req.fill_percentage}

@router.post("/{id}/trigger-alert")
def trigger_immediate_alert(id: int, db: Session = Depends(get_db)):
    bin_obj = db.query(Dustbin).filter(Dustbin.id == id).first()
    if not bin_obj:
        raise HTTPException(status_code=404, detail="Dustbin not found")
    worker = camera_manager.get_worker(id)
    annotated = worker.get_latest_annotated_frame() if worker else None
    res = alert_manager.trigger_manual_alert(db, bin_obj, annotated)
    return res
