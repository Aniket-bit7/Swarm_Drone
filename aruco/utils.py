import cv2
import os

# --- config ---
ARUCO_DICT   = cv2.aruco.DICT_4X4_50   # supports up to 50 unique markers
NUM_DRONES   = 5                         # how many drones in your swarm
MARKER_SIZE  = 200                       # pixel size of generated PNG

# --- paths ---
ROOT_DIR     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MARKERS_DIR  = os.path.join(ROOT_DIR, "markers", "generated")

os.makedirs(MARKERS_DIR, exist_ok=True)

def get_aruco_dict():
    return cv2.aruco.getPredefinedDictionary(ARUCO_DICT)

def get_detector():
    params = cv2.aruco.DetectorParameters()
    return cv2.aruco.ArucoDetector(get_aruco_dict(), params)