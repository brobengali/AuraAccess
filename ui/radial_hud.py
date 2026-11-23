"""
Translucent Floating Radial HUD (Pie Menu)
A frameless, always-on-top, semi-transparent overlay.
Allows motor-impaired users to trigger complex desktop actions
(Scroll, App Switch, Close Window) without fine motor precision.
"""

import sys
import math
from typing import Optional, Callable
from PyQt6.QtCore import Qt, QPoint, QRectF, pyqtSignal
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QBrush


class RadialHUDWidget(QWidget):
    action_triggered = pyqtSignal(str)

    def __init__(self, radius: int = 220, opacity: float = 0.82):
        super().__init__()
        self.radius = radius
        self.widget_opacity = opacity
        self.dwell_progress = 0.0
        self.active_quadrant: Optional[str] = None
        self.center_label = "Dwell Click"

        self.quadrants = {
            "top": {"label": "▲ Scroll Up", "action": "SCROLL_UP", "color": QColor(41, 128, 185)},
            "bottom": {"label": "▼ Scroll Down", "action": "SCROLL_DOWN", "color": QColor(39, 174, 96)},
            "left": {"label": "◀ Switch App", "action": "ALT_TAB", "color": QColor(142, 68, 173)},
            "right": {"label": "▶ Close Window", "action": "CLOSE_APP", "color": QColor(192, 57, 43)}
        }

        self._init_window_flags()

    def _init_window_flags(self):
        # Translucent, frameless, always-on-top window that does not steal focus
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        size = self.radius * 2 + 40
        self.resize(size, size)

    def set_dwell_progress(self, progress: float, quadrant: Optional[str]):
        """Updates the visual dwell ring progress [0.0 to 1.0]."""
        self.dwell_progress = max(0.0, min(1.0, progress))
        self.active_quadrant = quadrant
        self.update()

    def show_at(self, screen_x: int, screen_y: int):
        """Centers the HUD around target screen coordinates."""
        half = self.radius + 20
        self.move(screen_x - half, screen_y - half)
        self.show()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        center_x = self.width() / 2.0
        center_y = self.height() / 2.0
        center = QPoint(int(center_x), int(center_y))

        # Base semi-transparent background
        outer_rect = QRectF(center_x - self.radius, center_y - self.radius,
                            self.radius * 2, self.radius * 2)

        # Draw quadrants
        # Top: 45 to 135 deg (Qt angles are in 1/16th of a degree, 0 is at 3 o'clock)
        angles = {
            "right": (315, 90),
            "top": (45, 90),
            "left": (135, 90),
            "bottom": (225, 90)
        }

        for q_key, (start_deg, span_deg) in angles.items():
            info = self.quadrants[q_key]
            base_col = QColor(info["color"])
            if self.active_quadrant == q_key:
                base_col.setAlpha(int(240 * self.widget_opacity))
            else:
                base_col.setAlpha(int(140 * self.widget_opacity))

            painter.setBrush(QBrush(base_col))
            painter.setPen(QPen(QColor(255, 255, 255, 180), 2))
            painter.drawPie(outer_rect, start_deg * 16, span_deg * 16)

            # Draw label
            rad = math.radians(start_deg + span_deg / 2)
            label_x = center_x + (self.radius * 0.65) * math.cos(rad)
            label_y = center_y - (self.radius * 0.65) * math.sin(rad)

            painter.setPen(QColor(255, 255, 255, 250))
            painter.setFont(QFont("Arial", 11, QFont.Weight.Bold))
            text_rect = QRectF(label_x - 60, label_y - 15, 120, 30)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, info["label"])

        # Inner center circle (Dwell Click zone)
        inner_radius = self.radius * 0.35
        inner_rect = QRectF(center_x - inner_radius, center_y - inner_radius,
                            inner_radius * 2, inner_radius * 2)

        center_col = QColor(30, 30, 30, int(220 * self.widget_opacity))
        painter.setBrush(QBrush(center_col))
        painter.setPen(QPen(QColor(255, 255, 255, 200), 2))
        painter.drawEllipse(inner_rect)

        painter.setPen(QColor(255, 255, 255, 230))
        painter.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        painter.drawText(inner_rect, Qt.AlignmentFlag.AlignCenter, self.center_label)

        # Draw Animated Dwell Progress Ring if dwelling
        if self.dwell_progress > 0.0:
            ring_pen = QPen(QColor(241, 196, 15), 5)
            painter.setPen(ring_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            dwell_span = int(-self.dwell_progress * 360 * 16)
            painter.drawArc(inner_rect, 90 * 16, dwell_span)
