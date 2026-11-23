"""
Interactive Range-of-Motion Calibration Wizard (with Visual HUD)
Guides the user through 6 mobility calibration steps directly on-screen:
1. Neutral baseline (Relaxed forward gaze)
2. Maximum comfortable Look Left
3. Maximum comfortable Look Right
4. Maximum comfortable Look Up
5. Maximum comfortable Look Down
6. Eye Aspect Ratio (Gentle closure)

Saves output to: config/user_profile.json
"""

import os
import sys
import tempfile
from pathlib import Path

# Ensure root workspace directory is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["MPLCONFIGDIR"] = tempfile.gettempdir()

import time
import cv2
import numpy as np
from pathlib import Path

from core.capture import SafeFrameCapture
from vision.face_mesh import OfflineFaceTracker
from calibration.calibrator import CalibrationProfile


def draw_hud(frame_bgr: np.ndarray, step_name: str, instruction: str, countdown_text: str, progress: float):
    """Renders a high-contrast accessible visual overlay on the calibration window."""
    h, w, _ = frame_bgr.shape

    # Top banner (translucent dark box)
    overlay = frame_bgr.copy()
    cv2.rectangle(overlay, (0, 0), (w, 110), (20, 20, 20), -1)
    cv2.addWeighted(overlay, 0.75, frame_bgr, 0.25, 0, frame_bgr)

    # Step title
    cv2.putText(frame_bgr, f"STEP: {step_name}", (25, 35),
                cv2.FONT_HERSHEY_DUPLEX, 0.8, (0, 255, 255), 2, cv2.LINE_AA)

    # Main instruction
    cv2.putText(frame_bgr, instruction, (25, 70),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2, cv2.LINE_AA)

    # Countdown / Status
    cv2.putText(frame_bgr, countdown_text, (25, 98),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (50, 255, 50), 2, cv2.LINE_AA)

    # Bottom progress bar
    bar_y = h - 25
    bar_w = int((w - 50) * max(0.0, min(1.0, progress)))
    cv2.rectangle(frame_bgr, (25, bar_y), (w - 25, bar_y + 12), (50, 50, 50), -1)
    if bar_w > 0:
        cv2.rectangle(frame_bgr, (25, bar_y), (25 + bar_w, bar_y + 12), (0, 200, 0), -1)


def run_calibration(output_path: str = "config/user_profile.json", device_index: int = 0):
    print("=" * 60)
    print("Range-of-Motion Calibration Wizard")
    print("Camera window will open with on-screen visual guidance.")
    print("=" * 60)

    capture = SafeFrameCapture(device_index=device_index)
    if not capture.start():
        print(f"[Error] Could not open camera at index {device_index}.")
        sys.exit(1)

    tracker = OfflineFaceTracker()
    window_name = "Calibration Wizard - Hands-Free Accessibility"
    cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)

    steps = [
        ("Neutral Baseline", "Look straight ahead in a relaxed, neutral posture.", "neutral"),
        ("Look Left", "Turn head / look to the LEFT as far as comfortable.", "left"),
        ("Look Right", "Turn head / look to the RIGHT as far as comfortable.", "right"),
        ("Look Up", "Tilt head / look UP as far as comfortable.", "up"),
        ("Look Down", "Tilt head / look DOWN as far as comfortable.", "down"),
        ("Eyes Closed", "Gently CLOSE your eyes to calibrate blink detection.", "closed")
    ]

    results_data = {}

    try:
        for idx, (title, instruction, key) in enumerate(steps):
            # Phase 1: 2-second preparation
            prep_start = time.monotonic()
            while time.monotonic() - prep_start < 2.0:
                ret, frame_rgb = capture.read_frame()
                if not ret or frame_rgb is None:
                    continue
                frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
                remaining = 2.0 - (time.monotonic() - prep_start)
                draw_hud(frame_bgr, f"{idx+1}/6: {title}", instruction,
                         f"Get ready... Starting in {remaining:.1f}s", 0.0)
                cv2.imshow(window_name, frame_bgr)
                if cv2.waitKey(1) & 0xFF == 27:  # Esc
                    print("[Status] Calibration cancelled by user.")
                    return

            # Phase 2: 3-second sample recording
            samples = []
            rec_start = time.monotonic()
            rec_duration = 3.0
            while time.monotonic() - rec_start < rec_duration:
                ret, frame_rgb = capture.read_frame()
                if not ret or frame_rgb is None:
                    continue

                res = tracker.process_frame(frame_rgb)
                if res is not None:
                    samples.append(res)

                frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
                elapsed = time.monotonic() - rec_start
                progress = elapsed / rec_duration
                draw_hud(frame_bgr, f"{idx+1}/6: {title}", instruction,
                         f"RECORDING... ({elapsed:.1f}s / {rec_duration:.0f}s)", progress)
                cv2.imshow(window_name, frame_bgr)
                if cv2.waitKey(1) & 0xFF == 27:
                    print("[Status] Calibration cancelled by user.")
                    return

            results_data[key] = samples
            print(f"[Step {idx+1}/6 Completed] {title}: recorded {len(samples)} frames.")

        # Compute calibrated boundaries
        neutral_samples = results_data.get("neutral", [])
        if not neutral_samples:
            print("[Error] No face detected during neutral baseline. Please check lighting/camera.")
            return

        neutral_pitch = float(np.median([s.pitch for s in neutral_samples]))
        neutral_yaw = float(np.median([s.yaw for s in neutral_samples]))
        ear_open = float(np.median([(s.ear_left + s.ear_right) / 2.0 for s in neutral_samples]))

        # Left / Right
        samples_l = results_data.get("left", [])
        yaw_left_diff = max(4.0, abs(neutral_yaw - float(np.min([s.yaw for s in samples_l])))) if samples_l else 15.0

        samples_r = results_data.get("right", [])
        yaw_right_diff = max(4.0, abs(float(np.max([s.yaw for s in samples_r])) - neutral_yaw)) if samples_r else 15.0

        # Up / Down
        samples_u = results_data.get("up", [])
        pitch_up_diff = max(4.0, abs(neutral_pitch - float(np.min([s.pitch for s in samples_u])))) if samples_u else 12.0

        samples_d = results_data.get("down", [])
        pitch_down_diff = max(4.0, abs(float(np.max([s.pitch for s in samples_d])) - neutral_pitch)) if samples_d else 12.0

        # Closed eyes
        samples_c = results_data.get("closed", [])
        ear_closed = float(np.median([(s.ear_left + s.ear_right) / 2.0 for s in samples_c])) if samples_c else 0.14

        # Dynamically ensure closed eye baseline is distinctly below open baseline
        if ear_closed >= ear_open * 0.85:
            ear_closed = ear_open * 0.55

        blink_thresh = float((ear_open + ear_closed) / 2.0)

        profile = CalibrationProfile(
            neutral_pitch=neutral_pitch,
            neutral_yaw=neutral_yaw,
            max_yaw_left=yaw_left_diff,
            max_yaw_right=yaw_right_diff,
            max_pitch_up=pitch_up_diff,
            max_pitch_down=pitch_down_diff,
            ear_open_baseline=ear_open,
            ear_closed_baseline=ear_closed,
            blink_threshold=blink_thresh,
            calibrated=True
        )

        profile.save(output_path)
        print("\n" + "=" * 60)
        print(f"[SUCCESS] Calibration profile saved to {output_path}")
        print(f"Neutral Yaw: {neutral_yaw:.1f}°, Pitch: {neutral_pitch:.1f}°")
        print(f"Horizontal Movement Range: Left={yaw_left_diff:.1f}°, Right={yaw_right_diff:.1f}°")
        print(f"Vertical Movement Range: Up={pitch_up_diff:.1f}°, Down={pitch_down_diff:.1f}°")
        print("=" * 60)

    finally:
        capture.stop()
        tracker.close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    run_calibration()
