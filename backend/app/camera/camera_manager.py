import time
import threading
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from app.models.bin import Dustbin
from app.ai.detector import YOLODetector
from app.camera.stream_worker import StreamWorker
from app.camera.capture_device import CameraSourceManager
from app.utils.logger import logger
from app.config import settings

class CameraManager:
    """
    Central manager for multi-camera streams, worker lifecycles, and camera diagnostics.
    """

    def __init__(self):
        self.workers: Dict[int, StreamWorker] = {}
        self.lock = threading.Lock()
        self.detector = YOLODetector(model_path=settings.YOLO_MODEL_PATH)
        self.initialized = False

    def initialize(self, db: Session):
        with self.lock:
            if self.initialized:
                return
            self.initialized = True
            
            bins = db.query(Dustbin).filter(Dustbin.active == True).all()
            logger.info(f"Initializing CameraManager with {len(bins)} active bins...")
            for b in bins:
                worker = StreamWorker(bin_id_pk=b.id, bin_code=b.bin_id, detector=self.detector)
                self.workers[b.id] = worker
                worker.start()

    def start_bin_worker(self, bin_id_pk: int, bin_code: str):
        with self.lock:
            if bin_id_pk in self.workers:
                self.workers[bin_id_pk].stop()
            worker = StreamWorker(bin_id_pk=bin_id_pk, bin_code=bin_code, detector=self.detector)
            self.workers[bin_id_pk] = worker
            worker.start()

    def stop_bin_worker(self, bin_id_pk: int):
        with self.lock:
            if bin_id_pk in self.workers:
                worker = self.workers.pop(bin_id_pk)
                worker.stop()

    def get_worker(self, bin_id_pk: int) -> Optional[StreamWorker]:
        with self.lock:
            return self.workers.get(bin_id_pk)

    def get_worker_by_code(self, bin_code: str) -> Optional[StreamWorker]:
        with self.lock:
            for w in self.workers.values():
                if w.bin_code == bin_code:
                    return w
            return None

    def get_all_telemetry(self) -> List[Dict[str, Any]]:
        with self.lock:
            return [w.get_telemetry() for w in self.workers.values()]

    def test_camera_connection(self, camera_url: str, protocol: str = "http") -> Dict[str, Any]:
        """
        Tests whether the camera stream URL or webcam is accessible with detailed diagnostics.
        """
        return CameraSourceManager.test_connection(camera_url)

    def shutdown(self):
        with self.lock:
            logger.info("Shutting down CameraManager workers...")
            for worker in self.workers.values():
                worker.stop()
            self.workers.clear()
            self.initialized = False

camera_manager = CameraManager()
