import time
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.camera.camera_manager import camera_manager
import cv2
import numpy as np

router = APIRouter(prefix="/stream", tags=["Video Streaming"])

def generate_mjpeg_stream(bin_id: int):
    blank_frame = np.full((480, 640, 3), (25, 30, 36), dtype=np.uint8)
    cv2.putText(blank_frame, "CONNECTING TO CAMERA...", (160, 240),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (150, 160, 170), 2)
    _, blank_jpeg = cv2.imencode(".jpg", blank_frame)
    blank_bytes = blank_jpeg.tobytes()

    while True:
        worker = camera_manager.get_worker(bin_id)
        if worker:
            frame_bytes = worker.get_latest_jpeg()
            if frame_bytes is not None:
                yield (b"--frame\r\n"
                       b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n")
            else:
                yield (b"--frame\r\n"
                       b"Content-Type: image/jpeg\r\n\r\n" + blank_bytes + b"\r\n")
        else:
            yield (b"--frame\r\n"
                   b"Content-Type: image/jpeg\r\n\r\n" + blank_bytes + b"\r\n")
        time.sleep(0.08)  # ~12 FPS stream rate for smooth web playback

@router.get("/{bin_id}")
def stream_bin_video(bin_id: int):
    """
    Live MJPEG camera stream with YOLOv8 object bounding boxes,
    dual-ROI overlays, and HUD metadata.
    """
    return StreamingResponse(
        generate_mjpeg_stream(bin_id),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )
