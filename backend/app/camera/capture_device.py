import re
import socket
import time
import urllib.parse
from typing import Optional, Tuple, Any, List, Union
import cv2
import numpy as np
import requests
from app.utils.logger import logger
from app.camera.mock_stream import MockStreamGenerator

class CameraSourceManager:
    """
    Intelligent camera source resolver and multi-strategy frame grabber.
    Supports:
    - Android IP Webcam (auto-resolves IP, port, /video, /shot.jpg)
    - DroidCam / IPCam (/videofeed, :4747)
    - Built-in / USB Webcams (0, 1, 'webcam')
    - RTSP streams (rtsp://...)
    - Synthetic Demo generator ('demo')
    """

    @staticmethod
    def normalize_url(raw_input: str) -> Tuple[str, List[Union[str, int]]]:
        """
        Takes raw user input and returns:
        (canonical_display_url, list_of_ordered_candidates_to_try)
        """
        if not raw_input:
            return "demo", ["demo"]

        trimmed = raw_input.strip()

        # Check for local webcam index
        if trimmed in ("0", "1", "2") or trimmed.lower() in ("webcam", "pc", "builtin", "camera0"):
            idx = int(trimmed) if trimmed.isdigit() else 0
            return f"Webcam (Device {idx})", [idx]

        if trimmed.lower() in ("demo", "mock", "test", "simulated"):
            return "demo", ["demo"]

        # If it's RTSP, preserve RTSP
        if trimmed.lower().startswith("rtsp://"):
            return trimmed, [trimmed]

        # Ensure scheme
        url = trimmed
        if not (url.startswith("http://") or url.startswith("https://")):
            url = "http://" + url

        try:
            parsed = urllib.parse.urlparse(url)
            host = parsed.hostname or ""
            port = parsed.port
            path = parsed.path or ""
        except Exception:
            return trimmed, [trimmed]

        # If port is missing and it's a private IP address, default IP Webcam port is 8080
        if not port:
            port = 8080
            netloc = f"{host}:{port}"
        else:
            netloc = f"{host}:{port}"

        candidates = []
        # If user already typed /video or /shot.jpg or /videofeed
        if path and len(path) > 1:
            candidates.append(f"http://{netloc}{path}")
            if not path.endswith("/video"):
                candidates.append(f"http://{netloc}/video")
            if not path.endswith("/shot.jpg"):
                candidates.append(f"http://{netloc}/shot.jpg")
        else:
            # Common IP Webcam paths
            candidates.append(f"http://{netloc}/video")
            candidates.append(f"http://{netloc}/shot.jpg")
            candidates.append(f"http://{netloc}/videofeed")
            candidates.append(f"http://{netloc}")

        canonical = candidates[0]
        return canonical, candidates

    @staticmethod
    def test_connection(raw_input: str) -> dict:
        """
        Diagnoses network connectivity and attempts to read a test frame.
        Provides clear, actionable error messages.
        """
        canonical, candidates = CameraSourceManager.normalize_url(raw_input)

        # 1. Local Webcam
        if isinstance(candidates[0], int):
            idx = candidates[0]
            try:
                cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
                if cap.isOpened():
                    ret, frame = cap.read()
                    cap.release()
                    if ret and frame is not None:
                        return {
                            "online": True,
                            "resolved_url": f"Webcam (Device {idx})",
                            "status": "Camera Online",
                            "message": f"Successfully connected to PC Webcam (Device {idx}) - Frame: {frame.shape[1]}x{frame.shape[0]}.",
                            "latency_ms": 25.0
                        }
                return {
                    "online": False,
                    "resolved_url": f"Webcam (Device {idx})",
                    "status": "Camera Offline",
                    "message": f"Could not access PC Webcam {idx}. Ensure no other application (e.g. Zoom, Teams) is using it.",
                    "latency_ms": None
                }
            except Exception as e:
                return {
                    "online": False,
                    "resolved_url": f"Webcam (Device {idx})",
                    "status": "Camera Offline",
                    "message": f"Webcam error: {str(e)}",
                    "latency_ms": None
                }

        # 2. Demo mode
        if candidates[0] == "demo":
            return {
                "online": True,
                "resolved_url": "demo",
                "status": "Online (Demo Mode)",
                "message": "Demo mode simulated stream is operational.",
                "latency_ms": 10.0
            }

        # 3. Network URL / IP Camera
        start_time = time.time()
        parsed = urllib.parse.urlparse(candidates[0])
        host = parsed.hostname or ""
        port = parsed.port or 80

        # TCP ping check first for quick, accurate diagnostic
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2.5)
            res = sock.connect_ex((host, port))
            sock.close()
            if res != 0:
                return {
                    "online": False,
                    "resolved_url": candidates[0],
                    "status": "Camera Offline",
                    "message": f"Cannot reach {host}:{port}. Ensure your phone is connected to the same Wi-Fi network and IP Webcam is running (tap 'Start server').",
                    "latency_ms": None
                }
        except Exception as e:
            return {
                "online": False,
                "resolved_url": candidates[0],
                "status": "Camera Offline",
                "message": f"Network address resolution failed for '{host}': {str(e)}",
                "latency_ms": None
            }

        # Try candidates for working video frame
        for cand in candidates:
            try:
                # If /shot.jpg endpoint: test HTTP GET
                if cand.endswith(".jpg"):
                    r = requests.get(cand, timeout=3.0)
                    if r.status_code == 200 and len(r.content) > 1000:
                        latency = round((time.time() - start_time) * 1000.0, 1)
                        return {
                            "online": True,
                            "resolved_url": cand,
                            "status": "Camera Online",
                            "message": f"Successfully retrieved camera snapshot from {cand}.",
                            "latency_ms": latency
                        }
                else:
                    # Test via OpenCV
                    cap = cv2.VideoCapture(cand)
                    if cap.isOpened():
                        ret, frame = cap.read()
                        cap.release()
                        if ret and frame is not None:
                            latency = round((time.time() - start_time) * 1000.0, 1)
                            return {
                                "online": True,
                                "resolved_url": cand,
                                "status": "Camera Online",
                                "message": f"Connected to live stream at {cand} ({frame.shape[1]}x{frame.shape[0]}).",
                                "latency_ms": latency
                            }
            except Exception:
                continue

        return {
            "online": False,
            "resolved_url": candidates[0],
            "status": "Camera Offline",
            "message": f"Connected to {host}:{port}, but could not decode video stream. Make sure to use 'http://{host}:{port}/video'.",
            "latency_ms": round((time.time() - start_time) * 1000.0, 1)
        }


class ResilientCameraCapture:
    """
    Manages continuous video capture with automatic protocol fallback:
    1. DirectShow / VideoCapture (webcam or RTSP)
    2. OpenCV HTTP VideoCapture
    3. Direct HTTP MJPEG stream chunk parser
    4. HTTP Snapshot (/shot.jpg) poller
    5. Synthetic Demo generator fallback
    """

    def __init__(self, raw_source: str, bin_id: str = "BIN-001"):
        self.raw_source = raw_source
        self.bin_id = bin_id
        self.canonical_url, self.candidates = CameraSourceManager.normalize_url(raw_source)
        self.cap: Optional[cv2.VideoCapture] = None
        self.mock_generator: Optional[MockStreamGenerator] = None
        self.active_mode = "NONE" # "OPENCV", "MJPEG_STREAM", "SNAPSHOT", "DEMO"
        self.active_url: Optional[str] = None
        self.http_stream_response = None
        self.http_stream_bytes = b""
        self.last_shot_time = 0.0

    def open(self) -> bool:
        self.close()

        # Check demo mode
        if self.candidates[0] == "demo":
            self.mock_generator = MockStreamGenerator(bin_id=self.bin_id)
            self.active_mode = "DEMO"
            return True

        # Check local webcam
        if isinstance(self.candidates[0], int):
            idx = self.candidates[0]
            try:
                self.cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
                if self.cap.isOpened():
                    self.active_mode = "OPENCV"
                    logger.info(f"Opened local PC webcam device index {idx} for {self.bin_id}")
                    return True
            except Exception as e:
                logger.error(f"Error opening webcam device {idx}: {e}")
            return False

        # Try candidates via OpenCV
        for cand in self.candidates:
            if cand.endswith(".jpg"):
                continue  # reserve for snapshot fallback
            try:
                cap = cv2.VideoCapture(cand)
                if cap.isOpened():
                    ret, _ = cap.read()
                    if ret:
                        self.cap = cap
                        self.active_url = cand
                        self.active_mode = "OPENCV"
                        logger.info(f"Connected OpenCV stream to {cand} for {self.bin_id}")
                        return True
                    else:
                        cap.release()
            except Exception:
                continue

        # Try Direct HTTP MJPEG Stream or Snapshot endpoint
        for cand in self.candidates:
            if cand.endswith("/video") or cand.endswith("/videofeed"):
                try:
                    r = requests.get(cand, stream=True, timeout=4.0)
                    if r.status_code == 200:
                        self.http_stream_response = r
                        self.http_stream_bytes = b""
                        self.active_url = cand
                        self.active_mode = "MJPEG_STREAM"
                        logger.info(f"Connected Direct HTTP MJPEG stream to {cand} for {self.bin_id}")
                        return True
                except Exception:
                    continue

        for cand in self.candidates:
            if cand.endswith("/shot.jpg") or not cand.endswith("/video"):
                shot_url = cand if cand.endswith("/shot.jpg") else cand.rstrip("/") + "/shot.jpg"
                try:
                    r = requests.get(shot_url, timeout=3.0)
                    if r.status_code == 200 and len(r.content) > 1000:
                        self.active_url = shot_url
                        self.active_mode = "SNAPSHOT"
                        logger.info(f"Connected Snapshot stream to {shot_url} for {self.bin_id}")
                        return True
                except Exception:
                    continue

        return False

    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        if self.active_mode == "DEMO":
            if not self.mock_generator:
                self.mock_generator = MockStreamGenerator(bin_id=self.bin_id)
            return True, self.mock_generator.get_frame()

        if self.active_mode == "OPENCV" and self.cap:
            try:
                ret, frame = self.cap.read()
                if ret and frame is not None and frame.size > 0:
                    return True, frame
            except Exception:
                pass
            return False, None

        if self.active_mode == "SNAPSHOT" and self.active_url:
            now = time.time()
            if (now - self.last_shot_time) >= 0.1:  # max 10 FPS
                self.last_shot_time = now
                try:
                    r = requests.get(self.active_url, timeout=2.0)
                    if r.status_code == 200 and len(r.content) > 1000:
                        nparr = np.frombuffer(r.content, np.uint8)
                        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                        if frame is not None:
                            return True, frame
                except Exception:
                    pass
            return False, None

        if self.active_mode == "MJPEG_STREAM" and self.http_stream_response:
            try:
                for chunk in self.http_stream_response.iter_content(chunk_size=4096):
                    self.http_stream_bytes += chunk
                    a = self.http_stream_bytes.find(b"\xff\xd8")  # JPEG start
                    b = self.http_stream_bytes.find(b"\xff\xd9")  # JPEG end
                    if a != -1 and b != -1 and b > a:
                        jpg = self.http_stream_bytes[a:b+2]
                        self.http_stream_bytes = self.http_stream_bytes[b+2:]
                        nparr = np.frombuffer(jpg, np.uint8)
                        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                        if frame is not None:
                            return True, frame
            except Exception:
                pass
            return False, None

        return False, None

    def set_override(self, fill_pct: Optional[float]):
        if self.mock_generator:
            self.mock_generator.set_override(fill_pct)

    def close(self):
        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None

        if self.http_stream_response:
            try:
                self.http_stream_response.close()
            except Exception:
                pass
            self.http_stream_response = None

        self.active_mode = "NONE"
        self.active_url = None
