"""
Secure OS Action Dispatcher (Native Win32 + WinSta0 Desktop Attachment)
Guarantees physical mouse control on the interactive desktop:
- Attaches explicitly to WinSta0\\default desktop station.
- SetCursorPos & mouse_event for instantaneous, direct desktop cursor movement.
- Direct mouse click events (LEFTDOWN / LEFTUP).
"""

import time
import ctypes
from ctypes import wintypes
import winsound
import pyautogui
from config.schema import DispatcherConfig

user32 = ctypes.windll.user32
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.01

# Mouse Event Flags
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_WHEEL = 0x0800


# Virtual Key Codes
VK_MAP = {
    "shift": 0x10,
    "ctrl": 0x11,
    "alt": 0x12,
    "f8": 0x77,
    "caps_lock": 0x14
}


def is_hotkey_down(hotkey_name: str) -> bool:
    """Checks whether the specified clutch/engagement hotkey is physically pressed down."""
    vk = VK_MAP.get(hotkey_name.lower().strip(), 0x10)
    try:
        return (user32.GetAsyncKeyState(vk) & 0x8000) != 0
    except Exception:
        return False


def attach_to_interactive_desktop():
    """Attaches current thread to Windows interactive user desktop (WinSta0\\default)."""
    try:
        hwinsta = user32.OpenWindowStationW('WinSta0', False, 0x037F)
        if hwinsta:
            user32.SetProcessWindowStation(hwinsta)
        hdesk = user32.OpenDesktopW('default', 0, False, 0x01FF)
        if hdesk:
            user32.SetThreadDesktop(hdesk)
    except Exception:
        pass


class ActionDispatcher:
    def __init__(self, config: DispatcherConfig):
        self.config = config
        self.last_action_timestamp = 0.0
        self.min_action_interval = 1.0 / max(self.config.max_actions_per_second, 1)
        self.is_active = True

        attach_to_interactive_desktop()
        self.screen_width = max(100, user32.GetSystemMetrics(0))
        self.screen_height = max(100, user32.GetSystemMetrics(1))

    def set_active(self, active: bool):
        self.is_active = active

    def _can_dispatch(self) -> bool:
        if not self.is_active:
            return False
        now = time.monotonic()
        if now - self.last_action_timestamp >= self.min_action_interval:
            self.last_action_timestamp = now
            return True
        return False

    def move_cursor(self, screen_x: float, screen_y: float):
        """Moves cursor to screen coordinate clamped within desktop boundaries."""
        if not self.is_active:
            return
        try:
            clamped_x = int(max(2, min(self.screen_width - 3, screen_x)))
            clamped_y = int(max(2, min(self.screen_height - 3, screen_y)))

            # Direct native Win32 SetCursorPos (instantaneous, zero lag)
            user32.SetCursorPos(clamped_x, clamped_y)
        except Exception:
            pass

    def left_click(self):
        if self._can_dispatch():
            try:
                attach_to_interactive_desktop()
                user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            except Exception:
                pyautogui.click()

    def right_click(self):
        if self._can_dispatch():
            try:
                attach_to_interactive_desktop()
                user32.mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
                user32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
            except Exception:
                pyautogui.rightClick()

    def scroll_up(self):
        if self._can_dispatch():
            try:
                attach_to_interactive_desktop()
                user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, self.config.scroll_speed, 0)
            except Exception:
                pyautogui.scroll(self.config.scroll_speed)

    def scroll_down(self):
        if self._can_dispatch():
            try:
                attach_to_interactive_desktop()
                user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, -self.config.scroll_speed, 0)
            except Exception:
                pyautogui.scroll(-self.config.scroll_speed)

    def switch_app_forward(self):
        """Simulates Alt + Tab to switch to the next active application."""
        if self._can_dispatch():
            pyautogui.hotkey('alt', 'tab')

    def switch_app_backward(self):
        """Simulates Alt + Shift + Tab to switch to previous application."""
        if self._can_dispatch():
            pyautogui.hotkey('alt', 'shift', 'tab')

    def close_current_app(self):
        """Simulates Alt + F4 to close current window."""
        if self._can_dispatch():
            pyautogui.hotkey('alt', 'f4')

    def trigger_sos_alarm(self, freq: int = 900, duration_ms: int = 800):
        """Emits an audible emergency chime on local speaker."""
        try:
            winsound.Beep(freq, duration_ms)
            time.sleep(0.1)
            winsound.Beep(freq + 200, duration_ms)
        except Exception:
            print('\a')
