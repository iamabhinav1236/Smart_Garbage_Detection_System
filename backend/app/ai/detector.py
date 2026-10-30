import os
import ast
from typing import List, Dict, Any, Optional
import cv2
import numpy as np
from app.utils.logger import logger
from app.config import settings

# 80 standard COCO class names
COCO_CLASSES = [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat", "traffic light",
    "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat", "dog", "horse", "sheep", "cow",
    "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella", "handbag", "tie", "suitcase", "frisbee",
    "skis", "snowboard", "sports ball", "kite", "baseball bat", "baseball glove", "skateboard", "surfboard",
    "tennis racket", "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana", "apple",
    "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair", "couch",
    "potted plant", "bed", "dining table", "toilet", "tv", "laptop", "mouse", "remote", "keyboard", "cell phone",
    "microwave", "oven", "toaster", "sink", "refrigerator", "book", "clock", "vase", "scissors", "teddy bear",
    "hair drier", "toothbrush"
]

# COCO classes that commonly correspond to discarded waste. Plastic bags and wrappers are
# frequently recognised by COCO models as "kite", "umbrella" or "handbag", so those are included.
WASTE_COCO_CLASSES = {
    "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl",
    "banana", "apple", "sandwich", "orange", "broccoli", "carrot", "hot dog",
    "pizza", "donut", "cake", "backpack", "handbag", "suitcase", "umbrella", "kite",
    "book", "vase", "cell phone", "remote", "mouse", "scissors", "teddy bear",
    "toothbrush", "sports ball", "frisbee"
}

# Classes that block the camera's view of the bin (used for occlusion handling)
OCCLUDER_CLASSES = {"person"}

LETTERBOX_COLOR = (114, 114, 114)


class YOLODetector:
    """
    Production-grade YOLOv8 Detector wrapper using ONNXRuntime and OpenCV DNN.
    Compatible with custom Roboflow-trained waste detection models or default YOLOv8.

    If the ONNX model carries its own class names (Ultralytics exports do) and they are not
    the 80 COCO classes, the model is treated as a dedicated garbage model and every class
    it predicts counts as waste.
    """

    def __init__(self, model_path: str = None, conf_threshold: float = None, nms_threshold: float = 0.45):
        self.model_path = model_path or settings.YOLO_MODEL_PATH
        self.conf_threshold = conf_threshold if conf_threshold is not None else settings.CONFIDENCE_THRESHOLD
        self.nms_threshold = nms_threshold
        self.input_size = (640, 640)
        self.classes = COCO_CLASSES
        self.session = None
        self.input_name = None
        self.net = None
        self._load_model()
        self._build_class_index()

    def _load_model(self):
        try:
            import onnxruntime as ort
            if os.path.exists(self.model_path):
                opts = ort.SessionOptions()
                opts.intra_op_num_threads = 2
                self.session = ort.InferenceSession(self.model_path, opts, providers=["CPUExecutionProvider"])
                model_input = self.session.get_inputs()[0]
                self.input_name = model_input.name
                shape = model_input.shape
                if len(shape) == 4 and isinstance(shape[2], int) and isinstance(shape[3], int):
                    self.input_size = (shape[3], shape[2])
                self._read_class_names()
                logger.info(f"YOLOv8 ONNX model loaded successfully via ONNXRuntime from {self.model_path}")
                return
        except Exception as e:
            logger.warning(f"Failed to load via ONNXRuntime: {e}. Falling back to cv2.dnn")

        try:
            if os.path.exists(self.model_path):
                self.net = cv2.dnn.readNetFromONNX(self.model_path)
                logger.info(f"YOLOv8 ONNX loaded via cv2.dnn from {self.model_path}")
        except Exception as e:
            logger.error(f"Failed to load model from {self.model_path}: {e}")

    def _read_class_names(self):
        """Reads class names embedded in Ultralytics ONNX exports (metadata key 'names')."""
        try:
            meta = self.session.get_modelmeta().custom_metadata_map
            names = ast.literal_eval(meta.get("names", ""))
            if isinstance(names, dict) and names:
                self.classes = [str(names[i]) for i in sorted(names)]
        except Exception:
            pass

    def _build_class_index(self):
        self.is_custom_model = self.classes != COCO_CLASSES
        if self.is_custom_model:
            # Dedicated garbage model: every class is waste
            self.waste_ids = np.arange(len(self.classes))
            logger.info(f"Custom waste model detected with {len(self.classes)} classes: {self.classes}")
        else:
            self.waste_ids = np.array([i for i, c in enumerate(self.classes) if c in WASTE_COCO_CLASSES])
        self.occluder_ids = np.array([i for i, c in enumerate(self.classes) if c in OCCLUDER_CLASSES], dtype=int)

    def _letterbox(self, frame: np.ndarray):
        """Resizes keeping aspect ratio and pads to the model input size (as YOLOv8 was trained)."""
        h, w = frame.shape[:2]
        in_w, in_h = self.input_size
        r = min(in_w / w, in_h / h)
        new_w, new_h = int(round(w * r)), int(round(h * r))
        pad_x, pad_y = (in_w - new_w) // 2, (in_h - new_h) // 2
        resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        canvas = np.full((in_h, in_w, 3), LETTERBOX_COLOR, dtype=np.uint8)
        canvas[pad_y:pad_y + new_h, pad_x:pad_x + new_w] = resized
        return canvas, r, pad_x, pad_y

    def _infer(self, blob: np.ndarray) -> Optional[np.ndarray]:
        if self.session is not None:
            try:
                return self.session.run(None, {self.input_name: blob})[0]
            except Exception as e:
                logger.error(f"ONNXRuntime inference error: {e}")
        elif self.net is not None:
            try:
                self.net.setInput(blob)
                return self.net.forward()
            except Exception as e:
                logger.error(f"cv2.dnn inference error: {e}")
        return None

    def detect(self, frame: np.ndarray, waste_only: bool = True, include_occluders: bool = False) -> List[Dict[str, Any]]:
        """
        Runs object detection on input frame.
        Returns list of detection dictionaries:
        [{ "box": [x1, y1, x2, y2], "confidence": float, "class_name": str, "class_id": int, "is_waste": bool }]

        waste_only: only waste classes are scored, so a waste item is not lost when a
                    non-waste class happens to score slightly higher on the same anchor.
        include_occluders: also return people, so callers can tell when the bin is blocked.
        """
        if frame is None or frame.size == 0:
            return []

        h, w = frame.shape[:2]
        padded, ratio, pad_x, pad_y = self._letterbox(frame)
        blob = cv2.dnn.blobFromImage(padded, scalefactor=1.0 / 255.0, swapRB=True, crop=False)

        outputs = self._infer(blob)
        if outputs is None:
            return []

        # YOLOv8 output tensor format: [1, (4 + num_classes), 8400] -> [8400, (4 + num_classes)]
        predictions = outputs[0]
        if predictions.shape[0] < predictions.shape[1]:
            predictions = predictions.T

        scores = predictions[:, 4:]
        if waste_only:
            allowed = self.waste_ids
            if include_occluders and len(self.occluder_ids):
                allowed = np.concatenate([allowed, self.occluder_ids])
            allowed = allowed[allowed < scores.shape[1]]
        else:
            allowed = np.arange(scores.shape[1])
        if len(allowed) == 0:
            return []

        sub_scores = scores[:, allowed]
        best = np.argmax(sub_scores, axis=1)
        confidences = sub_scores[np.arange(len(sub_scores)), best]
        class_ids = allowed[best]

        keep = confidences >= self.conf_threshold
        if not np.any(keep):
            return []
        boxes_cxcywh = predictions[keep, :4]
        confidences = confidences[keep]
        class_ids = class_ids[keep]

        # Undo letterbox: model coords -> original frame coords
        cx, cy, bw, bh = boxes_cxcywh.T
        x1 = np.clip((cx - bw / 2 - pad_x) / ratio, 0, w)
        y1 = np.clip((cy - bh / 2 - pad_y) / ratio, 0, h)
        x2 = np.clip((cx + bw / 2 - pad_x) / ratio, 0, w)
        y2 = np.clip((cy + bh / 2 - pad_y) / ratio, 0, h)

        valid = ((x2 - x1) > 5) & ((y2 - y1) > 5)
        if not np.any(valid):
            return []
        x1, y1, x2, y2 = x1[valid], y1[valid], x2[valid], y2[valid]
        confidences, class_ids = confidences[valid], class_ids[valid]

        nms_boxes = np.stack([x1, y1, x2 - x1, y2 - y1], axis=1).astype(int).tolist()
        # Class-agnostic NMS: one physical item should not count as two overlapping classes
        indices = cv2.dnn.NMSBoxes(nms_boxes, confidences.astype(float).tolist(), self.conf_threshold, self.nms_threshold)

        detections = []
        for i in np.array(indices).flatten():
            cid = int(class_ids[i])
            cname = self.classes[cid] if cid < len(self.classes) else f"class_{cid}"
            detections.append({
                "box": [int(x1[i]), int(y1[i]), int(x2[i]), int(y2[i])],
                "confidence": float(confidences[i]),
                "class_name": cname,
                "class_id": cid,
                "is_waste": cname not in OCCLUDER_CLASSES or self.is_custom_model
            })
        return detections

    def draw_detections(self, frame: np.ndarray, detections: List[Dict[str, Any]]) -> np.ndarray:
        for det in detections:
            x1, y1, x2, y2 = det["box"]
            conf = det["confidence"]
            name = det["class_name"]

            # Emerald for waste items, slate for people/occluders
            color = (0, 255, 128) if det.get("is_waste", True) else (184, 163, 148)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

            label = f"{name} {conf:.2f}"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            ly = max(th + 6, y1)
            cv2.rectangle(frame, (x1, ly - th - 6), (x1 + tw + 6, ly), color, -1)
            cv2.putText(frame, label, (x1 + 3, ly - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)
        return frame
