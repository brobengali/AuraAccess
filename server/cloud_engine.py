"""
Cloud Demo Engine for AuraAccess
Lightweight, zero-hardware state provider for cloud serverless deployments (e.g. Vercel).
Implements the same API interface as TrackingEngineService without requiring
webcams, MediaPipe, OpenCV, or OS cursor injection.
"""

import threading
from typing import Dict, Any, Optional
from server.profile_store import ProfileStore, UserProfileData


class CloudDemoEngine:
    def __init__(self):
        self._lock = threading.Lock()
        self.profile_store = ProfileStore()
        profiles = self.profile_store.list_profiles()
        self.active_profile: UserProfileData = profiles[0]

        self.sensitivity_multiplier: float = 2.4
        self.engagement_mode: str = "toggle"
        self.engagement_hotkey: str = "shift"
        self.is_tracking_enabled: bool = True
        self.software_engaged: bool = False
        self.latest_jpeg_bytes: Optional[bytes] = None

        self.latest_telemetry: Dict[str, Any] = {
            "face_detected": True,
            "yaw": 0.8,
            "pitch": 0.4,
            "ear_left": 0.28,
            "ear_right": 0.28,
            "mar": 0.03,
            "dwell_progress": 0.0,
            "active_action": None,
            "active_app_title": "Cloud Demo Preview",
            "active_app_category": "general",
            "active_profile_id": self.active_profile.id,
            "tracking_enabled": True,
            "engaged": False,
            "engagement_hotkey": "shift",
            "engagement_mode": "toggle",
            "fps": 30.0,
            "sensitivity": self.sensitivity_multiplier
        }

    def start_background_service(self):
        """No-op on cloud serverless."""
        pass

    def stop_background_service(self):
        """No-op on cloud serverless."""
        pass

    def set_active_profile(self, profile_id: str) -> bool:
        p = self.profile_store.get_profile(profile_id)
        if p:
            with self._lock:
                self.active_profile = p
                self.latest_telemetry["active_profile_id"] = p.id
            return True
        return False

    def set_software_arm(self, armed: bool) -> bool:
        with self._lock:
            self.software_engaged = armed
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
