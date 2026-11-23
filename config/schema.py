"""
Configuration Schema & Validation
Ensures zero hardcoding and prevents dangerous or out-of-bounds parameters.
"""

from typing import Literal, Dict
from pydantic import BaseModel, Field, field_validator
import yaml
from pathlib import Path


class CameraConfig(BaseModel):
    device_index: int = Field(default=0, ge=0)
    width: int = Field(default=640, ge=320, le=1920)
    height: int = Field(default=480, ge=240, le=1080)
    target_fps: int = Field(default=30, ge=10, le=120)
    flip_horizontal: bool = True


class TrackingConfig(BaseModel):
    eye_aspect_ratio_blink_threshold: float = Field(default=0.19, ge=0.05, le=0.40)
    eye_aspect_ratio_wink_threshold: float = Field(default=0.17, ge=0.05, le=0.40)
    mouth_aspect_ratio_threshold: float = Field(default=0.45, ge=0.20, le=0.90)
    eyebrow_raise_ratio_threshold: float = Field(default=0.04, ge=0.01, le=0.15)
    min_blink_duration_ms: int = Field(default=120, ge=50, le=500)
    max_blink_duration_ms: int = Field(default=500, ge=200, le=1500)
    dwell_time_seconds: float = Field(default=1.2, ge=0.4, le=4.0)
    deadzone_radius_px: float = Field(default=12.0, ge=0.0, le=100.0)


class HeadPoseConfig(BaseModel):
    yaw_sensitivity: float = Field(default=1.8, ge=0.2, le=10.0)
    pitch_sensitivity: float = Field(default=2.2, ge=0.2, le=10.0)
    max_yaw_angle_deg: float = Field(default=35.0, ge=5.0, le=90.0)
    max_pitch_angle_deg: float = Field(default=25.0, ge=5.0, le=90.0)
    invert_x: bool = False
    invert_y: bool = False


class FilterConfig(BaseModel):
    algorithm: Literal["kalman", "dema"] = "kalman"
    kalman_process_noise: float = Field(default=0.005, gt=0.0, le=1.0)
    kalman_measurement_noise: float = Field(default=0.08, gt=0.0, le=2.0)
    spasm_velocity_cutoff_px: float = Field(default=250.0, ge=50.0, le=2000.0)


class FatigueConfig(BaseModel):
    enabled: bool = True
    max_continuous_minutes: int = Field(default=20, ge=5, le=180)
    blink_rate_warning_per_min: int = Field(default=8, ge=2, le=30)
    auto_rest_timeout_seconds: int = Field(default=60, ge=10, le=600)


class SOSConfig(BaseModel):
    enabled: bool = True
    sustained_eye_closure_seconds: float = Field(default=3.5, ge=2.0, le=10.0)
    rapid_blink_count: int = Field(default=5, ge=3, le=10)
    rapid_blink_window_seconds: float = Field(default=2.5, ge=1.0, le=5.0)
    chime_frequency_hz: int = Field(default=900, ge=200, le=5000)
    chime_duration_ms: int = Field(default=800, ge=100, le=5000)


class HUDConfig(BaseModel):
    enabled: bool = True
    radius_px: int = Field(default=220, ge=100, le=600)
    opacity: float = Field(default=0.82, ge=0.2, le=1.0)
    dwell_trigger_seconds: float = Field(default=1.0, ge=0.3, le=3.0)
    quadrant_actions: Dict[str, str] = Field(
        default_factory=lambda: {
            "top": "SCROLL_UP",
            "bottom": "SCROLL_DOWN",
            "left": "ALT_TAB",
            "right": "CLOSE_APP",
            "center": "DWELL_CLICK",
        }
    )


class DispatcherConfig(BaseModel):
    max_actions_per_second: int = Field(default=2, ge=1, le=10)
    scroll_speed: int = Field(default=150, ge=20, le=1000)
    killswitch_key: str = "esc"
    safe_mode: bool = True


class EngagementConfig(BaseModel):
    mode: Literal["hold", "toggle"] = "hold"
    hotkey: str = Field(default="shift", pattern=r"^(shift|ctrl|alt|f8|caps_lock)$")
    initial_engaged: bool = False


class AppConfig(BaseModel):
    camera: CameraConfig = Field(default_factory=CameraConfig)
    tracking: TrackingConfig = Field(default_factory=TrackingConfig)
    head_pose: HeadPoseConfig = Field(default_factory=HeadPoseConfig)
    filter: FilterConfig = Field(default_factory=FilterConfig)
    fatigue: FatigueConfig = Field(default_factory=FatigueConfig)
    sos: SOSConfig = Field(default_factory=SOSConfig)
    hud: HUDConfig = Field(default_factory=HUDConfig)
    dispatcher: DispatcherConfig = Field(default_factory=DispatcherConfig)
    engagement: EngagementConfig = Field(default_factory=EngagementConfig)

    @classmethod
    def load_from_yaml(cls, path: Path | str) -> "AppConfig":
        file_path = Path(path)
        if not file_path.is_file():
            raise FileNotFoundError(f"Configuration file not found at: {file_path}")
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return cls(**data)
