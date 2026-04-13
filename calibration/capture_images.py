import cv2
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PHONE_IP   = "10.181.123.13"   # ← your hotspot IP
PHONE_PORT = "8080"
STREAM_URL = f"http://{PHONE_IP}:{PHONE_PORT}/video"

SAVE_DIR   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")
os.makedirs(SAVE_DIR, exist_ok=True)

def capture():
    cap = cv2.VideoCapture(STREAM_URL)

    if not cap.isOpened():
        print("ERROR: Cannot connect to phone stream. Is IP Webcam running?")
        return

    count = 0
    saved_flash = 0  # frames to show green flash after saving

    print("Stream connected!")
    print("  Press S to save a photo")
    print("  Press Q to quit")
    print("\nNOTE: Click on the camera window first, then press S\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Stream lost.")
            break

        display = frame.copy()

        # green flash when saved
        if saved_flash > 0:
            overlay = display.copy()
            cv2.rectangle(overlay, (0, 0), (display.shape[1], display.shape[0]),
                          (0, 255, 0), -1)
            cv2.addWeighted(overlay, 0.3, display, 0.7, 0, display)
            saved_flash -= 1

        # HUD
        cv2.putText(display, f"Saved: {count} images",
                    (10, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.putText(display, "S = save    Q = quit",
                    (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(display, ">> CLICK THIS WINDOW FIRST then press S <<",
                    (10, display.shape[0] - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 220, 255), 2)

        cv2.imshow("Calibration Capture", display)

        key = cv2.waitKey(1) & 0xFF

        if key == ord('s') or key == ord('S'):
            filename = os.path.join(SAVE_DIR, f"calib_{count:03d}.jpg")
            cv2.imwrite(filename, frame)  # save original frame, not display
            count += 1
            saved_flash = 8  # show green flash for 8 frames
            print(f" Saved [{count}]: {filename}")

        elif key == ord('q') or key == ord('Q'):
            break

    print(f"\nTotal images saved: {count}")
    print(f"Location: {SAVE_DIR}")
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    capture()