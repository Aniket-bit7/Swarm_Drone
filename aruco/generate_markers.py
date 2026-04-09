import cv2
import numpy as np
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aruco.utils import get_aruco_dict, NUM_DRONES, MARKER_SIZE, MARKERS_DIR

def generate_marker(marker_id: int, size: int = MARKER_SIZE) -> np.ndarray:
    """Generate a single ArUco marker image with a white border."""
    aruco_dict = get_aruco_dict()

    # create marker (grayscale)
    marker_img = np.zeros((size, size), dtype=np.uint8)
    cv2.aruco.generateImageMarker(aruco_dict, marker_id, size, marker_img)

    # add white border (makes detection more reliable when printed)
    border = size // 10
    bordered = cv2.copyMakeBorder(
        marker_img,
        border, border, border, border,
        cv2.BORDER_CONSTANT,
        value=255
    )
    return bordered

def save_marker(marker_id: int) -> str:
    """Generate and save a marker PNG. Returns the saved file path."""
    img = generate_marker(marker_id)
    filename = f"marker_{marker_id}.png"
    filepath = os.path.join(MARKERS_DIR, filename)
    cv2.imwrite(filepath, img)
    return filepath

def generate_all():
    print(f"Generating {NUM_DRONES} markers → {MARKERS_DIR}\n")
    for i in range(NUM_DRONES):
        path = save_marker(i)
        print(f"  Drone {i}  →  {path}")
    print("\nDone. Print each marker and attach to your drone.")

def preview_all():
    """Show all markers in a single window for quick visual check."""
    markers = [generate_marker(i) for i in range(NUM_DRONES)]
    
    # tile them in a row
    row = np.hstack(markers)
    
    # add drone ID label below each
    label_h = 30
    canvas = np.ones((row.shape[0] + label_h, row.shape[1]), dtype=np.uint8) * 255
    canvas[:row.shape[0], :] = row

    tile_w = markers[0].shape[1]
    for i in range(NUM_DRONES):
        cx = i * tile_w + tile_w // 2
        cv2.putText(canvas, f"ID {i}", (cx - 18, row.shape[0] + 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, 0, 2)

    cv2.imshow("ArUco Markers Preview — press any key to close", canvas)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

if __name__ == "__main__":
    generate_all()
    preview_all()