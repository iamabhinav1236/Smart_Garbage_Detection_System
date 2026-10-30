"""
Standalone Interactive ROI Calibration Tool
Smart Garbage Detection System

Allows sanitation administrator to click and mark:
1) Bin Interior ROI (4 corners or polygon)
2) Floor ROI (surrounding area for litter detection)
"""

import sys
import json
import cv2
import numpy as np

def calibrate(camera_url="demo"):
    print("\n" + "="*60)
    print("SMART GARBAGE DETECTION SYSTEM - ROI CALIBRATION TOOL")
    print("="*60)
    print("Instructions:")
    print("1. Click points to outline the BIN INTERIOR ROI (Left Click).")
    print("2. Press 'f' to switch to marking the FLOOR ROI.")
    print("3. Press 'r' to reset current points.")
    print("4. Press 's' to SAVE and print JSON coordinates.")
    print("5. Press 'q' or ESC to exit.")
    print("="*60 + "\n")

    current_mode = "BIN"
    bin_points = []
    floor_points = []

    if camera_url.lower() == "demo" or not camera_url:
        # Load sample synthetic frame
        frame = np.full((480, 640, 3), (35, 42, 48), dtype=np.uint8)
        cv2.rectangle(frame, (200, 150), (440, 420), (50, 100, 60), -1)
        cv2.putText(frame, "SAMPLE DUSTBIN (CLICK TO CALIBRATE)", (120, 120),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2)
    else:
        cap = cv2.VideoCapture(camera_url)
        ret, frame = cap.read()
        cap.release()
        if not ret or frame is None:
            print(f"Error: Unable to connect to camera {camera_url}")
            return

    frame = cv2.resize(frame, (640, 480))
    clone = frame.copy()

    def mouse_callback(event, x, y, flags, param):
        nonlocal current_mode, bin_points, floor_points
        if event == cv2.EVENT_LBUTTONDOWN:
            if current_mode == "BIN":
                bin_points.append([x, y])
                print(f"[BIN ROI] Added point ({x}, {y})")
            else:
                floor_points.append([x, y])
                print(f"[FLOOR ROI] Added point ({x}, {y})")

    cv2.namedWindow("ROI Calibration - Smart Garbage System")
    cv2.setMouseCallback("ROI Calibration - Smart Garbage System", mouse_callback)

    while True:
        display = clone.copy()

        # Draw Bin ROI in Cyan
        if len(bin_points) > 1:
            cv2.polylines(display, [np.array(bin_points, dtype=np.int32)], isClosed=(len(bin_points) > 2), color=(255, 255, 0), thickness=2)
        for pt in bin_points:
            cv2.circle(display, tuple(pt), 4, (0, 255, 255), -1)

        # Draw Floor ROI in Amber
        if len(floor_points) > 1:
            cv2.polylines(display, [np.array(floor_points, dtype=np.int32)], isClosed=(len(floor_points) > 2), color=(0, 165, 255), thickness=2)
        for pt in floor_points:
            cv2.circle(display, tuple(pt), 4, (0, 165, 255), -1)

        # Status text
        status_text = f"MODE: {current_mode} ROI (Left Click to mark, 'f' to toggle, 's' to save, 'r' reset)"
        cv2.putText(display, status_text, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)

        cv2.imshow("ROI Calibration - Smart Garbage System", display)
        key = cv2.waitKey(20) & 0xFF

        if key == ord('q') or key == 27:
            break
        elif key == ord('f'):
            current_mode = "FLOOR" if current_mode == "BIN" else "BIN"
            print(f"Switched mode to: {current_mode} ROI")
        elif key == ord('r'):
            if current_mode == "BIN":
                bin_points = []
            else:
                floor_points = []
            print(f"Reset {current_mode} points")
        elif key == ord('s'):
            print("\n" + "="*50)
            print("CALIBRATION RESULTS:")
            print("BIN_ROI JSON:", json.dumps(bin_points))
            print("FLOOR_ROI JSON:", json.dumps(floor_points))
            print("="*50 + "\n")
            print("You can paste these coordinates directly into the web dashboard or database.")
            break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "demo"
    calibrate(url)
