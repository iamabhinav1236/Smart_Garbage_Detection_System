import numpy as np
import cv2
from typing import List, Dict, Any, Tuple, Optional
from app.ai.roi_manager import RoiManager
from app.ai.fill_level import boxes_mask, change_mask, clean_mask

class FloorLitterDetector:
    """
    Detects floor litter and overflowing garbage outside the dustbin using Floor ROI.

    The bin interior is always excluded from the floor zone, so waste inside the bin is
    never reported as litter. When an empty-scene reference image exists, new blobs on the
    floor are detected as well (catches litter YOLO has no class for).
    """

    @staticmethod
    def detect_litter(
        frame_shape: Tuple[int, int],
        floor_pts: np.ndarray,
        detections: List[Dict[str, Any]],
        bin_pts: Optional[np.ndarray] = None,
        frame: Optional[np.ndarray] = None,
        reference: Optional[np.ndarray] = None,
        occluders: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Calculates whether any waste objects are detected on the surrounding floor ROI.
        """
        empty = {"floor_litter_detected": False, "litter_count": 0, "litter_coverage_pct": 0.0}
        if len(floor_pts) < 3:
            return empty

        h, w = frame_shape[:2]
        floor_mask = np.zeros((h, w), dtype=np.uint8)
        cv2.fillPoly(floor_mask, [floor_pts], 255)
        if bin_pts is not None and len(bin_pts) >= 3:
            # Exclude the bin itself (dilated slightly to skip its outline)
            bin_mask = np.zeros((h, w), dtype=np.uint8)
            cv2.fillPoly(bin_mask, [bin_pts], 255)
            bin_mask = cv2.dilate(bin_mask, np.ones((7, 7), np.uint8))
            floor_mask = cv2.bitwise_and(floor_mask, cv2.bitwise_not(bin_mask))

        floor_area = max(1.0, float(cv2.countNonZero(floor_mask)))
        litter_mask = np.zeros((h, w), dtype=np.uint8)
        litter_count = 0

        for det in detections:
            single = boxes_mask(frame_shape, [det])
            box_area = max(1.0, float(cv2.countNonZero(single)))
            inter_area = float(cv2.countNonZero(cv2.bitwise_and(floor_mask, single)))
            # At least 15% of the object and a meaningful number of pixels on the floor zone
            if inter_area > 150 and (inter_area / box_area) > 0.15:
                litter_count += 1
                litter_mask = cv2.bitwise_or(litter_mask, single)

        if frame is not None and reference is not None and reference.shape == frame.shape:
            changed = change_mask(frame, reference, floor_mask, threshold=28.0)
            changed = cv2.bitwise_and(changed, floor_mask)
            changed = cv2.bitwise_and(changed, cv2.bitwise_not(boxes_mask(frame_shape, occluders or [])))
            changed = cv2.bitwise_and(changed, cv2.bitwise_not(litter_mask))
            changed = clean_mask(changed, min_area=max(120, int(floor_area * 0.003)))
            n_blobs, _ = cv2.connectedComponents(changed)
            litter_count += n_blobs - 1
            litter_mask = cv2.bitwise_or(litter_mask, changed)

        overlap = cv2.bitwise_and(floor_mask, litter_mask)
        coverage_pct = round(float(cv2.countNonZero(overlap)) / floor_area * 100.0, 2)

        return {
            "floor_litter_detected": litter_count > 0,
            "litter_count": litter_count,
            "litter_coverage_pct": coverage_pct
        }
