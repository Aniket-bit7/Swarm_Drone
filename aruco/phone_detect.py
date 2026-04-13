import cv2
import numpy as np
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aruco.utils import get_detector

# -------------------------------------------------------
# PUT YOUR PHONE IP HERE (shown on IP Webcam app screen)
# -------------------------------------------------------
PHONE_IP   = "10.181.123.13"
PHONE_PORT = "8080"
STREAM_URL = f"http://{PHONE_IP}:{PHONE_PORT}/video"
# -------------------------------------------------------

def draw_marker_info(frame: np.ndarray, corners, ids) -> np.ndarray:
    if ids is None:
        return frame

    for i, corner in enumerate(corners):
        pts = corner[0].astype(int)
        drone_id = int(ids[i][0])

        # bounding box
        cv2.polylines(frame, [pts], isClosed=True, color=(0, 200, 80), thickness=2)

        # corner dots
        colors = [(0,0,255), (0,255,255), (255,0,0), (255,0,255)]
        labels = ["TL", "TR", "BR", "BL"]
        for j, pt in enumerate(pts):
            cv2.circle(frame, tuple(pt), 5, colors[j], -1)
            cv2.putText(frame, labels[j], tuple(pt + [6, -6]),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.35, (200, 200, 200), 1)

        # drone ID at centre
        cx = int(pts[:, 0].mean())
        cy = int(pts[:, 1].mean())
        cv2.putText(frame, f"Drone {drone_id}", (cx - 30, cy),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 80), 2)

    return frame

def run():
    print(f"Connecting to phone stream: {STREAM_URL}")
    print("Make sure IP Webcam is running on your Nothing Phone.\n")

    detector = get_detector()
    cap = cv2.VideoCapture(STREAM_URL)

    if not cap.isOpened():
        print("ERROR: Could not connect to phone stream.")
        print("Check:")
        print("  1. IP Webcam app is running on your phone")
        print("  2. Phone and laptop are on the same Wi-Fi")
        print(f"  3. IP address is correct: {PHONE_IP}")
        return

    print("Connected! Press Q to quit.\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Stream lost. Check your phone.")
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        corners, ids, rejected = detector.detectMarkers(gray)

        frame = draw_marker_info(frame, corners, ids)

        # HUD overlay
        detected_ids = ids.flatten().tolist() if ids is not None else []
        hud_lines = [
            f"Stream: {PHONE_IP}:{PHONE_PORT}",
            f"Detected drones: {detected_ids}",
            f"Rejected candidates: {len(rejected)}",
        ]
        for idx, line in enumerate(hud_lines):
            cv2.putText(frame, line, (10, 28 + idx * 22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)

        cv2.imshow("Swarm — Phone Camera Detection", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    run()