import cv2
import numpy as np
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aruco.utils import get_detector

# --- change this to your phone IP stream URL if using IP Webcam ---
# e.g. "http://192.168.1.5:8080/video"
CAMERA_SOURCE = 0

def draw_marker_info(frame: np.ndarray, corners, ids) -> np.ndarray:
    """Draw bounding boxes, IDs, and corner dots on detected markers."""
    if ids is None:
        return frame

    for i, corner in enumerate(corners):
        pts = corner[0].astype(int)  # shape (4, 2)
        drone_id = int(ids[i][0])

        # draw outline
        cv2.polylines(frame, [pts], isClosed=True, color=(0, 200, 80), thickness=2)

        # draw corner dots
        for j, pt in enumerate(pts):
            color = [(0,0,255),(0,255,255),(255,0,0),(255,0,255)][j]
            cv2.circle(frame, tuple(pt), 5, color, -1)

        # corner order label (tiny, for learning)
        labels = ["TL","TR","BR","BL"]
        for j, pt in enumerate(pts):
            cv2.putText(frame, labels[j], tuple(pt + [6, -6]),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.35, (200,200,200), 1)

        # drone ID label at centre
        cx = int(pts[:, 0].mean())
        cy = int(pts[:, 1].mean())
        cv2.putText(frame, f"Drone {drone_id}", (cx - 30, cy),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 80), 2)

    return frame

def run_detection():
    detector = get_detector()
    cap = cv2.VideoCapture(CAMERA_SOURCE)

    if not cap.isOpened():
        print(f"ERROR: Cannot open camera source: {CAMERA_SOURCE}")
        return

    print("Detection running — press Q to quit.\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Frame read failed. Check your camera source.")
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        corners, ids, rejected = detector.detectMarkers(gray)

        frame = draw_marker_info(frame, corners, ids)

        # HUD
        detected_ids = ids.flatten().tolist() if ids is not None else []
        hud = f"Detected: {detected_ids}  |  Rejected candidates: {len(rejected)}"
        cv2.putText(frame, hud, (10, 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)

        cv2.imshow("ArUco Drone Detection", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    run_detection()