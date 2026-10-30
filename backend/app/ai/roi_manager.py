import json
import numpy as np
import cv2
from typing import List, Tuple, Optional

class RoiManager:
    """
    Manages dual-ROI coordinates (Bin Interior ROI and Floor ROI)
    Handles coordinate normalization, polygon point tests, area math, and overlay drawing.
    """

    @staticmethod
    def parse_roi(roi_str: str, frame_width: int, frame_height: int) -> np.ndarray:
        """
        Parses JSON ROI string into pixel coordinate array np.ndarray of shape (N, 2).
        Supports either:
        - normalized coordinates [[0.2, 0.2], [0.8, 0.2], ...]
        - absolute pixel coordinates [[120, 100], [480, 100], ...]
        """
        if not roi_str or roi_str.strip() == "":
            return np.array([], dtype=np.int32)
        try:
            pts = json.loads(roi_str)
            if not isinstance(pts, list) or len(pts) < 3:
                return np.array([], dtype=np.int32)
            
            coords = []
            for pt in pts:
                x, y = float(pt[0]), float(pt[1])
                # If coordinates are normalized (<= 1.0), scale to image size
                if x <= 1.0 and y <= 1.0 and frame_width > 1 and frame_height > 1:
                    px = int(x * frame_width)
                    py = int(y * frame_height)
                else:
                    px = int(x)
                    py = int(y)
                coords.append([px, py])
            return np.array(coords, dtype=np.int32)
        except Exception:
            return np.array([], dtype=np.int32)

    @staticmethod
    def polygon_area(pts: np.ndarray) -> float:
        if len(pts) < 3:
            return 0.0
        return float(cv2.contourArea(pts))

    @staticmethod
    def box_polygon_intersection_area(box: List[int], polygon_pts: np.ndarray, frame_shape: Tuple[int, int]) -> float:
        """
        Calculates intersection area between a bounding box [x1, y1, x2, y2]
        and a polygon ROI using binary mask bitwise AND.
        """
        if len(polygon_pts) < 3:
            return 0.0
        
        h, w = frame_shape[:2]
        poly_mask = np.zeros((h, w), dtype=np.uint8)
        cv2.fillPoly(poly_mask, [polygon_pts], 255)

        x1, y1, x2, y2 = max(0, int(box[0])), max(0, int(box[1])), min(w, int(box[2])), min(h, int(box[3]))
        if x2 <= x1 or y2 <= y1:
            return 0.0

        box_mask = np.zeros((h, w), dtype=np.uint8)
        box_mask[y1:y2, x1:x2] = 255

        intersection = cv2.bitwise_and(poly_mask, box_mask)
        return float(cv2.countNonZero(intersection))

    @staticmethod
    def draw_dual_roi_overlays(
        frame: np.ndarray,
        bin_pts: np.ndarray,
        floor_pts: np.ndarray,
        fill_pct: float,
        floor_litter: bool
    ) -> np.ndarray:
        """
        Draws glowing cyber/smart-city style HUD outlines and status labels
        over the Bin ROI and Floor ROI.
        """
        overlay = frame.copy()

        # 1. Bin Interior ROI
        if len(bin_pts) >= 3:
            # Color depends on fill percentage: Green -> Amber -> Bright Red
            if fill_pct >= 85.0:
                bin_color = (0, 0, 255)       # Red (Critical)
                tint_color = (0, 0, 180)
            elif fill_pct >= 60.0:
                bin_color = (0, 165, 255)     # Amber/Orange (Warning)
                tint_color = (0, 100, 200)
            else:
                bin_color = (0, 255, 128)     # Emerald Green (Normal)
                tint_color = (0, 150, 80)

            # Draw transparent fill
            cv2.fillPoly(overlay, [bin_pts], tint_color)
            cv2.addWeighted(overlay, 0.25, frame, 0.75, 0, frame)
            # Draw crisp border
            cv2.polylines(frame, [bin_pts], isClosed=True, color=bin_color, thickness=2, lineType=cv2.LINE_AA)

            # Bin ROI label
            min_y = np.min(bin_pts[:, 1])
            min_x = np.min(bin_pts[:, 0])
            label_text = f"BIN INTERIOR ROI | FILL: {fill_pct:.1f}%"
            cv2.putText(frame, label_text, (max(10, min_x), max(25, min_y - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, bin_color, 2, cv2.LINE_AA)

        # 2. Floor ROI
        if len(floor_pts) >= 3:
            floor_color = (0, 50, 255) if floor_litter else (255, 180, 0) # Red if litter detected, else Cyan/Orange
            cv2.polylines(frame, [floor_pts], isClosed=True, color=floor_color, thickness=2, lineType=cv2.LINE_AA)
            
            min_y = np.min(floor_pts[:, 1])
            min_x = np.min(floor_pts[:, 0])
            status_text = "FLOOR ZONE: LITTER DETECTED" if floor_litter else "FLOOR ZONE: CLEAR"
            cv2.putText(frame, status_text, (max(10, min_x), max(25, min_y - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, floor_color, 2, cv2.LINE_AA)

        return frame
