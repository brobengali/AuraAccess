# AuraAccess — Zero-Cloud Hands-Free Accessibility System

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform: Windows 10/11](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D6.svg)](https://microsoft.com/windows)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](https://python.org)
[![Air-Gapped: 100% Local](https://img.shields.io/badge/Architecture-100%25%20On--Device%20%7C%20Zero%20Cloud-success.svg)](#-100-privacy--zero-cloud-guarantee)

**AuraAccess** is a local-first, air-gapped hands-free accessibility control system engineered for individuals with quadriplegia, ALS, motor neuron diseases, and severe physical paralysis. It enables complete, fluid computer control through subtle head movements, eye winks, and facial gestures with zero cloud dependencies and zero data retention.

---

## 🔒 100% Privacy & Zero-Cloud Guarantee
- **Local-First & Air-Gapped:** Operates strictly on `127.0.0.1` (localhost). Never connects to external cloud servers or telemetry endpoints.
- **RAM-Only Frame Processing:** Camera frames are captured into volatile RAM buffers, processed via local CPU XNNPACK inference, and immediately overwritten. No video, images, or raw biometric data are ever written to disk.
- **Auditable & Open-Source:** Built with standard Python, OpenCV, and MediaPipe Tasks API running entirely on local CPU.

---

## 🌟 Key Features & Innovations

### 1. Shift Key Single-Tap Safety Clutch (No Holding Required)
- **Tap once for Access:** Tap the <kbd>Shift</kbd> key once to grant cursor control. A high chime (1175 Hz) confirms activation.
- **Tap again to Decline Access:** Tap <kbd>Shift</kbd> again to freeze the cursor and release all control. A low chime (587 Hz) confirms safety lock.
- **Zero Hijacking:** Caregivers and family members can use the physical mouse and keyboard freely at any time without cursor fighting.

### 2. Swift Cursor Navigation (Native Optical Mouse Feel)
- **Direct Nose-Tip Steering:** Intuitive tracking mapped from facial landmark geometry.
- **Non-Linear Pointer Acceleration:** Subtle movements (<3px) provide single-pixel precision for clicking links and checkboxes; swift head turns effortlessly fling the cursor across dual displays.
- **Adaptive Tremor & Spasm Shield:** Dual-stage 2D Kalman filter eliminates Parkinsonian tremors and accidental spasms while keeping intentional steering latency near zero.

### 3. Dwell Click Accumulator (Hover to Click)
- **48px Stability Zone:** Cursor stays locked within target zone even during natural breathing or micro-drifts.
- **Visual 360° Ring on Face:** Real-time yellow/green progress ring winds around the nose tip on the camera feed.
- **Audio Click Feedback:** Crisp chime confirms click execution, followed by a 0.8s cooldown to prevent repeated accidental clicking.

### 4. Context-Aware Action Studio
Automatically detects the foreground active window and dynamically adapts facial gesture responses:
| Gesture | General Desktop | YouTube & Media | Reading & Documents |
| :--- | :--- | :--- | :--- |
| **Dwell (0.9s)** | Left Click | Left Click | Left Click |
| **Left Eye Wink** | Left Click | Play / Pause (<kbd>Space</kbd>) | Page Down |
| **Right Eye Wink** | App Switcher (<kbd>Alt+Tab</kbd>) | Mute / Unmute | Page Up |
| **Mouth Open / Smile** | Scroll Down | Scroll Comments Down | Scroll Down |

### 5. Multi-User Range-of-Motion Normalization
- No hardcoded mobility thresholds.
- Step-by-step 5-point calibration wizard maps whatever range of motion the user possesses (even a 2° to 4° neck tilt) to the full 100% width and height of the display.
- Multiple user profiles (`profiles/{profile_id}.json`) can be switched with one click.

### 6. Emergency Caregiver SOS Alarm
- Sustained eye closure for 3.5 seconds or 5 rapid distress blinks immediately triggers an audible 900 Hz local emergency chime through PC speakers to summon caregivers.

### 7. Integrated "How to Use" Reference Manual
- Complete operational documentation is built directly into the web dashboard (`http://127.0.0.1:8000`), with quick-jump navigation pills, FAQ, and troubleshooting guide.

---

## 🚀 Quick Start Guide

### Prerequisites
- Windows 10 or 11
- Python 3.10 or higher
- Standard USB Webcam or built-in laptop camera

### Installation
```bash
# Clone the repository
git clone https://github.com/brobengali/AuraAccess.git
cd AuraAccess

# Install dependencies
pip install -r requirements.txt
```

### Launch the Application
```bash
python run_app.py
```
This automatically starts the local engine and launches the dashboard at:
👉 **`http://127.0.0.1:8000`**

### Alternative 1-Click Batch Launcher:
Double-click `START_AURA_ACCESS.bat` in the project root directory.

---

## 🧪 Running Automated Unit Tests
```bash
python -m unittest tests/test_components.py
```
All unit tests verify:
- Dwell click accumulation and cooldown
- Kalman tremor suppression and spasm dampening
- EAR (Eye Aspect Ratio) and MAR (Mouth Aspect Ratio) gesture math
- Pydantic schema validation and bounds checking
- Range-of-motion coordinate normalizer

---

## 📁 Repository Architecture
```text
AuraAccess/
├── calibration/        # 5-point mobility calibration wizard
├── config/             # Pydantic schema & default_config.yaml
├── core/               # DirectShow frame capture & gesture state machine
├── dispatcher/         # Native Win32 SetCursorPos & mouse injection
├── filters/            # Adaptive Kalman tremor & spasm suppression
├── models/             # Offline MediaPipe FaceLandmarker task model
├── profiles/           # Multi-user personalized calibration JSON stores
├── server/             # FastAPI, WebSocket telemetry & app detector
├── tests/              # Component & integration test suite
├── ui/                 # Floating always-on-top assistive desktop dock
├── vision/             # Landmark geometric aspect ratio and pose math
├── web/                # High-contrast accessible web dashboard
├── requirements.txt    # Project dependencies
├── run_app.py          # Unified application entrypoint
└── START_AURA_ACCESS.bat # 1-click Windows desktop batch launcher
```

---

## 📄 License
This project is open-source under the [MIT License](LICENSE).
