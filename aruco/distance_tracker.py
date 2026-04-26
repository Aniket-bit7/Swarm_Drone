import cv2
import numpy as np
import os
import sys
from itertools import combinations

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aruco.utils import get_detector

# --- config ---
PHONE_IP    = "100.103.15.180"
PHONE_PORT  = "8080"
STREAM_URL  = f"http://{PHONE_IP}:{PHONE_PORT}/video"

MARKER_SIZE = 0.047  # metres — same as your pose_estimation.py

CALIB_FILE  = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "calibration", "camera_params.npz"
)

# minimum distance alert threshold in metres
# if two drones get closer than this, show a warning
COLLISION_THRESHOLD = 0.30  # 30cm

def load_calibration():
    if not os.path.exists(CALIB_FILE):
        print(f"ERROR: Calibration file not found: {CALIB_FILE}")
        sys.exit(1)
    data = np.load(CALIB_FILE)
    return data["camera_matrix"], data["dist_coeffs"]

def get_3d_position(tvec):
    """Extract X, Y, Z from tvec as a clean numpy array."""
    return tvec[0].flatten()  # shape (3,)

def distance_3d(pos_a, pos_b):
    """Euclidean distance between two 3D positions in metres."""
    return float(np.linalg.norm(pos_a - pos_b))

def draw_distance_line(frame, pt_a, pt_b, dist, too_close):
    """Draw a line between two marker centres with distance label."""
    color  = (0, 0, 255) if too_close else (0, 220, 255)
    thickness = 3 if too_close else 1

    cv2.line(frame, pt_a, pt_b, color, thickness)

    # label at midpoint
    mid_x = (pt_a[0] + pt_b[0]) // 2
    mid_y = (pt_a[1] + pt_b[1]) // 2

    label = f"{dist*100:.1f} cm"
    if too_close:
        label += "  !! TOO CLOSE"

    (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
    cv2.rectangle(frame,
                  (mid_x - 4, mid_y - th - 4),
                  (mid_x + tw + 4, mid_y + 6),
                  (0, 0, 0), -1)
    cv2.putText(frame, label, (mid_x, mid_y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)

def draw_drone_info(frame, drone_id, pos, centre_px):
    """Draw drone ID and XYZ position near its marker."""
    x, y, z = pos
    lines = [
        f"Drone {drone_id}",
        f"X:{x:+.3f} Y:{y:+.3f} Z:{z:.3f} m",
    ]
    lx, ly = centre_px[0] + 12, centre_px[1] - 10
    for j, line in enumerate(lines):
        cy = ly + j * 20
        (tw, th), _ = cv2.getTextSize(line, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.rectangle(frame, (lx - 2, cy - th - 2),
                      (lx + tw + 2, cy + 4), (0, 0, 0), -1)
        color = (0, 255, 100) if j == 0 else (200, 200, 200)
        cv2.putText(frame, line, (lx, cy),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

def run():
    camera_matrix, dist_coeffs = load_calibration()
    detector = get_detector()

    cap = cv2.VideoCapture(STREAM_URL)
    if not cap.isOpened():
        print("ERROR: Cannot connect to phone stream.")
        return

    print(f"Stream connected: {STREAM_URL}")
    print(f"Collision threshold: {COLLISION_THRESHOLD*100:.0f} cm")
    print("Press Q to quit\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Stream lost.")
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        corners, ids, _ = detector.detectMarkers(gray)

        # dict: drone_id → { pos_3d, centre_px }
        drones = {}

        if ids is not None:
            rvecs, tvecs, _ = cv2.aruco.estimatePoseSingleMarkers(
                corners, MARKER_SIZE, camera_matrix, dist_coeffs
            )

            for i in range(len(ids)):
                drone_id = int(ids[i][0])
                pos      = get_3d_position(tvecs[i])
                pts      = corners[i][0].astype(int)
                centre   = (int(pts[:, 0].mean()), int(pts[:, 1].mean()))

                drones[drone_id] = {"pos": pos, "centre": centre}

                # draw axes
                cv2.drawFrameAxes(frame, camera_matrix, dist_coeffs,
                                  rvecs[i], tvecs[i], MARKER_SIZE * 0.8)

                # draw bounding box
                cv2.polylines(frame, [pts], isClosed=True,
                              color=(0, 200, 80), thickness=2)

                # draw drone info
                draw_drone_info(frame, drone_id, pos, centre)

            # --- compute pairwise distances ---
            drone_ids = list(drones.keys())

            for id_a, id_b in combinations(drone_ids, 2):
                pos_a    = drones[id_a]["pos"]
                pos_b    = drones[id_b]["pos"]
                dist     = distance_3d(pos_a, pos_b)
                too_close = dist < COLLISION_THRESHOLD

                draw_distance_line(
                    frame,
                    drones[id_a]["centre"],
                    drones[id_b]["centre"],
                    dist,
                    too_close
                )

                # terminal output
                status = "!! TOO CLOSE !!" if too_close else "OK"
                print(f"  Drone {id_a} <-> Drone {id_b} : "
                      f"{dist*100:.1f} cm  [{status}]", end="   ")

            if drone_ids:
                print()

        # HUD
        n = len(drones)
        pairs = len(list(combinations(drones.keys(), 2)))
        hud = f"Drones visible: {n}  |  Pairs tracked: {pairs}  |  Threshold: {COLLISION_THRESHOLD*100:.0f}cm"
        cv2.putText(frame, hud, (10, 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)

        cv2.imshow("Swarm — Distance Tracker", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    run()