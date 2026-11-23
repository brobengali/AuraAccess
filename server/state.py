"""
Live Telemetry & Tracking Engine Service (Direct Nose-Tip Tracking + Clutch Engagement)
Features:
- Clutch / Engagement hotkey (e.g. Hold Shift to control mouse; release Shift to stop instantly).
- Prevents accidental cursor hijacking for users with motor function.
- Direct Nose-Tip landmark tracking for natural, jitter-free cursor steering.
- Attaches to WinSta0\\default desktop station for physical cursor interaction.
"""

import os
import time
import threading
from pathlib import Path
import cv2
import numpy as np
from typing import Optional, Dict, Any, List

from config.schema import AppConfig
from core.capture import SafeFrameCapture
from vision.face_mesh import OfflineFaceTracker
from filters.tremor_filter import KalmanTremorFilter
from calibration.calibrator import CalibrationProfile
from dispatcher.action_controller import (
    ActionDispatcher,
    attach_to_interactive_desktop,
    is_hotkey_down
)
from core.state_machine import GestureStateMachine, SystemState
from server.app_detector import get_active_window_context
from server.profile_store import ProfileStore, UserProfileData


BASE_DIR = Path(__file__).resolve().parent.parent


class TrackingEngineService:
    def __init__(self, config_path: Optional[str | Path] = None):
        if config_path is None:
            self.config_path = BASE_DIR / "config" / "default_config.yaml"
        else:
            self.config_path = Path(config_path)
            if not self.config_path.is_absolute():
                self.config_path = BASE_DIR / self.config_path

        try:
            self.cfg = AppConfig.load_from_yaml(self.config_path)
        except Exception:
            self.cfg = AppConfig()

        self.profile_store = ProfileStore(BASE_DIR / "profiles")

        # Load active profile
        profiles = self.profile_store.list_profiles()
        self.active_profile: UserProfileData = profiles[0]

        # Engagement / Clutch settings (Shift key by default)
        self.engagement_mode = self.cfg.engagement.mode        # "hold" or "toggle"
        self.engagement_hotkey = self.cfg.engagement.hotkey    # "shift"
        self.is_tracking_enabled = True                        # Master switch enabled
        self.toggle_engaged = False
        self.software_engaged = False                          # Web button software lock
        self.last_key_state = False

        self.is_running = False
        self.thread: Optional[threading.Thread] = None

        # Sensitivity multiplier (default 2.4x for natural reach)
        self.sensitivity_multiplier = 2.4

        # Neutral resting nose baseline (auto-calibrates in the first frame)
        self.neutral_nose_x = 320.0
        self.neutral_nose_y = 240.0
        self.has_neutral_nose = False

        # In-memory latest annotated JPEG buffer for /video_feed
        self.latest_jpeg_bytes: Optional[bytes] = None

        # Real-time Telemetry
        self.latest_telemetry: Dict[str, Any] = {
            "face_detected": False,
            "yaw": 0.0,
            "pitch": 0.0,
            "ear_left": 0.0,
            "ear_right": 0.0,
            "mar": 0.0,
            "dwell_progress": 0.0,
            "active_action": None,
            "active_app_title": "Desktop",
            "active_app_category": "general",
            "active_profile_id": self.active_profile.id,
            "tracking_enabled": True,
            "engaged": False,
            "engagement_hotkey": self.engagement_hotkey,
            "engagement_mode": self.engagement_mode,
            "fps": 0.0,
            "sensitivity": self.sensitivity_multiplier
        }

        self._lock = threading.Lock()

    def recenter(self):
        """Recenters the cursor to current head position."""
        self.has_neutral_nose = False

    def set_active_profile(self, profile_id: str) -> bool:
        p = self.profile_store.get_profile(profile_id)
        if p:
            with self._lock:
                self.active_profile = p
                self.latest_telemetry["active_profile_id"] = p.id
                self.has_neutral_nose = False
            return True
        return False

    def set_software_arm(self, armed: bool) -> bool:
        with self._lock:
            self.software_engaged = armed
            self.toggle_engaged = armed
            self.latest_telemetry["engaged"] = armed
            return self.software_engaged

    def set_engagement_config(self, mode: str, hotkey: str):
        with self._lock:
            self.engagement_mode = mode
            self.engagement_hotkey = hotkey.lower().strip()
            self.latest_telemetry["engagement_mode"] = self.engagement_mode
            self.latest_telemetry["engagement_hotkey"] = self.engagement_hotkey

    def toggle_tracking(self, enable: Optional[bool] = None) -> bool:
        with self._lock:
            if enable is None:
                self.is_tracking_enabled = not self.is_tracking_enabled
            else:
                self.is_tracking_enabled = enable
            self.latest_telemetry["tracking_enabled"] = self.is_tracking_enabled
            return self.is_tracking_enabled

    def set_sensitivity(self, val: float):
        with self._lock:
            self.sensitivity_multiplier = max(0.5, min(6.0, val))
            self.latest_telemetry["sensitivity"] = self.sensitivity_multiplier

    def start_background_service(self):
        # Do not start camera thread in serverless cloud environments (Vercel / Lambda)
        if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
            return
        if self.is_running:
            return
        self.is_running = True
        self.thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.thread.start()

    def stop_background_service(self):
        self.is_running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)

    def _worker_loop(self):
        attach_to_interactive_desktop()

        capture = SafeFrameCapture(
            device_index=self.cfg.camera.device_index,
            width=self.cfg.camera.width,
            height=self.cfg.camera.height,
            flip_horizontal=self.cfg.camera.flip_horizontal
        )

        if not capture.start():
            print("[Error] Camera capture could not be opened by background service.")
            self.is_running = False
            return

        tracker = OfflineFaceTracker()
        tremor_filter = KalmanTremorFilter(
            process_noise=0.015,
            measurement_noise=0.05,
            spasm_velocity_cutoff=300.0,
            deadzone_radius=2.0
        )

        dispatcher = ActionDispatcher(self.cfg.dispatcher)
        state_machine = GestureStateMachine(self.cfg.tracking, self.cfg.fatigue, self.cfg.sos)
        screen_w, screen_h = dispatcher.screen_width, dispatcher.screen_height

        frame_count = 0
        fps_start = time.monotonic()
        current_fps = 0.0

        try:
            while self.is_running:
                try:
                    ret, frame_rgb = capture.read_frame()
                    if not ret or frame_rgb is None:
                        time.sleep(0.01)
                        continue

                    # FPS calculation
                    frame_count += 1
                    now = time.monotonic()
                    if now - fps_start >= 1.0:
                        current_fps = frame_count / (now - fps_start)
                        frame_count = 0
                        fps_start = now

                    # Context detection
                    app_ctx = get_active_window_context()

                    # Process face mesh
                    res = tracker.process_frame(frame_rgb)
                    display_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)

                    if res is None:
                        cv2.putText(display_bgr, "Looking for face...", (20, 40),
                                    cv2.FONT_HERSHEY_DUPLEX, 0.7, (0, 165, 255), 2)
                        _, jpeg = cv2.imencode(".jpg", display_bgr, [cv2.IMWRITE_JPEG_QUALITY, 70])
                        with self._lock:
                            self.latest_jpeg_bytes = jpeg.tobytes()
                            self.latest_telemetry["face_detected"] = False
                            self.latest_telemetry["fps"] = round(current_fps, 1)
                            self.latest_telemetry["active_app_title"] = app_ctx.title
                            self.latest_telemetry["active_app_category"] = app_ctx.category
                            self.latest_telemetry["engaged"] = False
                        state_machine.reset_dwell()
                        time.sleep(0.01)
                        continue

                    # Current nose position in camera pixels (0 to 640, 0 to 480)
                    nx = float(res.nose_tip_px[0])
                    ny = float(res.nose_tip_px[1])

                    # Auto-seed neutral resting nose baseline on first detection
                    if not self.has_neutral_nose:
                        self.neutral_nose_x = nx
                        self.neutral_nose_y = ny
                        self.has_neutral_nose = True
                        tremor_filter.reset(screen_w / 2.0, screen_h / 2.0)

                    # CHECK CLUTCH / ENGAGEMENT HOTKEY STATE (Shift Key Single-Tap or Hold)
                    key_down = is_hotkey_down(self.engagement_hotkey)
                    if self.engagement_mode == "toggle":
                        # Single-tap toggle: tap Shift once for access, tap again to decline
                        if key_down and not self.last_key_state:
                            self.toggle_engaged = not self.toggle_engaged
                            try:
                                import winsound
                                if self.toggle_engaged:
                                    winsound.Beep(1175, 50)  # High chime: D6 (Access Granted)
                                else:
                                    winsound.Beep(587, 50)   # Low chime: D5 (Access Declined)
                            except Exception:
                                pass
                        cursor_engaged = self.toggle_engaged or self.software_engaged
                        self.last_key_state = key_down
                    elif self.engagement_mode == "hold":
                        cursor_engaged = key_down or self.software_engaged
                    else:
                        cursor_engaged = self.toggle_engaged or self.software_engaged

                    # Master killswitch/toggle
                    if not self.is_tracking_enabled:
                        cursor_engaged = False

                    with self._lock:
                        p = self.active_profile
                        sensitivity = self.sensitivity_multiplier

                    # DIRECT NOSE TIP DISPLACEMENT MAPPING (Swift pointer acceleration)
                    dx = nx - self.neutral_nose_x
                    dy = ny - self.neutral_nose_y

                    # Pointer acceleration curve (Swift & effortless cross-screen reach)
                    abs_dx = abs(dx)
                    abs_dy = abs(dy)
                    accel_x = 1.0 + 0.025 * min(abs_dx, 40.0)
                    accel_y = 1.0 + 0.025 * min(abs_dy, 35.0)

                    norm_x = (dx / 46.0) * sensitivity * accel_x
                    norm_y = (dy / 35.0) * sensitivity * accel_y

                    norm_x = float(np.clip(norm_x, -1.0, 1.0))
                    norm_y = float(np.clip(norm_y, -1.0, 1.0))

                    target_x = (norm_x * 0.5 + 0.5) * screen_w
                    target_y = (norm_y * 0.5 + 0.5) * screen_h

                    # Smooth with tremor filter
                    smooth_x, smooth_y = tremor_filter.update(target_x, target_y)

                    # Dwell accumulation (48px dwell radius allows reliable click on any button)
                    if cursor_engaged:
                        dwell_progress = state_machine.update_dwell((smooth_x, smooth_y))
                    else:
                        dwell_progress = 0.0
                        state_machine.reset_dwell()

                    eye_intents = state_machine.process_eyes(res.ear_left, res.ear_right)

                    # Draw annotated overlay on display frame for /video_feed
                    dot_color = (0, 255, 0) if cursor_engaged else (140, 140, 140)
                    cv2.circle(display_bgr, (int(nx), int(ny)), 6, dot_color, -1)
                    cv2.circle(display_bgr, (int(self.neutral_nose_x), int(self.neutral_nose_y)), 4, (255, 200, 0), 1)

                    # Dwell accumulation circle around nose tip
                    if cursor_engaged and dwell_progress > 0.04:
                        arc_angle = int(360 * min(1.0, dwell_progress))
                        cv2.ellipse(display_bgr, (int(nx), int(ny)), (18, 18), -90, 0, arc_angle, (0, 255, 255), 2)

                    status_str = f"ACCESS GRANTED (TAP {self.engagement_hotkey.upper()} TO LOCK)" if cursor_engaged else f"LOCKED (TAP {self.engagement_hotkey.upper()} FOR ACCESS)"
                    status_col = (0, 255, 0) if cursor_engaged else (0, 165, 255)
                    cv2.putText(display_bgr, status_str, (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.55, status_col, 2)

                    _, jpeg = cv2.imencode(".jpg", display_bgr, [cv2.IMWRITE_JPEG_QUALITY, 70])

                    with self._lock:
                        self.latest_jpeg_bytes = jpeg.tobytes()

                    # Action mapping per application category
                    active_action_name = None
                    category = app_ctx.category
                    mappings = p.gesture_mappings.get(category, p.gesture_mappings.get("general", {}))

                    # Move physical Windows cursor ONLY when actively engaged!
                    if cursor_engaged:
                        dispatcher.move_cursor(smooth_x, smooth_y)

                        # Dwell Click Execution (with audible confirmation & cooldown)
                        if dwell_progress >= 1.0:
                            action_to_run = mappings.get("dwell", "LEFT_CLICK")
                            self._execute_action(dispatcher, action_to_run)
                            active_action_name = f"Dwell -> {action_to_run}"
                            try:
                                import winsound
                                winsound.Beep(1600, 45)  # Crisp click feedback chime
                            except Exception:
                                pass
                            state_machine.complete_dwell_click(cooldown_seconds=0.8)

                        if eye_intents["left_wink"]:
                            action_to_run = mappings.get("left_wink", "LEFT_CLICK")
                            self._execute_action(dispatcher, action_to_run)
                            active_action_name = f"Left Wink -> {action_to_run}"

                        elif eye_intents["right_wink"]:
                            action_to_run = mappings.get("right_wink", "ALT_TAB")
                            self._execute_action(dispatcher, action_to_run)
                            active_action_name = f"Right Wink -> {action_to_run}"

                        if res.mar > self.cfg.tracking.mouth_aspect_ratio_threshold:
                            action_to_run = mappings.get("mouth_open", "SCROLL_DOWN")
                            self._execute_action(dispatcher, action_to_run)
                            active_action_name = f"Mouth Open -> {action_to_run}"

                        if eye_intents["sos_triggered"]:
                            dispatcher.trigger_sos_alarm(self.cfg.sos.chime_frequency_hz, self.cfg.sos.chime_duration_ms)
                            active_action_name = "SOS ALARM TRIGGERED"
                    else:
                        state_machine.reset_dwell()

                    # Update live telemetry state
                    with self._lock:
                        self.latest_telemetry = {
                            "face_detected": True,
                            "yaw": round(float(res.yaw), 1),
                            "pitch": round(float(res.pitch), 1),
                            "ear_left": round(float(res.ear_left), 3),
                            "ear_right": round(float(res.ear_right), 3),
                            "mar": round(float(res.mar), 3),
                            "dwell_progress": round(dwell_progress if cursor_engaged else 0.0, 2),
                            "active_action": active_action_name,
                            "active_app_title": app_ctx.title,
                            "active_app_category": app_ctx.category,
                            "active_profile_id": p.id,
                            "tracking_enabled": self.is_tracking_enabled,
                            "engaged": cursor_engaged,
                            "engagement_hotkey": self.engagement_hotkey,
                            "engagement_mode": self.engagement_mode,
                            "fps": round(current_fps, 1),
                            "sensitivity": sensitivity
                        }

                    time.sleep(1.0 / self.cfg.camera.target_fps)
                except Exception as inner_err:
                    time.sleep(0.02)
                    continue

        finally:
            capture.stop()
            tracker.close()

    def _execute_action(self, dispatcher: ActionDispatcher, action_code: str):
        """Executes mapped actions safely."""
        import pyautogui
        action = action_code.upper()
        if action == "LEFT_CLICK":
            dispatcher.left_click()
        elif action == "RIGHT_CLICK":
            dispatcher.right_click()
        elif action == "SCROLL_DOWN":
            dispatcher.scroll_down()
        elif action == "SCROLL_UP":
            dispatcher.scroll_up()
        elif action == "ALT_TAB":
            dispatcher.switch_app_forward()
        elif action == "CLOSE_APP":
            dispatcher.close_current_app()
        elif action == "SPACE_PLAY_PAUSE":
            pyautogui.press('space')
        elif action == "PAGE_DOWN":
            pyautogui.press('pagedown')
        elif action == "PAGE_UP":
            pyautogui.press('pageup')
