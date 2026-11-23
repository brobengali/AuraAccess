"""
Range-of-Motion Calibrator
Measures the individual user's unique motor boundaries:
- Neutral resting head position
- Maximum comfortable yaw (left / right)
- Maximum comfortable pitch (up / down)
- Eye aspect ratios (open vs closed)
Stores only mathematical calibration coefficients locally.
"""

import json
from pathlib import Path
from typing import Optional, Dict
from pydantic import BaseModel, Field


class CalibrationProfile(BaseModel):
    neutral_pitch: float = Field(default=0.0)
    neutral_yaw: float = Field(default=0.0)
    max_yaw_left: float = Field(default=15.0, ge=2.0)
    max_yaw_right: float = Field(default=15.0, ge=2.0)
    max_pitch_up: float = Field(default=12.0, ge=2.0)
    max_pitch_down: float = Field(default=12.0, ge=2.0)
    ear_open_baseline: float = Field(default=0.28, ge=0.05, le=0.65)
    ear_closed_baseline: float = Field(default=0.14, ge=0.01, le=0.50)
    blink_threshold: float = Field(default=0.19, ge=0.05, le=0.55)
    calibrated: bool = Field(default=False)

    def normalize_head_pose(self, pitch: float, yaw: float) -> tuple[float, float]:
        """
        Maps the raw head pitch and yaw into a normalized [-1.0, 1.0] coordinate system
        based on the user's specific motor range.
        """
        # Relative to neutral resting baseline
        rel_yaw = yaw - self.neutral_yaw
        rel_pitch = pitch - self.neutral_pitch

        # Normalize yaw (Horizontal)
        if rel_yaw >= 0:
            norm_x = min(1.0, rel_yaw / max(self.max_yaw_right, 1e-4))
        else:
            norm_x = max(-1.0, rel_yaw / max(self.max_yaw_left, 1e-4))

        # Normalize pitch (Vertical)
        if rel_pitch >= 0:
            norm_y = min(1.0, rel_pitch / max(self.max_pitch_down, 1e-4))
        else:
            norm_y = max(-1.0, rel_pitch / max(self.max_pitch_up, 1e-4))

        return norm_x, norm_y

    def save(self, filepath: Path | str):
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.model_dump_json(indent=2))

    @classmethod
    def load(cls, filepath: Path | str) -> "CalibrationProfile":
        path = Path(filepath)
        if not path.exists():
            return cls(calibrated=False)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(**data)
