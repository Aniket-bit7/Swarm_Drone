# Swarm Drone — Software Setup Guide

> Covers everything from environment setup to real-time distance tracking between drones.
> ESP32 firmware and flight control are covered in a separate document.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Folder Structure](#folder-structure)
3. [Requirements](#requirements)
4. [Step 1 — Generate ArUco Markers](#step-1--generate-aruco-markers)
5. [Step 2 — Phone Camera Stream Setup](#step-2--phone-camera-stream-setup)
6. [Step 3 — Camera Calibration](#step-3--camera-calibration)
7. [Step 4 — Pose Estimation](#step-4--pose-estimation)
8. [Step 5 — Distance Tracker](#step-5--distance-tracker)
9. [Configuration Reference](#configuration-reference)
10. [Troubleshooting](#troubleshooting)

---

## Project Overview

This system uses a **Nothing Phone camera** as an overhead vision system to track a swarm of 4 ESP32-S3 drones in real time. Each drone has a unique **ArUco marker** attached to it. A Python script running on a laptop reads the phone's video stream, detects all markers, computes their 3D positions, measures distances between drones, and later sends control commands over UDP.

```
Nothing Phone (IP Webcam)
        │
        │  MJPEG video stream (Wi-Fi hotspot)
        ▼
   Laptop (Python)
   ├── ArUco detection
   ├── Pose estimation (solvePnP)
   ├── Distance tracking
   └── (next) UDP → ESP32 drones
```

---

## Folder Structure

```
swarm_drone/
├── markers/
│   └── generated/              # saved marker PNGs (auto-created)
├── calibration/
│   ├── images/                 # checkerboard photos for calibration
│   ├── capture_images.py       # captures photos from phone stream
│   ├── calibrate.py            # computes camera matrix from photos
│   └── camera_params.npz       # saved calibration output (auto-generated)
├── aruco/
│   ├── utils.py                # shared config and helpers
│   ├── generate_markers.py     # generates marker PNGs
│   ├── detect_markers.py       # basic live detection (webcam)
│   ├── phone_detect.py         # live detection from phone stream
│   ├── pose_estimation.py      # 3D position of each drone
│   └── distance_tracker.py     # real-time pairwise distances
└── requirements.txt
```

---

## Requirements

### Hardware
- Laptop (Windows / Linux / Mac)
- Nothing Phone (or any Android phone) running **IP Webcam** app
- 4 printed ArUco markers (one per drone)
- Phone and laptop connected to the **same network** (phone hotspot recommended)

### Software

Install dependencies:

```bash
pip install -r requirements.txt
```

**`requirements.txt`**
```
opencv-contrib-python==4.10.0.84
numpy
```

> ⚠️ Must use `opencv-contrib-python` — not `opencv-python`. The ArUco module lives in the contrib package.

---

## Step 1 — Generate ArUco Markers

Each drone gets a unique marker ID (0, 1, 2, 3).

### Config (`aruco/utils.py`)

```python
ARUCO_DICT  = cv2.aruco.DICT_4X4_50   # 4x4 grid, up to 50 unique markers
NUM_DRONES  = 4                         # one marker per drone
MARKER_SIZE = 200                       # PNG pixel size
```

### Run

```bash
python aruco/generate_markers.py
```

**Output:** `markers/generated/marker_0.png` through `marker_3.png`

A preview window shows all 4 markers side by side. Print each one and attach to its drone.

> 📏 After printing, measure the **black square only** (not the white border) with a ruler. You will need this measurement in metres later for accurate pose estimation.

---

## Step 2 — Phone Camera Stream Setup

### On your Nothing Phone

1. Install **IP Webcam** from the Play Store *(by Pavel Khlebovich)*
2. Recommended settings before starting:
   - Resolution: `1280 × 720`
   - Quality: `50–60%`
   - FPS limit: `30`
   - Focus mode: `Continuous`
3. Tap **Start server**
4. Note the IP address shown on screen (e.g. `192.168.43.57:8080`)

### Network setup

> ⚠️ Phone and laptop **must** be on the same subnet. The easiest way is to use your **phone's hotspot**.

**Recommended setup:**
1. Enable hotspot on your Nothing Phone
2. Connect your laptop to that hotspot
3. Open IP Webcam → Start server
4. The IP will now be in the `192.168.43.x` range

**Verify connection** — open this in your laptop browser:
```
http://192.168.43.x:8080
```
You should see the IP Webcam web interface with a live video feed.

### Update the IP in code

In `aruco/phone_detect.py` (and all subsequent scripts):
```python
PHONE_IP   = "192.168.43.x"   # replace with your actual IP
PHONE_PORT = "8080"
```

### Run basic phone detection

```bash
python aruco/phone_detect.py
```

You should see the phone camera feed on your laptop with green boxes drawn around any detected markers.

---

## Step 3 — Camera Calibration

Calibration tells OpenCV your phone camera's exact lens properties — focal length, optical center, and distortion. Without this, 3D position values will be inaccurate.

> You only need to do this **once** per phone. The result is saved and reused.

### What you need

A checkerboard pattern with **9×6 inner corners**. Options:
- Display it fullscreen on a second laptop/monitor
- Print it on A4 paper

### Step 3.1 — Capture calibration images

```bash
python calibration/capture_images.py
```

A window opens showing your phone camera feed.

- Point your phone at the checkerboard from different angles
- **Click on the camera window first** so it has keyboard focus
- Press **`S`** to save a photo — a green flash confirms each save
- Take **20–25 photos** varying angle, tilt, rotation, and distance
- Press **`Q`** to quit

**Good photo checklist:**

| Do | Don't |
|---|---|
| Cover all corners of the frame | Keep board only in the center |
| Tilt and rotate the board | Always hold it flat |
| Vary distance (close + far) | Stay the same distance |
| Good even lighting | Dark or shadowy shots |
| 20+ photos | Less than 10 |

Photos are saved to `calibration/images/`.

### Step 3.2 — Run calibration

```bash
python calibration/calibrate.py
```

**What it outputs:**
- Reprojection error — lower is better
  - `< 0.5` = excellent ✅
  - `0.5 – 1.0` = acceptable
  - `> 1.0` = retake photos
- `calibration/camera_params.npz` — saved camera matrix and distortion coefficients

> 💡 A reprojection error of **0.10** was achieved during development — this is excellent.

---

## Step 4 — Pose Estimation

Detects each drone's full **6-DOF pose** (X, Y, Z position + roll, pitch, yaw) in real 3D space from the phone camera.

### Before running — set your marker size

Measure your printed marker's **black square** with a ruler and update:

```python
# aruco/pose_estimation.py
MARKER_SIZE = 0.05   # your measured size in metres
                     # e.g. 5cm → 0.05, 7cm → 0.07
```

> ⚠️ Even 2mm of error here causes ~2cm of position error at 50cm distance.

### Run

```bash
python aruco/pose_estimation.py
```

### What you see on screen

| Element | Meaning |
|---|---|
| Red axis | X direction |
| Green axis | Y direction |
| Blue axis | Z direction (out of marker) |
| `X Y Z` numbers | Position in metres from camera |
| `R P Yaw` numbers | Orientation in degrees |

### Terminal output

```
Drone 0 | pos=(+0.012, -0.003, 0.487)m | yaw=+2.1°
Drone 1 | pos=(-0.391, +0.008, 0.502)m | yaw=-1.3°
```

---

## Step 5 — Distance Tracker

Tracks real-time **pairwise 3D distances** between all detected drones simultaneously. Uses high-precision pose estimation with subpixel refinement and weighted smoothing.

### Key improvements over basic detection

| Feature | Detail |
|---|---|
| `solvePnP` with `SOLVEPNP_IPPE_SQUARE` | More accurate than `estimatePoseSingleMarkers` |
| LM refinement (`solvePnPRefineLM`) | Sub-millimetre pose optimization |
| Subpixel corner refinement | Corners detected to 0.0001px accuracy |
| Weighted rolling average | Smooths noise across last 5 frames |
| Frame undistortion (`cv2.remap`) | Removes lens distortion before detection |
| Histogram equalization | Better detection in varied lighting |

### Config

```python
# aruco/distance_tracker.py
MARKER_SIZE          = 0.05   # metres — your measured marker
COLLISION_THRESHOLD  = 0.30   # metres — warn if drones closer than this
SMOOTH_FRAMES        = 5      # smoothing window (higher = smoother, more lag)
```

### Run

```bash
python aruco/distance_tracker.py
```

### What you see on screen

- **Yellow line** between every drone pair — shows distance in cm
- **Red line + warning** when two drones are closer than the threshold
- Position info box on each drone showing raw and smoothed coordinates

### Terminal output

```
Drone 0 <-> Drone 1 : 42.17 cm  [OK]
Drone 0 <-> Drone 2 : 28.93 cm  [!! TOO CLOSE !!]
```

### Adjust collision threshold

```python
COLLISION_THRESHOLD = 0.50   # 50cm — increase for more safety margin
```

---

## Configuration Reference

| File | Variable | Default | Description |
|---|---|---|---|
| `aruco/utils.py` | `NUM_DRONES` | `4` | Number of drones in swarm |
| `aruco/utils.py` | `ARUCO_DICT` | `DICT_4X4_50` | ArUco dictionary |
| `aruco/utils.py` | `MARKER_SIZE` | `200` | PNG pixel size for generation |
| `aruco/pose_estimation.py` | `MARKER_SIZE` | `0.05` | Physical marker size in metres |
| `aruco/pose_estimation.py` | `PHONE_IP` | — | Your phone's hotspot IP |
| `aruco/distance_tracker.py` | `COLLISION_THRESHOLD` | `0.30` | Alert distance in metres |
| `aruco/distance_tracker.py` | `SMOOTH_FRAMES` | `5` | Position smoothing window |

---

## Troubleshooting

### Cannot connect to phone stream

- Make sure IP Webcam is running and shows "server started"
- Laptop must be connected to **phone hotspot** (not same router — they may be isolated)
- Try opening `http://<phone-ip>:8080` in your laptop browser first
- Turn off mobile data on your phone — it can cause IP conflicts

### `S` key not saving images during calibration

- **Click on the camera preview window** with your mouse first
- The OpenCV window must have focus — not the terminal

### Reprojection error too high (> 1.0)

- Retake photos — more angles, better lighting
- Make sure the full checkerboard is visible in every shot
- Avoid motion blur — hold the board still when pressing S

### Markers not detected

- Ensure you installed `opencv-contrib-python` not `opencv-python`
- Check lighting — avoid strong shadows across the marker
- Marker must face the camera — not at extreme angles (> 60°)

### Distance readings inaccurate

- Measure `MARKER_SIZE` precisely — black square only, not the white border
- Recalibrate camera if reprojection error was above 0.5
- Increase `SMOOTH_FRAMES` for less jitter (at the cost of slight lag)

---

*Next steps (covered separately): UDP communication → PID control → ESP32 firmware → swarm formation*
