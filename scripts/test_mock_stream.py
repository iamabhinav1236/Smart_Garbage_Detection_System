import time
import os
import sys

# Ensure backend directory is in python path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
sys.path.insert(0, backend_dir)

from app.camera.mock_stream import MockStreamGenerator
from app.ai.detector import YOLODetector
from app.ai.fill_level import FillLevelEstimator
from app.ai.roi_manager import RoiManager
from app.ai.litter_detector import FloorLitterDetector
from app.config import settings

def main():
    print("=" * 60)
    print("Testing Mock Stream Generator & YOLOv8 Detection Pipeline")
    print("=" * 60)

    generator = MockStreamGenerator(bin_id="TEST-001")
    detector = YOLODetector(model_path=settings.YOLO_MODEL_PATH)
    estimator = FillLevelEstimator()

    bin_roi = RoiManager.parse_roi("[[160, 140], [480, 140], [530, 420], [110, 420]]", 640, 480)
    floor_roi = RoiManager.parse_roi("[[40, 400], [600, 400], [620, 470], [20, 470]]", 640, 480)

    print("Generating 10 frames and running inference...")
    for i in range(10):
        t0 = time.time()
        frame = generator.get_frame()
        detections = detector.detect(frame, waste_only=True)
        fill_res = estimator.calculate_fill(frame.shape, bin_roi, detections, bin_key="TEST-001")
        floor_res = FloorLitterDetector.detect_litter(frame.shape, floor_roi, detections)
        dt = (time.time() - t0) * 1000.0

        print(f"Frame #{i+1:02d} | Time: {dt:.1f}ms | Detections: {len(detections)} | "
              f"Fill Level: {fill_res['fill_percentage']}% ({fill_res['status']}) | "
              f"Floor Litter: {'DETECTED' if floor_res['floor_litter_detected'] else 'CLEAR'}")
        time.sleep(0.2)

    print("\nSUCCESS: AI Pipeline test completed without errors!")

if __name__ == "__main__":
    main()
