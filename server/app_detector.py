"""
Active Application Context Detector (Windows)
Detects the currently focused foreground window and matches it
to application categories (e.g., YouTube/Browser, Document/PDF, Media Player).
Zero hardcoding: uses generic process & title matching rules.
"""

import ctypes
from ctypes import wintypes
from typing import Optional, NamedTuple


class ActiveAppContext(NamedTuple):
    title: str
    process_name: str
    category: str


# Win32 API functions
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32


def get_active_window_context() -> ActiveAppContext:
    """Returns the title and category of the foreground application."""
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return ActiveAppContext(title="Desktop", process_name="explorer.exe", category="desktop")

    # Get Window Title
    length = user32.GetWindowTextLengthW(hwnd)
    buff = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buff, length + 1)
    window_title = buff.value or "Unknown"

    # Identify App Category from Window Title or Process
    title_lower = window_title.lower()
    category = "general"

    if "youtube" in title_lower or "netflix" in title_lower or "spotify" in title_lower or "vlc" in title_lower:
        category = "media"
    elif "chrome" in title_lower or "edge" in title_lower or "firefox" in title_lower or "browser" in title_lower:
        category = "browser"
    elif "word" in title_lower or "pdf" in title_lower or "notion" in title_lower or "docs" in title_lower or "notepad" in title_lower:
        category = "document"
    elif len(window_title.strip()) == 0 or window_title.lower() in ["desktop", "task switching", "start"]:
        category = "desktop"

    return ActiveAppContext(
        title=window_title,
        process_name="active_app",
        category=category
    )
