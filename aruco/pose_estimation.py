import cv2
import numpy as np
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aruco.utils import get_detector

# --- config ---
PHONE_IP    = "10.110.189.147"
PHONE_PORT  = "8080"
STREAM_URL  = f"http://{PHONE_IP}:{PHONE_PORT}/video"

MARKER_SIZE = 0.047  # real physical size of your printed marker in METRES
               # measure your actual printed marker and update this
               # e.g. if marker is 5cm → 0.05, if 8cm → 0.08

CALIB_FILE  = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "calibration", "camera_params.npz"
)

def load_calibration():
    if not os.path.exists(CALIB_FILE):
        print(f"ERROR: Calibration file not found: {CALIB_FILE}")
        print("Run calibration/calibrate.py first.")
        sys.exit(1)

    data = np.load(CALIB_FILE)
    camera_matrix = data["camera_matrix"]
    dist_coeffs   = data["dist_coeffs"]
    print("Calibration loaded OK")
    return camera_matrix, dist_coeffs

def get_euler_angles(rvec):
    """Convert rotation vector to roll, pitch, yaw in degrees."""
    R, _ = cv2.Rodrigues(rvec)
    sy   = np.sqrt(R[0,0]**2 + R[1,0]**2)
    if sy > 1e-6:
        roll  = np.degrees(np.arctan2( R[2,1], R[2,2]))
        pitch = np.degrees(np.arctan2(-R[2,0], sy))
        yaw   = np.degrees(np.arctan2( R[1,0], R[0,0]))
    else:
        roll  = np.degrees(np.arctan2(-R[1,2], R[1,1]))
        pitch = np.degrees(np.arctan2(-R[2,0], sy))
        yaw   = 0.0
    return roll, pitch, yaw

def draw_pose(frame, corners, ids, rvecs, tvecs):
    """Draw axes and pose info on each detected drone."""
    if ids is None:
        return frame

    for i in range(len(ids)):
        drone_id = int(ids[i][0])
        rvec     = rvecs[i]
        tvec     = tvecs[i]

        # X=red  Y=green  Z=blue axes drawn on marker
        cv2.drawFrameAxes(frame, camera_matrix, dist_coeffs,
                          rvec, tvec, MARKER_SIZE * 0.8)

        # bounding box
        pts = corners[i][0].astype(int)
        cv2.polylines(frame, [pts], isClosed=True, color=(0, 200, 80), thickness=2)

        # position in metres
        x, y, z      = tvec[0][0], tvec[0][1], tvec[0][2]
        roll, pitch, yaw = get_euler_angles(rvec)

        # label position — top left corner of marker
        lx, ly = pts[0][0], pts[0][1] - 10

        lines = [
            f"Drone {drone_id}",
            f"X:{x:+.3f}  Y:{y:+.3f}  Z:{z:.3f} m",
            f"R:{roll:+.1f}  P:{pitch:+.1f}  Yaw:{yaw:+.1f} deg",
        ]

        for j, line in enumerate(lines):
            cy = ly + j * 20
            # dark background for readability
            (tw, th), _ = cv2.getTextSize(line, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(frame, (lx - 2, cy - th - 2),
                          (lx + tw + 2, cy + 4), (0, 0, 0), -1)
            color = (0, 255, 100) if j == 0 else (255, 255, 255)
            cv2.putText(frame, line, (lx, cy),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

    return frame

def run():
    global camera_matrix, dist_coeffs
    camera_matrix, dist_coeffs = load_calibration()
    detector = get_detector()

    cap = cv2.VideoCapture(STREAM_URL)
    if not cap.isOpened():
        print("ERROR: Cannot connect to phone stream.")
        return

    print(f"Stream connected: {STREAM_URL}")
    print(f"Marker physical size: {MARKER_SIZE*100:.1f} cm")
    print("Press Q to quit\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Stream lost.")
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        corners, ids, rejected = detector.detectMarkers(gray)

        if ids is not None:
            rvecs, tvecs, _ = cv2.aruco.estimatePoseSingleMarkers(
                corners, MARKER_SIZE, camera_matrix, dist_coeffs
            )
            frame = draw_pose(frame, corners, ids, rvecs, tvecs)

            # print positions to terminal
            for i in range(len(ids)):
                drone_id    = int(ids[i][0])
                x, y, z     = tvecs[i][0]
                roll, pitch, yaw = get_euler_angles(rvecs[i])
                print(f"Drone {drone_id} | "
                      f"pos=({x:+.3f}, {y:+.3f}, {z:.3f})m | "
                      f"yaw={yaw:+.1f}°", end="   ")
            print()

        else:
            cv2.putText(frame, "No markers detected", (10, 35),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

        cv2.imshow("Swarm — Pose Estimation", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    run()