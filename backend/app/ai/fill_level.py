from collections import deque
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
import cv2
from app.ai.roi_manager import RoiManager


def boxes_mask(shape: Tuple[int, int], detections: List[Dict[str, Any]]) -> np.ndarray:
    """Binary mask (255) covering all detection boxes."""
    h, w = shape[:2]
    mask = np.zeros((h, w), dtype=np.uint8)
    for det in detections:
        x1, y1, x2, y2 = det["box"]
        x1, y1, x2, y2 = max(0, int(x1)), max(0, int(y1)), min(w, int(x2)), min(h, int(y2))
        if x2 > x1 and y2 > y1:
            mask[y1:y2, x1:x2] = 255
    return mask


def change_mask(frame: np.ndarray, reference: np.ndarray, roi_mask: np.ndarray, threshold: float = 22.0) -> np.ndarray:
    """
    Pixels that differ from the empty-bin reference image, in LAB colour space.
    Brightness is compensated using the area outside the ROI, so a cloud or a light
    switching on does not register as garbage.
    """
    cur = cv2.cvtColor(cv2.GaussianBlur(frame, (5, 5), 0), cv2.COLOR_BGR2LAB).astype(np.float32)
    ref = cv2.cvtColor(cv2.GaussianBlur(reference, (5, 5), 0), cv2.COLOR_BGR2LAB).astype(np.float32)

    outside = roi_mask == 0
    if np.count_nonzero(outside) > 1000:
        cur[..., 0] += float(np.median(ref[..., 0][outside] - cur[..., 0][outside]))

    diff = np.abs(cur - ref)
    # Lightness changes are weighted lower than colour changes (shadows, reflections)
    score = np.maximum(diff[..., 0] * 0.5, np.maximum(diff[..., 1], diff[..., 2]) * 1.2)
    return ((score > threshold).astype(np.uint8) * 255)


def texture_mask(frame: np.ndarray) -> np.ndarray:
    """
    Reference-free clutter detection: garbage piles are dense in edges and colour variation,
    while an empty bin interior/liner is comparatively smooth.
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    edges = cv2.Canny(gray, 40, 120)
    density = cv2.blur(edges.astype(np.float32) / 255.0, (17, 17))

    # Local colour variation (saturation std) catches smooth coloured items such as bottles
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV).astype(np.float32)
    sat = hsv[..., 1]
    mean = cv2.blur(sat, (17, 17))
    var = cv2.blur(sat * sat, (17, 17)) - mean * mean
    sat_std = np.sqrt(np.clip(var, 0, None))

    return (((density > 0.06) | (sat_std > 28)).astype(np.uint8) * 255)


def clean_mask(mask: np.ndarray, min_area: int) -> np.ndarray:
    """Morphological clean-up and removal of tiny noise blobs."""
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    n, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    out = np.zeros_like(mask)
    for i in range(1, n):
        if stats[i, cv2.CC_STAT_AREA] >= min_area:
            out[labels == i] = 255
    return out


class FillLevelEstimator:
    """
    Hybrid Fill-Level Estimator for the Bin Interior ROI.

    Combines two independent signals into one occupancy mask:
      1. YOLOv8 waste detections (recognised objects: bottles, cups, food, bags...)
      2. Pixel-level occupancy: change vs. an empty-bin reference image when one has been
         captured (most accurate), otherwise edge/colour texture analysis.

    From the mask it computes surface coverage and the height of the waste pile (from a
    row-occupancy profile, robust to a single stray box), then smooths over time with a
    median filter + EMA. Frames where a person blocks the bin are held, not measured.
    """

    def __init__(self, smoothing_factor: float = 0.3, window: int = 7):
        self.smoothing_factor = smoothing_factor
        self.window = window
        self.history: Dict[str, float] = {}
        self.raw_windows: Dict[str, deque] = {}

    @staticmethod
    def default_bin_roi(frame_shape: Tuple[int, int]) -> np.ndarray:
        h, w = frame_shape[:2]
        return np.array([
            [int(w * 0.25), int(h * 0.35)],
            [int(w * 0.75), int(h * 0.35)],
            [int(w * 0.80), int(h * 0.90)],
            [int(w * 0.20), int(h * 0.90)]
        ], dtype=np.int32)

    def calculate_fill(
        self,
        frame_shape: Tuple[int, int],
        bin_pts: np.ndarray,
        detections: List[Dict[str, Any]],
        bin_key: str = "default",
        frame: Optional[np.ndarray] = None,
        reference: Optional[np.ndarray] = None,
        occluders: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Estimates the dustbin fill percentage inside bin_pts.
        Returns:
        {
            "fill_percentage": float,
            "raw_percentage": float,
            "surface_coverage_pct": float,
            "estimated_fill_height_pct": float,
            "waste_boxes_in_bin": int,
            "method": "reference" | "texture" | "detections",
            "occluded": bool,
            "status": "NORMAL" | "WARNING" | "CRITICAL",
            "occupancy_mask": np.ndarray (full-frame, 255 = waste inside bin)
        }
        """
        h, w = frame_shape[:2]
        if len(bin_pts) < 3:
            bin_pts = self.default_bin_roi(frame_shape)

        bin_mask = np.zeros((h, w), dtype=np.uint8)
        cv2.fillPoly(bin_mask, [bin_pts], 255)
        bin_area = max(1.0, float(cv2.countNonZero(bin_mask)))

        bin_min_y = int(np.clip(np.min(bin_pts[:, 1]), 0, h - 1))
        bin_max_y = int(np.clip(np.max(bin_pts[:, 1]), 0, h - 1))
        bin_height = max(1.0, float(bin_max_y - bin_min_y))

        # Occlusion: a person standing in front of the bin makes the frame unreliable
        occluder_mask = boxes_mask(frame_shape, occluders or [])
        occluded_px = float(cv2.countNonZero(cv2.bitwise_and(occluder_mask, bin_mask)))
        occluded = occluded_px / bin_area > 0.30

        # 1. YOLO detections that sit mostly inside the bin
        waste_in_bin = []
        for det in detections:
            single = boxes_mask(frame_shape, [det])
            box_px = max(1.0, float(cv2.countNonZero(single)))
            inter = float(cv2.countNonZero(cv2.bitwise_and(single, bin_mask)))
            if inter / box_px >= 0.4:
                waste_in_bin.append(det)
        det_mask = cv2.bitwise_and(boxes_mask(frame_shape, waste_in_bin), bin_mask)

        # 2. Pixel-level occupancy. The ROI is eroded so the bin rim/edges are not counted.
        method = "detections"
        visual = np.zeros((h, w), dtype=np.uint8)
        if frame is not None and frame.shape[:2] == (h, w):
            inner = cv2.erode(bin_mask, np.ones((9, 9), np.uint8))
            if reference is not None and reference.shape == frame.shape:
                visual = change_mask(frame, reference, bin_mask)
                method = "reference"
            else:
                visual = texture_mask(frame)
                method = "texture"
            visual = cv2.bitwise_and(visual, inner)
            visual = cv2.bitwise_and(visual, cv2.bitwise_not(occluder_mask))
            visual = clean_mask(visual, min_area=max(40, int(bin_area * 0.004)))

        occupancy = cv2.bitwise_or(det_mask, visual)
        occupied = float(cv2.countNonZero(occupancy))
        surface_coverage_pct = min(100.0, occupied / bin_area * 100.0)

        # Pile height from the row profile: waste piles up from the bottom, so walk upwards from
        # the bottom of the bin while rows are occupied (small gaps tolerated). Isolated bands
        # higher up (bin rim, a hand, a reflection) are not counted as fill.
        height_fill_pct = 0.0
        band_density = 0.0
        if occupied > 0:
            rows_occ = np.count_nonzero(occupancy[bin_min_y:bin_max_y + 1], axis=1).astype(np.float32)
            rows_roi = np.count_nonzero(bin_mask[bin_min_y:bin_max_y + 1], axis=1).astype(np.float32)
            frac = rows_occ / np.maximum(rows_roi, 1.0)
            frac = np.convolve(frac, np.ones(9) / 9.0, mode="same")
            filled = frac >= 0.10
            max_gap = max(3, int(len(frac) * 0.08))
            # The bottom few rows may be hidden by the eroded ROI edge, so start just above them
            top_idx, gap = None, 0
            for i in range(len(frac) - 1, -1, -1):
                if filled[i]:
                    top_idx, gap = i, 0
                elif top_idx is not None or i < len(frac) - max_gap * 2:
                    gap += 1
                    if gap > max_gap:
                        break
            if top_idx is not None:
                waste_top = bin_min_y + top_idx
                height_fill_pct = (bin_max_y - waste_top) / bin_height * 100.0
                band_density = float(rows_occ[top_idx:].sum() / max(1.0, rows_roi[top_idx:].sum()))

        # Height is what "full" means. A very sparse band (e.g. one tall stick) is scaled down.
        raw_fill = height_fill_pct * min(1.0, band_density / 0.12) if occupied > 0 else 0.0
        raw_fill = float(np.clip(raw_fill, 0.0, 100.0))

        prev_fill = self.history.get(bin_key)
        if occluded and prev_fill is not None:
            smoothed_fill = prev_fill
        else:
            # Median over a short window rejects single-frame spikes, EMA keeps it smooth
            win = self.raw_windows.setdefault(bin_key, deque(maxlen=self.window))
            win.append(raw_fill)
            median_raw = float(np.median(win))
            if prev_fill is None:
                prev_fill = median_raw
            smoothed_fill = (self.smoothing_factor * median_raw) + ((1.0 - self.smoothing_factor) * prev_fill)
        smoothed_fill = round(float(np.clip(smoothed_fill, 0.0, 100.0)), 1)
        self.history[bin_key] = smoothed_fill

        if smoothed_fill >= 85.0:
            status = "CRITICAL"
        elif smoothed_fill >= 60.0:
            status = "WARNING"
        else:
            status = "NORMAL"

        return {
            "fill_percentage": smoothed_fill,
            "raw_percentage": round(raw_fill, 1),
            "surface_coverage_pct": round(surface_coverage_pct, 1),
            "estimated_fill_height_pct": round(height_fill_pct, 1),
            "waste_boxes_in_bin": len(waste_in_bin),
            "method": method,
            "occluded": occluded,
            "status": status,
            "occupancy_mask": occupancy
        }
