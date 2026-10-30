import time
import math
import numpy as np
import cv2

class MockStreamGenerator:
    """
    Generates realistic synthetic video frames of a campus dustbin scene
    for demonstration and testing without requiring physical phone IP webcam.
    Clearly watermarks "DEMO MODE" on every frame.
    """

    def __init__(self, bin_id: str = "BIN-001", width: int = 640, height: int = 480):
        self.bin_id = bin_id
        self.width = width
        self.height = height
        self.start_time = time.time()
        self.fill_cycle_period = 90.0  # complete fill/empty cycle every 90 seconds
        self.manual_override_fill = None

    def set_override(self, fill_pct: float = None):
        self.manual_override_fill = fill_pct

    def get_frame(self) -> np.ndarray:
        elapsed = time.time() - self.start_time
        
        # Calculate dynamic target fill level based on sinusoidal cycle or override
        if self.manual_override_fill is not None:
            simulated_fill = max(0.0, min(100.0, self.manual_override_fill))
        else:
            # Smooth progression between 30% and 92%
            wave = (math.sin(elapsed * 2 * math.pi / self.fill_cycle_period) + 1.0) / 2.0
            simulated_fill = 35.0 + (wave * 58.0)

        # Base frame: realistic campus outdoor background (slate ground, brick wall)
        frame = np.full((self.height, self.width, 3), (35, 42, 48), dtype=np.uint8)

        # Campus wall background
        cv2.rectangle(frame, (0, 0), (self.width, int(self.height * 0.4)), (55, 62, 70), -1)
        # Floor line / curb
        cv2.rectangle(frame, (0, int(self.height * 0.4)), (self.width, self.height), (28, 32, 36), -1)
        cv2.line(frame, (0, int(self.height * 0.4)), (self.width, int(self.height * 0.4)), (80, 90, 100), 2)

        # Draw Dustbin geometry
        # Center coordinates
        bin_center_x = int(self.width * 0.5)
        bin_top_y = int(self.height * 0.28)
        bin_bottom_y = int(self.height * 0.82)
        bin_top_w = int(self.width * 0.36)
        bin_bot_w = int(self.width * 0.28)

        bin_pts = np.array([
            [bin_center_x - bin_top_w // 2, bin_top_y],
            [bin_center_x + bin_top_w // 2, bin_top_y],
            [bin_center_x + bin_bot_w // 2, bin_bottom_y],
            [bin_center_x - bin_bot_w // 2, bin_bottom_y]
        ], dtype=np.int32)

        # Dustbin body (metallic green/dark graphite)
        cv2.fillPoly(frame, [bin_pts], (40, 75, 45))
        cv2.polylines(frame, [bin_pts], isClosed=True, color=(70, 120, 80), thickness=3)

        # Dustbin rim
        cv2.ellipse(frame, (bin_center_x, bin_top_y), (bin_top_w // 2 + 5, 14), 0, 0, 360, (50, 95, 60), -1)
        cv2.ellipse(frame, (bin_center_x, bin_top_y), (bin_top_w // 2 + 5, 14), 0, 0, 360, (90, 160, 110), 2)

        # Draw waste accumulation inside the bin matching simulated_fill
        waste_fill_fraction = simulated_fill / 100.0
        bin_height = bin_bottom_y - bin_top_y
        current_waste_top = int(bin_bottom_y - (waste_fill_fraction * bin_height))

        # Waste items count proportional to fill
        num_items = int(2 + (simulated_fill / 8.0))
        np.random.seed(42)  # consistent placement
        
        # Color palette for synthetic waste items
        waste_colors = [
            (210, 180, 140),  # cardboard cup
            (50, 190, 230),   # plastic bottle cyan
            (200, 50, 80),    # soda can red
            (180, 220, 90),   # green bottle
            (240, 240, 240),  # paper / wrapper
            (80, 140, 220)    # blue carton
        ]

        for i in range(num_items):
            # Item vertical position stacked upwards
            item_y = int(bin_bottom_y - 20 - (i * (bin_height / max(1, num_items + 2))))
            item_type = i % 3
            # Keep the drawn pile at the simulated level (bottles are taller than cups/bags)
            item_top = item_y - (36 if item_type == 0 else 18)
            if item_top < current_waste_top - 6:
                continue

            # item horizontal wobble within bin width
            x_wobble = int((np.sin(i * 1.7) * 0.35) * (bin_top_w // 2))
            item_x = bin_center_x + x_wobble
            col = waste_colors[i % len(waste_colors)]

            if item_type == 0:  # bottle
                cv2.rectangle(frame, (item_x - 14, item_y - 28), (item_x + 14, item_y + 10), col, -1)
                cv2.rectangle(frame, (item_x - 6, item_y - 36), (item_x + 6, item_y - 28), (255, 255, 255), -1)
            elif item_type == 1:  # cup / bowl
                pts_cup = np.array([
                    [item_x - 18, item_y - 18],
                    [item_x + 18, item_y - 18],
                    [item_x + 12, item_y + 12],
                    [item_x - 12, item_y + 12]
                ], dtype=np.int32)
                cv2.fillPoly(frame, [pts_cup], col)
            else:  # crumpled bag / container
                cv2.circle(frame, (item_x, item_y), 18, col, -1)

        # Floor litter if fill is critical (> 85%) or if scheduled
        if simulated_fill >= 84.0:
            # Overflown items on the floor left and right
            cv2.rectangle(frame, (bin_center_x - bin_bot_w - 45, bin_bottom_y - 10),
                          (bin_center_x - bin_bot_w - 15, bin_bottom_y + 15), (200, 50, 80), -1)
            cv2.circle(frame, (bin_center_x + bin_bot_w + 35, bin_bottom_y + 12), 14, (50, 190, 230), -1)

        # Clear DEMO MODE Watermark Header
        watermark_bg = np.zeros((40, self.width, 3), dtype=np.uint8)
        watermark_bg[:] = (20, 24, 30)
        frame[0:40, 0:self.width] = cv2.addWeighted(frame[0:40, 0:self.width], 0.3, watermark_bg, 0.7, 0)
        cv2.putText(frame, "SIMULATED CAMERA STREAM - [DEMO MODE]", (15, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 220, 255), 2, cv2.LINE_AA)
        cv2.putText(frame, f"TARGET FILL: {simulated_fill:.1f}%", (self.width - 200, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1, cv2.LINE_AA)

        return frame
