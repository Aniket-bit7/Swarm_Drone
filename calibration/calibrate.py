import cv2
import numpy as np
import os
import glob

IMAGES_DIR   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")
OUTPUT_FILE  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "camera_params.npz")

CHESSBOARD   = (9, 6)   # inner corners — must match your printed board
SQUARE_SIZE  = 1.0      # treat each square as 1 unit (relative scale is fine for ArUco)

def calibrate():
    # 3D points of checkerboard corners in real world (z=0 flat plane)
    objp = np.zeros((CHESSBOARD[0] * CHESSBOARD[1], 3), np.float32)
    objp[:, :2] = np.mgrid[0:CHESSBOARD[0], 0:CHESSBOARD[1]].T.reshape(-1, 2)
    objp *= SQUARE_SIZE

    obj_points = []   # 3D points from all images
    img_points = []   # 2D points from all images

    images = sorted(glob.glob(os.path.join(IMAGES_DIR, "*.jpg")))

    if not images:
        print(f"ERROR: No images found in {IMAGES_DIR}")
        print("Run capture_images.py first.")
        return

    print(f"Found {len(images)} images. Processing...\n")

    good = 0
    for fname in images:
        img  = cv2.imread(fname)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        ret, corners = cv2.findChessboardCorners(gray, CHESSBOARD, None)

        if ret:
            # refine corner positions to subpixel accuracy
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
            corners  = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)

            obj_points.append(objp)
            img_points.append(corners)
            good += 1

            # draw detected corners for visual feedback
            cv2.drawChessboardCorners(img, CHESSBOARD, corners, ret)
            cv2.imshow("Corners found", img)
            cv2.waitKey(200)
            print(f"  OK  {os.path.basename(fname)}")
        else:
            print(f"  SKIP (no corners found)  {os.path.basename(fname)}")

    cv2.destroyAllWindows()
    print(f"\n{good}/{len(images)} images used for calibration.")

    if good < 10:
        print("WARNING: Need at least 10 good images. Take more photos and retry.")
        return

    # run calibration
    ret, camera_matrix, dist_coeffs, rvecs, tvecs = cv2.calibrateCamera(
        obj_points, img_points, gray.shape[::-1], None, None
    )

    # reprojection error — lower is better, under 1.0 is good
    mean_error = 0
    for i in range(len(obj_points)):
        projected, _ = cv2.projectPoints(obj_points[i], rvecs[i], tvecs[i],
                                          camera_matrix, dist_coeffs)
        mean_error += cv2.norm(img_points[i], projected, cv2.NORM_L2) / len(projected)
    mean_error /= len(obj_points)

    print(f"\nReprojection error: {mean_error:.4f}  (good if < 1.0)")
    print(f"\nCamera matrix:\n{camera_matrix}")
    print(f"\nDistortion coefficients:\n{dist_coeffs}")

    # save
    np.savez(OUTPUT_FILE,
             camera_matrix=camera_matrix,
             dist_coeffs=dist_coeffs)
    print(f"\nSaved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    calibrate()