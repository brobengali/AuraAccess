"""
Multi-User Profile Store
Manages multiple user profiles in profiles/{profile_id}.json.
Allows any user to create, save, delete, and switch profiles without hardcoding.
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class UserProfileData(BaseModel):
    id: str
    name: str
    neutral_pitch: float = 0.0
    neutral_yaw: float = 0.0
    max_yaw_left: float = 15.0
    max_yaw_right: float = 15.0
    max_pitch_up: float = 12.0
    max_pitch_down: float = 12.0
    ear_open_baseline: float = 0.28
    ear_closed_baseline: float = 0.14
    blink_threshold: float = 0.20
    calibrated: bool = False
    gesture_mappings: Dict[str, Dict[str, str]] = Field(
        default_factory=lambda: {
            "general": {
                "left_wink": "LEFT_CLICK",
                "right_wink": "ALT_TAB",
                "mouth_open": "SCROLL_DOWN",
                "dwell": "LEFT_CLICK"
            },
            "media": {
                "left_wink": "SPACE_PLAY_PAUSE",
                "right_wink": "NEXT_TRACK",
                "mouth_open": "SCROLL_DOWN",
                "dwell": "LEFT_CLICK"
            },
            "document": {
                "left_wink": "PAGE_DOWN",
                "right_wink": "PAGE_UP",
                "mouth_open": "SCROLL_DOWN",
                "dwell": "LEFT_CLICK"
            }
        }
    )


BASE_DIR = Path(__file__).resolve().parent.parent


class ProfileStore:
    def __init__(self, profiles_dir: Optional[Path | str] = None):
        if profiles_dir is None:
            self.profiles_dir = BASE_DIR / "profiles"
        else:
            self.profiles_dir = Path(profiles_dir)
            if not self.profiles_dir.is_absolute():
                self.profiles_dir = BASE_DIR / self.profiles_dir

        try:
            self.profiles_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        self._ensure_default_profile()

    def _sanitize_id(self, name: str) -> str:
        s = re.sub(r'[^a-zA-Z0-9_-]', '_', name.strip().lower())
        return s or "user_profile"

    def _ensure_default_profile(self):
        # Check if any profile exists, if user_profile.json exists in config, migrate it!
        existing = list(self.profiles_dir.glob("*.json")) if self.profiles_dir.exists() else []
        legacy_file = BASE_DIR / "config" / "user_profile.json"

        if not existing and legacy_file.exists():
            try:
                with open(legacy_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                initial_profile = UserProfileData(
                    id="primary_user",
                    name="Primary User",
                    **data
                )
                self.save_profile(initial_profile)
                return
            except Exception:
                pass

        if not existing:
            default_p = UserProfileData(
                id="default_user",
                name="Default User",
                calibrated=False
            )
            self.save_profile(default_p)

    def list_profiles(self) -> List[UserProfileData]:
        profiles = []
        if self.profiles_dir.exists():
            for p in self.profiles_dir.glob("*.json"):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    profiles.append(UserProfileData(**data))
                except Exception:
                    continue
        if not profiles:
            profiles.append(UserProfileData(id="primary_user", name="Primary User", calibrated=True))
        return sorted(profiles, key=lambda x: x.name)

    def get_profile(self, profile_id: str) -> Optional[UserProfileData]:
        p = self.profiles_dir / f"{self._sanitize_id(profile_id)}.json"
        if not p.exists():
            return None
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            return UserProfileData(**data)
        except Exception:
            return None

    def save_profile(self, profile: UserProfileData) -> UserProfileData:
        clean_id = self._sanitize_id(profile.id)
        profile.id = clean_id
        try:
            self.profiles_dir.mkdir(parents=True, exist_ok=True)
            target = self.profiles_dir / f"{clean_id}.json"
            with open(target, "w", encoding="utf-8") as f:
                f.write(profile.model_dump_json(indent=2))
        except Exception:
            pass  # Cloud/serverless read-only filesystem
        return profile

    def delete_profile(self, profile_id: str) -> bool:
        clean_id = self._sanitize_id(profile_id)
        target = self.profiles_dir / f"{clean_id}.json"
        try:
            if target.exists():
                target.unlink()
                return True
        except Exception:
            pass
        return False
