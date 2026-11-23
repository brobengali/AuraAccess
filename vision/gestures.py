"""
Facial Geometry & Gesture Mathematics
Computes:
1. Eye Aspect Ratio (EAR) for left/right blinks & winks
2. Mouth Aspect Ratio (MAR) for mouth opening / smile detection
3. Head Pose Orientation (Yaw, Pitch, Roll) using 3D PnP
"""

import numpy as np
from typing import List, Tuple, Dict


# MediaPipe FaceMesh key landmark indices
# Left eye
LEFT_EYE_LANDMARKS = [362, 385, 387, 263, 373, 380]
# Right eye
RIGHT_EYE_LANDMARKS = [33, 160, 158, 133, 153, 144]
# Mouth
MOUTH_OUTER_LANDMARKS = [61, 291, 13, 14, 17, 0]
# 3D Head model points for perspective-n-point pose estimation
MODEL_3D_POINTS = np.array([
    (0.0, 0.0, 0.0),          # Nose tip
    (0.0, -330.0, -65.0),     # Chin
    (-225.0, 170.0, -135.0),  # Left eye left corner
    (225.0, 170.0, -135.0),   # Right eye right corner
    (-150.0, -150.0, -125.0), # Left Mouth corner
    (150.0, -150.0, -125.0)   # Right mouth corner
], dtype=np.float64)

# Corresponding FaceMesh landmark indices for 3D PnP
FACE_3D_INDICES = [1, 199, 33, 263, 61, 291]


def compute_aspect_ratio(p1: np.ndarray, p2: np.ndarray, p3: np.ndarray,
                         p4: np.ndarray, p5: np.ndarray, p6: np.ndarray) -> float:
    """
    Computes Eye Aspect Ratio (EAR) based on Soukupová & Čech formula:
    EAR = (||p2 - p6|| + ||p3 - p5||) / (2 * ||p1 - p4||)
    """
    vertical_1 = np.linalg.norm(p2 - p6)
    vertical_2 = np.linalg.norm(p3 - p5)
    horizontal = np.linalg.norm(p1 - p4)

    if horizontal < 1e-6:
        return 0.0

    return float((vertical_1 + vertical_2) / (2.0 * horizontal))


def calculate_ear(landmarks_2d: np.ndarray, indices: List[int]) -> float:
    pts = [landmarks_2d[idx] for idx in indices]
    return compute_aspect_ratio(pts[0], pts[1], pts[2], pts[3], pts[4], pts[5])


def calculate_mar(landmarks_2d: np.ndarray) -> float:
    """
    Computes Mouth Aspect Ratio (MAR):
    MAR = ||top_lip - bottom_lip|| / ||left_corner - right_corner||
    """
    left_corner = landmarks_2d[61]
    right_corner = landmarks_2d[291]
    top_lip = landmarks_2d[13]
    bottom_lip = landmarks_2d[14]

    horizontal = np.linalg.norm(left_corner - right_corner)
    vertical = np.linalg.norm(top_lip - bottom_lip)

    if horizontal < 1e-6:
        return 0.0

    return float(vertical / horizontal)


def estimate_head_pose(landmarks_2d_px: np.ndarray, img_w: int, img_h: int) -> Tuple[float, float, float]:
    """
    Calculates Head Pose (Pitch, Yaw, Roll in degrees) using cv2.solvePnP.
    Returns: (pitch_deg, yaw_deg, roll_deg)
    """
    import cv2

    image_points = np.array([
        landmarks_2d_px[idx] for idx in FACE_3D_INDICES
    ], dtype=np.float64)

    focal_length = img_w
    center = (img_w / 2.0, img_h / 2.0)
    camera_matrix = np.array([
        [focal_length, 0, center[0]],
        [0, focal_length, center[1]],
        [0, 0, 1]
    ], dtype=np.float64)

    dist_coeffs = np.zeros((4, 1), dtype=np.float64)

    success, rotation_vector, translation_vector = cv2.solvePnP(
        MODEL_3D_POINTS,
        image_points,
        camera_matrix,
        dist_coeffs,
        flags=cv2.SOLVEPNP_ITERATIVE
    )

    if not success:
        return 0.0, 0.0, 0.0

    # Convert rotation vector to rotation matrix
    rmat, _ = cv2.Rodrigues(rotation_vector)
    # Decompose rotation matrix into Euler angles
    angles, _, _, _, _, _ = cv2.RQDecomp3x3(rmat)

    pitch = float(angles[0])
    yaw = float(angles[1])
    roll = float(angles[2])

    return pitch, yaw, roll
