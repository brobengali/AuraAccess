"""
Unit & Integration Tests for Assistive System Components
Tests:
1. Config schema validation and out-of-bounds rejection
2. Kalman tremor filter smoothing and spasm suppression
3. Calibration profile coordinate normalization
4. Gesture math (EAR & MAR)
"""

import unittest
import numpy as np
from pathlib import Path

from config.schema import AppConfig, TrackingConfig
from filters.tremor_filter import KalmanTremorFilter
from calibration.calibrator import CalibrationProfile
from vision.gestures import compute_aspect_ratio, calculate_ear, calculate_mar


class TestConfigSchema(unittest.TestCase):
    def test_default_config_load(self):
        config_path = Path("config/default_config.yaml")
        cfg = AppConfig.load_from_yaml(config_path)
        self.assertEqual(cfg.camera.width, 640)
        self.assertEqual(cfg.camera.height, 480)
        self.assertTrue(cfg.filter.algorithm in ["kalman", "dema"])

    def test_invalid_config_rejection(self):
        # Negative camera device index should fail validation
        with self.assertRaises(Exception):
            TrackingConfig(eye_aspect_ratio_blink_threshold=0.99)  # Max is 0.40


class TestTremorFilter(unittest.TestCase):
    def test_deadzone_stability(self):
        kf = KalmanTremorFilter(deadzone_radius=10.0)
        # Initial pos
        kf.update(100.0, 100.0)
        # Small micro-tremor under 10px
        filtered_x, filtered_y = kf.update(103.0, 102.0)
        # Should stay at last clean pos
        self.assertAlmostEqual(filtered_x, 100.0, places=1)
        self.assertAlmostEqual(filtered_y, 100.0, places=1)

    def test_spasm_dampening(self):
        kf = KalmanTremorFilter(spasm_velocity_cutoff=100.0)
        kf.update(100.0, 100.0)
        # Sudden anomalous jump 500px away (spasm)
        filtered_x, filtered_y = kf.update(600.0, 100.0)
        # Should be dampened significantly below 600
        self.assertLess(filtered_x, 300.0)


class TestCalibrationNormalization(unittest.TestCase):
    def test_normalization(self):
        profile = CalibrationProfile(
            neutral_pitch=0.0,
            neutral_yaw=0.0,
            max_yaw_left=20.0,
            max_yaw_right=20.0,
            max_pitch_up=15.0,
            max_pitch_down=15.0,
            calibrated=True
        )

        # Center
        norm_x, norm_y = profile.normalize_head_pose(0.0, 0.0)
        self.assertAlmostEqual(norm_x, 0.0)
        self.assertAlmostEqual(norm_y, 0.0)

        # Max right
        norm_x, _ = profile.normalize_head_pose(0.0, 20.0)
        self.assertAlmostEqual(norm_x, 1.0)

        # Max left
        norm_x, _ = profile.normalize_head_pose(0.0, -20.0)
        self.assertAlmostEqual(norm_x, -1.0)


class TestGestureMath(unittest.TestCase):
    def test_eye_aspect_ratio_open_vs_closed(self):
        # Synthetic open eye coordinates
        p1 = np.array([0.0, 0.0])
        p2 = np.array([5.0, 10.0])
        p3 = np.array([15.0, 10.0])
        p4 = np.array([20.0, 0.0])
        p5 = np.array([15.0, -10.0])
        p6 = np.array([5.0, -10.0])
        ear_open = compute_aspect_ratio(p1, p2, p3, p4, p5, p6)

        # Synthetic closed eye coordinates (vertical points collapse near 0)
        p2_c = np.array([5.0, 1.0])
        p3_c = np.array([15.0, 1.0])
        p5_c = np.array([15.0, -1.0])
        p6_c = np.array([5.0, -1.0])
        ear_closed = compute_aspect_ratio(p1, p2_c, p3_c, p4, p5_c, p6_c)

        self.assertGreater(ear_open, ear_closed)
        self.assertLess(ear_closed, 0.20)


class TestDwellAccumulator(unittest.TestCase):
    def test_dwell_accumulation_and_reset(self):
        import time
        from config.schema import TrackingConfig, FatigueConfig, SOSConfig
        from core.state_machine import GestureStateMachine

        tc = TrackingConfig(dwell_time_seconds=0.4, deadzone_radius_px=14.0)
        fc = FatigueConfig(enabled=False)
        sc = SOSConfig(enabled=False)
        sm = GestureStateMachine(tc, fc, sc)

        # Initial dwell sample
        prog1 = sm.update_dwell((500.0, 500.0))
        self.assertEqual(prog1, 0.0)

        # Still within 48px dwell radius after 220ms
        time.sleep(0.22)
        prog2 = sm.update_dwell((510.0, 505.0))
        self.assertGreater(prog2, 0.3)

        # After another 220ms, should reach full dwell 1.0
        time.sleep(0.22)
        prog3 = sm.update_dwell((512.0, 503.0))
        self.assertAlmostEqual(prog3, 1.0, places=1)

        # Complete click with cooldown
        sm.complete_dwell_click(cooldown_seconds=0.2)
        prog_cooldown = sm.update_dwell((512.0, 503.0))
        self.assertEqual(prog_cooldown, 0.0)


if __name__ == "__main__":
    unittest.main()
