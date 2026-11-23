"""
Signal Conditioning & Tremor Suppression Filter
Uses a 2D Kalman Filter and adaptive spasm dampening to eliminate
involuntary head tremors and accidental spastic jerks.
"""

import numpy as np
from typing import Tuple


class KalmanTremorFilter:
    def __init__(
        self,
        process_noise: float = 0.005,
        measurement_noise: float = 0.08,
        spasm_velocity_cutoff: float = 250.0,
        deadzone_radius: float = 12.0,
    ):
        self.process_noise = process_noise
        self.measurement_noise = measurement_noise
        self.spasm_velocity_cutoff = spasm_velocity_cutoff
        self.deadzone_radius = deadzone_radius

        # State vector: [x, y, dx, dy]^T
        self.state = np.zeros(4, dtype=np.float64)

        # State transition matrix F
        self.F = np.array([
            [1, 0, 1, 0],
            [0, 1, 0, 1],
            [0, 0, 1, 0],
            [0, 0, 0, 1]
        ], dtype=np.float64)

        # Measurement matrix H
        self.H = np.array([
            [1, 0, 0, 0],
            [0, 1, 0, 0]
        ], dtype=np.float64)

        # Covariance matrices
        self.P = np.eye(4, dtype=np.float64) * 10.0
        self.Q = np.eye(4, dtype=np.float64) * self.process_noise
        self.R = np.eye(2, dtype=np.float64) * self.measurement_noise

        self.initialized = False
        self.last_clean_pos = (0.0, 0.0)

    def update(self, raw_x: float, raw_y: float) -> Tuple[float, float]:
        """
        Filters raw landmark/head coordinates.
        Suppresses high-frequency tremors, dampens spastic jerks,
        and applies deadband stability.
        """
        measurement = np.array([raw_x, raw_y], dtype=np.float64)

        if not self.initialized:
            self.state[0] = raw_x
            self.state[1] = raw_y
            self.state[2] = 0.0
            self.state[3] = 0.0
            self.last_clean_pos = (raw_x, raw_y)
            self.initialized = True
            return raw_x, raw_y

        # Predict step
        state_pred = self.F @ self.state
        P_pred = (self.F @ self.P @ self.F.T) + self.Q

        # Check for sudden spastic jerk (instantaneous velocity anomaly)
        displacement = np.linalg.norm(measurement - np.array(self.last_clean_pos))
        is_spasm = displacement > self.spasm_velocity_cutoff
        if is_spasm:
            # Dampen anomalous jerk by interpolating towards predicted position
            measurement = self.last_clean_pos + (measurement - self.last_clean_pos) * 0.15

        # Update step (Measurement residual)
        y = measurement - (self.H @ state_pred)
        S = (self.H @ P_pred @ self.H.T) + self.R
        K = P_pred @ self.H.T @ np.linalg.inv(S)

        self.state = state_pred + (K @ y)
        self.P = (np.eye(4) - (K @ self.H)) @ P_pred

        filtered_x = float(self.state[0])
        filtered_y = float(self.state[1])

        # Deadzone stabilization: ignore micro-tremors below threshold
        dist_from_last = np.hypot(filtered_x - self.last_clean_pos[0], filtered_y - self.last_clean_pos[1])
        if dist_from_last < self.deadzone_radius:
            return self.last_clean_pos

        # Adaptive Swift Responsiveness (only during normal intentional motion, not spasms):
        # If user is moving intentionally (dist > deadzone), blend towards raw measurement
        # to eliminate sluggish lag and provide swift, crisp physical mouse responsiveness.
        if not is_spasm:
            swiftness_alpha = float(np.clip((dist_from_last - self.deadzone_radius) / 12.0, 0.0, 0.75))
            final_x = filtered_x * (1.0 - swiftness_alpha) + raw_x * swiftness_alpha
            final_y = filtered_y * (1.0 - swiftness_alpha) + raw_y * swiftness_alpha
        else:
            final_x = filtered_x
            final_y = filtered_y

        self.last_clean_pos = (final_x, final_y)
        return final_x, final_y

    def reset(self, init_x: float = 0.0, init_y: float = 0.0):
        self.state = np.array([init_x, init_y, 0.0, 0.0], dtype=np.float64)
        self.P = np.eye(4, dtype=np.float64) * 10.0
        self.last_clean_pos = (init_x, init_y)
        self.initialized = False
