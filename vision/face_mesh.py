"""
MediaPipe FaceLandmarker Processor (Offline Tasks API)
Extracts 478 3D landmarks in real-time.
Runs 100% locally and offline using the local task model in models/face_landmarker.task.
"""

import os
import tempfile
os.environ["MPLCONFIGDIR"] = tempfile.gettempdir()

from pathlib import Path
import numpy as np
from typing import Optional, Tuple, NamedTuple

import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision


class FaceTrackingResult(NamedTuple):
    landmarks_px: np.ndarray          # Shape: (N, 2) in image pixel coordinates
    landmarks_normalized: np.ndarray  # Shape: (N, 3) normalized (0-1)
    nose_tip_px: Tuple[float, float]
    ear_left: float
    ear_right: float
    mar: float
    pitch: float
    yaw: float
    roll: float


class OfflineFaceTracker:
    def __init__(
        self,
        model_path: Optional[str] = None,
        max_num_faces: int = 1,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
    ):
        if model_path is None:
            # Default to local models directory
            root_dir = Path(__file__).resolve().parent.parent
            model_path = str(root_dir / "models" / "face_landmarker.task")

        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model asset not found at: {model_path}")

        base_options = python.BaseOptions(model_asset_path=model_path)
        options = vision.FaceLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.IMAGE,
            num_faces=max_num_faces,
            min_face_detection_confidence=min_detection_confidence,
            min_face_presence_confidence=min_tracking_confidence,
            output_face_blendshapes=True,
        )
        self.detector = vision.FaceLandmarker.create_from_options(options)

    def process_frame(self, frame_rgb: np.ndarray) -> Optional[FaceTrackingResult]:
        """
        Processes an RGB frame and returns computed face geometry & gesture metrics.
        No data is persisted.
        """
        from vision.gestures import (
            calculate_ear,
            calculate_mar,
            estimate_head_pose,
            LEFT_EYE_LANDMARKS,
            RIGHT_EYE_LANDMARKS,
        )

        h, w, _ = frame_rgb.shape
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
        detection_result = self.detector.detect(mp_image)

        if not detection_result.face_landmarks:
            return None

        # Focus on primary user face (index 0)
        face_landmarks = detection_result.face_landmarks[0]
        n_landmarks = len(face_landmarks)

        coords_px = np.empty((n_landmarks, 2), dtype=np.float64)
        coords_norm = np.empty((n_landmarks, 3), dtype=np.float64)

        for i, lm in enumerate(face_landmarks):
            coords_px[i, 0] = lm.x * w
            coords_px[i, 1] = lm.y * h
            coords_norm[i, 0] = lm.x
            coords_norm[i, 1] = lm.y
            coords_norm[i, 2] = lm.z

        # Nose tip landmark index is 1
        nose_tip = (float(coords_px[1, 0]), float(coords_px[1, 1]))

        # Calculate gesture metrics
        ear_l = calculate_ear(coords_px, LEFT_EYE_LANDMARKS)
        ear_r = calculate_ear(coords_px, RIGHT_EYE_LANDMARKS)
        mar = calculate_mar(coords_px)
        pitch, yaw, roll = estimate_head_pose(coords_px, w, h)

        return FaceTrackingResult(
            landmarks_px=coords_px,
            landmarks_normalized=coords_norm,
            nose_tip_px=nose_tip,
            ear_left=ear_l,
            ear_right=ear_r,
            mar=mar,
            pitch=pitch,
            yaw=yaw,
            roll=roll,
        )

    def close(self):
        if self.detector is not None:
            self.detector.close()
            self.detector = None
