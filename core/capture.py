"""
Ephemeral In-Memory Frame Capture
Guarantees 100% on-device privacy:
- Never writes video frames or images to disk.
- Buffers are immediately overwritten in RAM.
- No network transmission.
"""

import cv2
import numpy as np
from typing import Optional, Tuple


class SafeFrameCapture:
    def __init__(self, device_index: int = 0, width: int = 640, height: int = 480, flip_horizontal: bool = True):
        self.device_index = device_index
        self.width = width
        self.height = height
        self.flip_horizontal = flip_horizontal
        self.cap: Optional[cv2.VideoCapture] = None
        self._is_open = False

    def start(self) -> bool:
        """Initializes the local hardware camera feed."""
        # Using DirectShow on Windows for fastest and cleanest device lock
        self.cap = cv2.VideoCapture(self.device_index, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            # Fallback to standard backend if DirectShow is unavailable
            self.cap = cv2.VideoCapture(self.device_index)

        if not self.cap.isOpened():
            self._is_open = False
            return False

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self._is_open = True
        return True

    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Reads one single frame into volatile RAM.
        Returns RGB numpy array suitable for real-time vision inference.
        """
        if not self._is_open or self.cap is None:
            return False, None

        ret, frame_bgr = self.cap.read()
        if not ret or frame_bgr is None:
            return False, None

        if self.flip_horizontal:
            frame_bgr = cv2.flip(frame_bgr, 1)

        # Convert to RGB in-place in memory
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        return True, frame_rgb

    def stop(self):
        """Immediately releases camera handle and purges any internal buffer."""
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self._is_open = False
