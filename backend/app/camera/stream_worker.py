import time
import threading
import datetime
import json
import numpy as np
import cv2
from typing import Optional, Dict, Any, List
from app.ai.detector import YOLODetector
from app.ai.fill_level import FillLevelEstimator
from app.ai.roi_manager import RoiManager
from app.ai.litter_detector import FloorLitterDetector
from app.ai.reference_store import ReferenceStore
from app.camera.capture_device import ResilientCameraCapture
from app.email.alert_manager import alert_manager
from app.database import SessionLocal
from app.models.bin import Dustbin
from app.models.reading import FillReading
from app.utils.logger import logger

class StreamWorker:
    """
    Continuous background camera capture and AI analysis worker for a single dustbin.
    Handles resilient reconnection, multi-strategy capture (IP Webcam, PC Webcam, Demo),
    dual-ROI inference, HUD overlay, and alert dispatch.
    """

    def __init__(self, bin_id_pk: int, bin_code: str, detector: YOLODetector):
        self.bin_id_pk = bin_id_pk
        self.bin_code = bin_code
        self.detector = detector
        self.fill_estimator = FillLevelEstimator(smoothing_factor=0.3)
        self.running = False
        self.thread: Optional[threading.Thread] = None

        # Camera state
        self.camera_online = False
        self.capture_device: Optional[ResilientCameraCapture] = None
        self.latest_raw_frame: Optional[np.ndarray] = None
        self.latest_annotated_frame: Optional[np.ndarray] = None
        self.latest_jpeg: Optional[bytes] = None
        self.lock = threading.Lock()

        # Telemetry
        self.current_fill = 0.0
        self.current_status = "NORMAL"
        self.floor_litter_detected = False
        self.litter_count = 0
        self.surface_coverage = 0.0
        self.fill_height = 0.0
        self.waste_boxes_count = 0
        self.detection_method = "detections"
        self.occluded = False
        self.has_reference = False
        self.fps = 0.0
        self.last_db_save = 0.0

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True, name=f"Worker-{self.bin_code}")
        self.thread.start()
        logger.info(f"Started monitoring stream worker for bin {self.bin_code} (ID: {self.bin_id_pk})")

    def stop(self):
        self.running = False
        if self.capture_device:
            self.capture_device.close()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        logger.info(f"Stopped monitoring stream worker for bin {self.bin_code}")

    def get_latest_jpeg(self) -> Optional[bytes]:
        with self.lock:
            return self.latest_jpeg

    def get_latest_annotated_frame(self) -> Optional[np.ndarray]:
        with self.lock:
            return self.latest_annotated_frame.copy() if self.latest_annotated_frame is not None else None

    def get_latest_raw_frame(self) -> Optional[np.ndarray]:
        with self.lock:
            return self.latest_raw_frame.copy() if self.latest_raw_frame is not None else None

    def get_telemetry(self) -> Dict[str, Any]:
        with self.lock:
            return {
                "bin_id": self.bin_code,
                "bin_pk": self.bin_id_pk,
                "camera_online": self.camera_online,
                "fill_percentage": self.current_fill,
                "status": self.current_status,
                "floor_litter_detected": self.floor_litter_detected,
                "litter_count": self.litter_count,
                "surface_coverage_pct": self.surface_coverage,
                "fill_height_pct": self.fill_height,
                "waste_boxes_count": self.waste_boxes_count,
                "detection_method": self.detection_method,
                "view_occluded": self.occluded,
                "has_empty_reference": self.has_reference,
                "fps": round(self.fps, 1),
                "timestamp": datetime.datetime.utcnow().isoformat()
            }

    def set_override(self, fill_pct: Optional[float]):
        if self.capture_device:
            self.capture_device.set_override(fill_pct)

    def _run_loop(self):
        reconnect_delay = 5.0
        last_url = None

        while self.running:
            # 1. Fetch current bin details from DB
            db = SessionLocal()
            bin_obj = None
            try:
                bin_obj = db.query(Dustbin).filter(Dustbin.id == self.bin_id_pk).first()
            except Exception as e:
                logger.error(f"Error fetching bin {self.bin_code} from DB: {e}")
            finally:
                db.close()

            if not bin_obj or not bin_obj.active:
                time.sleep(1.0)
                continue

            camera_url = (bin_obj.camera_url or "demo").strip()

            # 2. Check if we need to open or re-open the camera source
            if self.capture_device is None or last_url != camera_url:
                if self.capture_device:
                    self.capture_device.close()
                self.capture_device = ResilientCameraCapture(raw_source=camera_url, bin_id=self.bin_code)
                last_url = camera_url

                success = self.capture_device.open()
                if not success:
                    self.camera_online = False
                    logger.warning(f"Could not open camera stream '{camera_url}' for {self.bin_code}. Retrying in {reconnect_delay}s...")
                    time.sleep(reconnect_delay)
                    reconnect_delay = min(30.0, reconnect_delay * 1.5)
                    continue
                else:
                    self.camera_online = True
                    reconnect_delay = 5.0

            # 3. Read frames and run AI inference
            frame_width, frame_height = 640, 480
            bin_pts = RoiManager.parse_roi(bin_obj.bin_roi, frame_width, frame_height)
            floor_pts = RoiManager.parse_roi(bin_obj.floor_roi, frame_width, frame_height)

            consecutive_failures = 0
            reference = ReferenceStore.load(self.bin_id_pk)
            reference_mtime = ReferenceStore.mtime(self.bin_id_pk)
            last_config_check = time.time()

            while self.running:
                start_cycle = time.time()

                # Pick up calibration / settings changes live (every 2 s) instead of only on reconnect
                if start_cycle - last_config_check > 2.0:
                    last_config_check = start_cycle
                    db_cfg = SessionLocal()
                    try:
                        fresh = db_cfg.query(Dustbin).filter(Dustbin.id == self.bin_id_pk).first()
                        if fresh:
                            db_cfg.expunge(fresh)
                    except Exception as e:
                        fresh = None
                        logger.error(f"Error refreshing config for {self.bin_code}: {e}")
                    finally:
                        db_cfg.close()
                    if fresh is None or not fresh.active or (fresh.camera_url or "demo").strip() != camera_url:
                        break
                    if fresh.bin_roi != bin_obj.bin_roi or fresh.floor_roi != bin_obj.floor_roi:
                        bin_pts = RoiManager.parse_roi(fresh.bin_roi, frame_width, frame_height)
                        floor_pts = RoiManager.parse_roi(fresh.floor_roi, frame_width, frame_height)
                        logger.info(f"Applied updated ROI calibration for {self.bin_code}")
                    bin_obj = fresh
                    mtime = ReferenceStore.mtime(self.bin_id_pk)
                    if mtime != reference_mtime:
                        reference_mtime = mtime
                        reference = ReferenceStore.load(self.bin_id_pk)
                        logger.info(f"Empty-bin reference {'loaded' if reference is not None else 'cleared'} for {self.bin_code}")

                ret, frame = self.capture_device.read_frame()
                if not ret or frame is None or frame.size == 0:
                    consecutive_failures += 1
                    if consecutive_failures > 5:
                        logger.warning(f"Repeated frame acquisition failures for {self.bin_code}. Resetting capture...")
                        self.camera_online = False
                        self.capture_device.close()
                        self.capture_device = None
                        break
                    time.sleep(0.5)
                    continue

                consecutive_failures = 0
                self.camera_online = True
                frame = cv2.resize(frame, (frame_width, frame_height))

                with self.lock:
                    self.latest_raw_frame = frame.copy()

                # Run YOLO detection (waste items + people who may block the view)
                all_detections = self.detector.detect(frame, waste_only=True, include_occluders=True)
                detections = [d for d in all_detections if d["is_waste"]]
                occluders = [d for d in all_detections if not d["is_waste"]]

                # Fill level calculation (YOLO + pixel-level occupancy)
                fill_res = self.fill_estimator.calculate_fill(
                    frame_shape=frame.shape,
                    bin_pts=bin_pts,
                    detections=detections,
                    bin_key=self.bin_code,
                    frame=frame,
                    reference=reference,
                    occluders=occluders
                )
                fill_pct = fill_res["fill_percentage"]
                status = fill_res["status"]

                # Floor litter detection
                floor_res = FloorLitterDetector.detect_litter(
                    frame_shape=frame.shape,
                    floor_pts=floor_pts,
                    detections=detections,
                    bin_pts=bin_pts,
                    frame=frame,
                    reference=reference,
                    occluders=occluders
                )
                floor_litter = floor_res["floor_litter_detected"] and bin_obj.floor_litter_enabled

                # Draw Visual HUD Overlay
                annotated = frame.copy()
                annotated = RoiManager.draw_dual_roi_overlays(annotated, bin_pts, floor_pts, fill_pct, floor_litter)
                occ = fill_res["occupancy_mask"] > 0
                if np.any(occ):
                    # Highlight the pixels counted as waste
                    annotated[occ] = (annotated[occ] * 0.55 + np.array([0, 200, 255]) * 0.45).astype(np.uint8)
                annotated = self.detector.draw_detections(annotated, all_detections)
                annotated = self._draw_hud_banner(annotated, bin_obj, fill_pct, status, floor_litter)

                # Update JPEG buffer
                _, jpeg_buf = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 80])
                jpeg_bytes = jpeg_buf.tobytes()

                # Update internal telemetry
                now_ts = time.time()
                cycle_time = max(0.001, now_ts - start_cycle)
                calc_fps = 1.0 / cycle_time

                with self.lock:
                    self.latest_annotated_frame = annotated
                    self.latest_jpeg = jpeg_bytes
                    self.current_fill = fill_pct
                    self.current_status = status
                    self.floor_litter_detected = floor_litter
                    self.litter_count = floor_res["litter_count"]
                    self.surface_coverage = fill_res["surface_coverage_pct"]
                    self.fill_height = fill_res["estimated_fill_height_pct"]
                    self.waste_boxes_count = fill_res["waste_boxes_in_bin"]
                    self.detection_method = fill_res["method"]
                    self.occluded = fill_res["occluded"]
                    self.has_reference = reference is not None
                    self.fps = calc_fps

                # Alerting check
                db_alert = SessionLocal()
                try:
                    alert_bin = db_alert.query(Dustbin).filter(Dustbin.id == self.bin_id_pk).first()
                    if alert_bin:
                        alert_manager.process_bin_reading(
                            db=db_alert,
                            bin_obj=alert_bin,
                            fill_percentage=fill_pct,
                            annotated_frame=annotated,
                            floor_litter_detected=floor_litter
                        )
                except Exception as ex:
                    logger.error(f"Alert processing error for {self.bin_code}: {ex}")
                finally:
                    db_alert.close()

                # Periodic Database state update (every 15 seconds)
                if (now_ts - self.last_db_save) > 15.0:
                    self.last_db_save = now_ts
                    db_save = SessionLocal()
                    try:
                        b = db_save.query(Dustbin).filter(Dustbin.id == self.bin_id_pk).first()
                        if b:
                            b.current_fill_percentage = fill_pct
                            b.current_status = status
                            b.floor_litter_detected = floor_litter
                            b.camera_online = self.camera_online
                            b.last_reading_time = datetime.datetime.utcnow()

                            reading = FillReading(
                                bin_id=b.id,
                                fill_percentage=fill_pct,
                                floor_litter_detected=floor_litter,
                                waste_boxes_count=fill_res["waste_boxes_in_bin"],
                                timestamp=datetime.datetime.utcnow()
                            )
                            db_save.add(reading)
                            db_save.commit()
                    except Exception as e:
                        logger.error(f"Error persisting reading for {self.bin_code}: {e}")
                    finally:
                        db_save.close()

                # Frame throttle
                target_sleep = max(0.01, (1.0 / 8.0) - (time.time() - start_cycle))
                time.sleep(target_sleep)

        if self.capture_device:
            self.capture_device.close()
        logger.info(f"Stream worker terminated for {self.bin_code}")

    def _draw_hud_banner(
        self,
        frame: np.ndarray,
        bin_obj: Dustbin,
        fill_pct: float,
        status: str,
        floor_litter: bool
    ) -> np.ndarray:
        h, w = frame.shape[:2]

        # Top Bar
        top_bar = np.zeros((36, w, 3), dtype=np.uint8)
        top_bar[:] = (15, 23, 42)
        frame[0:36, 0:w] = cv2.addWeighted(frame[0:36, 0:w], 0.2, top_bar, 0.8, 0)

        dot_color = (0, 0, 255) if status == "CRITICAL" else ((0, 165, 255) if status == "WARNING" else (0, 255, 128))
        cv2.circle(frame, (18, 18), 7, dot_color, -1)
        cv2.putText(frame, f"{bin_obj.bin_id} | {bin_obj.name}", (34, 23),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, (241, 245, 249), 1, cv2.LINE_AA)

        ai_state = "VIEW BLOCKED" if self.occluded else ("AI: REF" if self.has_reference else "AI: ACTIVE")
        hud_right = f"FILL: {fill_pct:.1f}% [{status}] | {ai_state}"
        (tw, _), _ = cv2.getTextSize(hud_right, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
        cv2.putText(frame, hud_right, (w - tw - 15, 23),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, dot_color, 1, cv2.LINE_AA)

        # Bottom Bar
        bot_bar = np.zeros((26, w, 3), dtype=np.uint8)
        bot_bar[:] = (15, 23, 42)
        frame[h-26:h, 0:w] = cv2.addWeighted(frame[h-26:h, 0:w], 0.2, bot_bar, 0.8, 0)
        
        litter_text = "FLOOR OVERFLOW: DETECTED" if floor_litter else "FLOOR: CLEAN"
        litter_color = (0, 50, 255) if floor_litter else (0, 255, 128)
        cv2.putText(frame, litter_text, (15, h - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, litter_color, 1, cv2.LINE_AA)
        
        loc_text = f"LOC: {bin_obj.location[:30]}"
        cv2.putText(frame, loc_text, (w - 240, h - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, (148, 163, 184), 1, cv2.LINE_AA)

        return frame
