"""
Assistive Gesture State Machine
Orchestrates:
1. Normal Tracking Mode
2. Dwell-Time Accumulator (Click or Radial HUD trigger)
3. Blink & Wink Intent Validator (eliminates accidental twitches)
4. Fatigue Monitor & Rest Mode
5. Emergency SOS Detector
"""

import time
from enum import Enum, auto
from typing import Optional, List, Tuple, Dict
from config.schema import TrackingConfig, FatigueConfig, SOSConfig


class SystemState(Enum):
    ACTIVE_TRACKING = auto()
    DWELLING = auto()
    RADIAL_HUD = auto()
    REST_MODE = auto()
    SOS_TRIGGERED = auto()


class GestureStateMachine:
    def __init__(self, tracking_cfg: TrackingConfig, fatigue_cfg: FatigueConfig, sos_cfg: SOSConfig):
        self.tracking_cfg = tracking_cfg
        self.fatigue_cfg = fatigue_cfg
        self.sos_cfg = sos_cfg

        self.current_state = SystemState.ACTIVE_TRACKING

        # Dwell tracking
        self.dwell_start_time: Optional[float] = None
        self.dwell_center_pos: Optional[Tuple[float, float]] = None
        self.dwell_cooldown_until: float = 0.0

        # Blink history for deliberate gesture vs involuntary twitch
        self.blink_start_time: Optional[float] = None
        self.recent_blinks: List[float] = []

        # Eye closure timer for SOS
        self.closure_start_time: Optional[float] = None

        # Fatigue tracking
        self.session_start_time = time.monotonic()
        self.last_interaction_time = time.monotonic()
        self.is_rest_mode = False

    def update_dwell(self, current_pos: Tuple[float, float]) -> float:
        """
        Returns dwell progress ratio between 0.0 and 1.0.
        When 1.0 is reached, dwell is complete.
        """
        now = time.monotonic()
        if now < self.dwell_cooldown_until:
            return 0.0

        if self.dwell_center_pos is None:
            self.dwell_center_pos = current_pos
            self.dwell_start_time = now
            return 0.0

        dist = ((current_pos[0] - self.dwell_center_pos[0]) ** 2 +
                (current_pos[1] - self.dwell_center_pos[1]) ** 2) ** 0.5

        # Dwell radius: 48 pixels allows human head stability without false cancels
        dwell_radius = max(48.0, self.tracking_cfg.deadzone_radius_px * 3.5)

        if dist > dwell_radius:
            # User moved beyond dwell zone: reset
            self.dwell_center_pos = current_pos
            self.dwell_start_time = now
            return 0.0

        elapsed = now - (self.dwell_start_time or now)
        dwell_duration = max(0.3, float(self.tracking_cfg.dwell_time_seconds))
        progress = min(1.0, elapsed / dwell_duration)
        return progress

    def complete_dwell_click(self, cooldown_seconds: float = 0.8):
        """Called when dwell click executes: resets accumulator and sets cooldown."""
        self.dwell_cooldown_until = time.monotonic() + cooldown_seconds
        self.dwell_start_time = None
        self.dwell_center_pos = None

    def reset_dwell(self):
        self.dwell_start_time = None
        self.dwell_center_pos = None

    def process_eyes(self, ear_left: float, ear_right: float) -> Dict[str, bool]:
        """
        Analyzes eye aspect ratios and returns confirmed intents:
        - 'blink' (both eyes closed for deliberate duration)
        - 'left_wink' (left eye closed, right open)
        - 'right_wink' (right eye closed, left open)
        - 'sos_triggered' (sustained closure or rapid distress blinks)
        """
        now = time.monotonic()
        results = {
            "blink": False,
            "left_wink": False,
            "right_wink": False,
            "sos_triggered": False
        }

        blink_thresh = self.tracking_cfg.eye_aspect_ratio_blink_threshold
        wink_thresh = self.tracking_cfg.eye_aspect_ratio_wink_threshold

        both_closed = (ear_left < blink_thresh) and (ear_right < blink_thresh)
        left_only = (ear_left < wink_thresh) and (ear_right >= blink_thresh)
        right_only = (ear_right < wink_thresh) and (ear_left >= blink_thresh)

        # SOS Sustained Eye Closure check
        if both_closed:
            if self.closure_start_time is None:
                self.closure_start_time = now
            elif (now - self.closure_start_time) >= self.sos_cfg.sustained_eye_closure_seconds:
                results["sos_triggered"] = True
                self.current_state = SystemState.SOS_TRIGGERED
                return results
        else:
            self.closure_start_time = None

        # Deliberate Blink validation (Filtering out micro-twitches)
        if both_closed:
            if self.blink_start_time is None:
                self.blink_start_time = now
        else:
            if self.blink_start_time is not None:
                duration_ms = (now - self.blink_start_time) * 1000.0
                self.blink_start_time = None
                if self.tracking_cfg.min_blink_duration_ms <= duration_ms <= self.tracking_cfg.max_blink_duration_ms:
                    results["blink"] = True
                    self.recent_blinks.append(now)

        # SOS Rapid Blinking pattern check
        window_start = now - self.sos_cfg.rapid_blink_window_seconds
        self.recent_blinks = [t for t in self.recent_blinks if t >= window_start]
        if len(self.recent_blinks) >= self.sos_cfg.rapid_blink_count:
            results["sos_triggered"] = True
            self.current_state = SystemState.SOS_TRIGGERED
            self.recent_blinks.clear()
            return results

        # Wink validation
        if left_only:
            results["left_wink"] = True
        elif right_only:
            results["right_wink"] = True

        return results

    def check_fatigue(self) -> bool:
        """Checks if session duration exceeds fatigue threshold."""
        if not self.fatigue_cfg.enabled:
            return False
        elapsed_min = (time.monotonic() - self.session_start_time) / 60.0
        if elapsed_min >= self.fatigue_cfg.max_continuous_minutes:
            self.is_rest_mode = True
            self.current_state = SystemState.REST_MODE
            return True
        return False
