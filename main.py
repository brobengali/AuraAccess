"""
Hands-Free Accessibility Controller - Main Execution Pipeline
Orchestrates:
1. In-memory camera frame capture (Zero Cloud)
2. Offline MediaPipe FaceMesh & 3D Head Pose tracking
3. Kalman tremor & involuntary spasm filtering
4. Range-of-motion profile normalization
5. Dwell-time accumulator & Blink intent validator
6. Emergency SOS detection & Caregiver alert
7. Translucent floating Radial HUD
"""

import os
import tempfile
os.environ["MPLCONFIGDIR"] = tempfile.gettempdir()

import sys
import time
import argparse
from pathlib import Path
import numpy as np

from config.schema import AppConfig
from core.capture import SafeFrameCapture
from vision.face_mesh import OfflineFaceTracker
from filters.tremor_filter import KalmanTremorFilter
from calibration.calibrator import CalibrationProfile
from dispatcher.action_controller import ActionDispatcher
from core.state_machine import GestureStateMachine, SystemState


def run_system(config_path: str = "config/default_config.yaml", profile_path: str = "config/user_profile.json"):
    # 1. Load validated configuration
    cfg = AppConfig.load_from_yaml(config_path)
    print("=" * 60)
    print("Hands-Free Accessibility System")
    print("Mode: 100% Offline, Local-First, Zero Cloud Data")
    print("Emergency Failsafe: Move mouse cursor to any corner or press Ctrl+C")
    print("=" * 60)

    # 2. Load user calibration profile
    profile = CalibrationProfile.load(profile_path)
    if profile.calibrated:
        print("[Status] Loaded personalized range-of-motion profile.")
        # Dynamically apply user's calibrated eye thresholds
        cfg.tracking.eye_aspect_ratio_blink_threshold = profile.blink_threshold
        cfg.tracking.eye_aspect_ratio_wink_threshold = profile.blink_threshold * 0.9
        print(f"[Status] Calibrated Blink Threshold applied: {profile.blink_threshold:.3f}")
    else:
        print("[Status] Running with default range-of-motion calibration.")

    # 3. Initialize components
    capture = SafeFrameCapture(
        device_index=cfg.camera.device_index,
        width=cfg.camera.width,
        height=cfg.camera.height,
        flip_horizontal=cfg.camera.flip_horizontal
    )

    if not capture.start():
        print(f"[Error] Failed to access local camera index {cfg.camera.device_index}.")
        print("Please verify camera permissions or connection.")
        sys.exit(1)

    tracker = OfflineFaceTracker()
    tremor_filter = KalmanTremorFilter(
        process_noise=cfg.filter.kalman_process_noise,
        measurement_noise=cfg.filter.kalman_measurement_noise,
        spasm_velocity_cutoff=cfg.filter.spasm_velocity_cutoff_px,
        deadzone_radius=cfg.tracking.deadzone_radius_px
    )

    dispatcher = ActionDispatcher(cfg.dispatcher)
    state_machine = GestureStateMachine(cfg.tracking, cfg.fatigue, cfg.sos)

    screen_w, screen_h = dispatcher.screen_width, dispatcher.screen_height

    print("[Status] System active and tracking...")

    try:
        while True:
            ret, frame_rgb = capture.read_frame()
            if not ret or frame_rgb is None:
                time.sleep(0.01)
                continue

            # Process 100% locally
            result = tracker.process_frame(frame_rgb)
            if result is None:
                # Face not in view: safely reset dwell
                state_machine.reset_dwell()
                continue

            # 4. Check for Fatigue & Rest Mode
            if state_machine.check_fatigue():
                print("[Safety] Continuous session limit reached. Entering Rest Mode.")
                time.sleep(1.0)
                continue

            # 5. Check Eye gestures & SOS emergency trigger
            eye_intents = state_machine.process_eyes(result.ear_left, result.ear_right)

            if eye_intents["sos_triggered"]:
                print("[ALERT] Emergency SOS Triggered! Sounding local chime...")
                dispatcher.trigger_sos_alarm(cfg.sos.chime_frequency_hz, cfg.sos.chime_duration_ms)
                time.sleep(1.0)
                continue

            # 6. Normalize Head Pose coordinates
            if profile.calibrated:
                norm_x, norm_y = profile.normalize_head_pose(result.pitch, result.yaw)
            else:
                norm_x = np.clip(result.yaw / cfg.head_pose.max_yaw_angle_deg, -1.0, 1.0)
                norm_y = np.clip(result.pitch / cfg.head_pose.max_pitch_angle_deg, -1.0, 1.0)

            # Map to screen coordinates
            target_x = (norm_x * 0.5 + 0.5) * screen_w
            target_y = (norm_y * 0.5 + 0.5) * screen_h

            # 7. Apply Kalman filter & Spasm suppression
            smooth_x, smooth_y = tremor_filter.update(target_x, target_y)

            # Move cursor
            dispatcher.move_cursor(smooth_x, smooth_y)

            # 8. Check for Dwell Click
            dwell_progress = state_machine.update_dwell((smooth_x, smooth_y))
            if dwell_progress >= 1.0:
                print("[Action] Dwell Click executed.")
                dispatcher.left_click()
                state_machine.reset_dwell()

            # 9. Mouth Open -> Scroll Down
            if result.mar > cfg.tracking.mouth_aspect_ratio_threshold:
                dispatcher.scroll_down()

            # 10. Deliberate Wink Actions
            if eye_intents["left_wink"]:
                print("[Action] Left Wink -> Left Click")
                dispatcher.left_click()
            elif eye_intents["right_wink"]:
                print("[Action] Right Wink -> App Switch")
                dispatcher.switch_app_forward()

            # Small yield to maintain target FPS without CPU hogging
            time.sleep(1.0 / cfg.camera.target_fps)

    except KeyboardInterrupt:
        print("\n[Status] Shutdown signal received. Stopping cleanly...")
    finally:
        capture.stop()
        tracker.close()
        print("[Status] Camera released and memory sanitized.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hands-Free Accessibility System")
    parser.add_argument("--config", default="config/default_config.yaml", help="Path to config YAML")
    parser.add_argument("--profile", default="config/user_profile.json", help="Path to calibration profile")
    args = parser.parse_args()

    run_system(args.config, args.profile)
