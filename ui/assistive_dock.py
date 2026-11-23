"""
Assistive Floating Desktop Dock (Always-On-Top)
A translucent, frameless toolbar that floats over all Windows applications:
- 🚀 Apps Launcher (Opens Chrome, YouTube, Notepad, Files, Calculator)
- 🪟 Switch App (Alt + Tab slide)
- 📜 Scroll Mode (Hands-free page scrolling)
- ⌨️ On-Screen Keyboard (Windows OSK launcher for typing)
- ❌ Close App (Alt + F4)
- ⏸️ Pause / Resume Cursor Tracking
Supports Dwell-Time Clicking (hovering over any button for 1.0s triggers it).
"""

import sys
import os
import subprocess
import time
import webbrowser
import threading
import tkinter as tk
from tkinter import ttk
import pyautogui

# API client to sync tracking status with background service
import urllib.request
import json


class AssistiveDock:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("AuraAccess Dock")

        # Window properties: Always on top, frameless, semi-transparent
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.92)
        self.root.overrideredirect(True)

        self.screen_w = self.root.winfo_screenwidth()
        self.screen_h = self.root.winfo_screenheight()

        # Position at top center of the screen
        dock_w = 780
        dock_h = 56
        pos_x = (self.screen_w - dock_w) // 2
        pos_y = 12
        self.root.geometry(f"{dock_w}x{dock_h}+{pos_x}+{pos_y}")
        self.root.configure(bg="#0f172a")

        # State
        self.is_tracking_active = True
        self.app_drawer_open = False
        self.drawer_window = None

        # Dwell hover state
        self.hovered_btn = None
        self.hover_start_time = 0
        self.dwell_timer_id = None
        self.dwell_duration_ms = 950  # 0.95 second hover triggers action

        self._build_ui()
        self._sync_tracking_state(True)

    def _build_ui(self):
        main_frame = tk.Frame(self.root, bg="#0f172a", bd=1, relief="solid")
        main_frame.pack(fill="both", expand=True, padx=2, pady=2)

        # Brand pill
        brand_label = tk.Label(
            main_frame,
            text=" ✦ Aura ",
            font=("Segoe UI", 10, "bold"),
            fg="#38bdf8",
            bg="#1e293b",
            padx=8,
            pady=4
        )
        brand_label.pack(side="left", padx=(6, 8))

        # Buttons configuration
        buttons = [
            ("🚀 Apps", self.toggle_app_drawer, "#4f46e5"),
            ("🪟 Switch App", self.switch_app, "#334155"),
            ("▲ Scroll Up", self.scroll_up, "#334155"),
            ("▼ Scroll Down", self.scroll_down, "#334155"),
            ("⌨️ Keyboard", self.open_keyboard, "#334155"),
            ("❌ Close", self.close_active_app, "#991b1b"),
        ]

        for text, cmd, bg_col in buttons:
            btn = tk.Button(
                main_frame,
                text=text,
                font=("Segoe UI", 9, "bold"),
                fg="#ffffff",
                bg=bg_col,
                activebackground="#6366f1",
                activeforeground="#ffffff",
                bd=0,
                padx=12,
                pady=6,
                cursor="hand2",
                command=cmd
            )
            btn.pack(side="left", padx=4)
            self._attach_dwell(btn, cmd)

        # Pause / Resume Tracking Toggle
        self.btn_pause = tk.Button(
            main_frame,
            text="🟢 Active",
            font=("Segoe UI", 9, "bold"),
            fg="#10b981",
            bg="#064e3b",
            activebackground="#059669",
            bd=0,
            padx=12,
            pady=6,
            command=self.toggle_tracking
        )
        self.btn_pause.pack(side="right", padx=(4, 8))
        self._attach_dwell(self.btn_pause, self.toggle_tracking)

    def _attach_dwell(self, widget, action):
        """Attaches hands-free hover dwell detection."""
        def on_enter(event):
            widget.configure(relief="sunken")
            self.hovered_btn = widget
            # Start dwell countdown
            self.dwell_timer_id = self.root.after(self.dwell_duration_ms, lambda: self._execute_dwell(action, widget))

        def on_leave(event):
            widget.configure(relief="flat")
            if self.dwell_timer_id is not None:
                self.root.after_cancel(self.dwell_timer_id)
                self.dwell_timer_id = None
            self.hovered_btn = None

        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)

    def _execute_dwell(self, action, widget):
        widget.configure(bg="#22c55e")  # Flash green confirmation
        self.root.after(150, lambda: self._reset_btn_color(widget))
        action()

    def _reset_btn_color(self, widget):
        if widget == self.btn_pause:
            return
        widget.configure(bg="#334155")

    # Actions
    def switch_app(self):
        """Slides to the next application (Alt+Tab)."""
        pyautogui.hotkey('alt', 'tab')

    def scroll_up(self):
        pyautogui.scroll(250)

    def scroll_down(self):
        pyautogui.scroll(-250)

    def close_active_app(self):
        pyautogui.hotkey('alt', 'f4')

    def open_keyboard(self):
        """Launches the Windows native On-Screen Keyboard."""
        try:
            subprocess.Popen("osk.exe", shell=True)
        except Exception as e:
            print("Failed to launch OSK:", e)

    def toggle_tracking(self):
        self.is_tracking_active = not self.is_tracking_active
        self._sync_tracking_state(self.is_tracking_active)
        if self.is_tracking_active:
            self.btn_pause.configure(text="🟢 Active", fg="#10b981", bg="#064e3b")
        else:
            self.btn_pause.configure(text="⏸️ Paused", fg="#f59e0b", bg="#78350f")

    def _sync_tracking_state(self, active: bool):
        def _call():
            try:
                req = urllib.request.Request(
                    "http://127.0.0.1:8000/api/tracking/toggle",
                    data=json.dumps({"enabled": active}).encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )
                urllib.request.urlopen(req, timeout=1.0)
            except Exception:
                pass
        threading.Thread(target=_call, daemon=True).start()

    def toggle_app_drawer(self):
        """Opens or closes the large-tile App Launcher Grid."""
        if self.app_drawer_open:
            if self.drawer_window:
                self.drawer_window.destroy()
            self.app_drawer_open = False
            return

        self.drawer_window = tk.Toplevel(self.root)
        self.drawer_window.title("Apps")
        self.drawer_window.attributes("-topmost", True)
        self.drawer_window.attributes("-alpha", 0.95)
        self.drawer_window.overrideredirect(True)

        w = 480
        h = 240
        x = (self.screen_w - w) // 2
        y = 76
        self.drawer_window.geometry(f"{w}x{h}+{x}+{y}")
        self.drawer_window.configure(bg="#0f172a")

        container = tk.Frame(self.drawer_window, bg="#1e293b", bd=2, relief="solid")
        container.pack(fill="both", expand=True, padx=4, pady=4)

        header = tk.Label(container, text="Select Application (Dwell to Open)", font=("Segoe UI", 10, "bold"), fg="#94a3b8", bg="#1e293b")
        header.pack(pady=(8, 12))

        grid_frame = tk.Frame(container, bg="#1e293b")
        grid_frame.pack()

        apps = [
            ("🌐 Google Chrome", lambda: self._launch_app("chrome", "https://google.com")),
            ("🎬 YouTube", lambda: self._launch_app("browser", "https://youtube.com")),
            ("📝 Notepad", lambda: subprocess.Popen("notepad.exe")),
            ("📁 File Explorer", lambda: subprocess.Popen("explorer.exe")),
            ("🧮 Calculator", lambda: subprocess.Popen("calc.exe")),
            ("⚙️ Settings", lambda: subprocess.Popen("start ms-settings:", shell=True))
        ]

        for i, (name, action) in enumerate(apps):
            r = i // 2
            c = i % 2
            btn = tk.Button(
                grid_frame,
                text=name,
                font=("Segoe UI", 10, "bold"),
                fg="#ffffff",
                bg="#334155",
                activebackground="#4f46e5",
                bd=0,
                width=18,
                pady=10,
                command=lambda a=action: self._run_and_close_drawer(a)
            )
            btn.grid(row=r, column=c, padx=8, pady=6)
            self._attach_dwell(btn, lambda a=action: self._run_and_close_drawer(a))

        self.app_drawer_open = True

    def _launch_app(self, app_type: str, url: str = ""):
        if app_type == "chrome":
            try:
                subprocess.Popen(f"start chrome {url}", shell=True)
            except Exception:
                webbrowser.open(url)
        else:
            webbrowser.open(url)

    def _run_and_close_drawer(self, action):
        action()
        if self.drawer_window:
            self.drawer_window.destroy()
        self.app_drawer_open = False


def launch_dock():
    dock = AssistiveDock()
    dock.root.mainloop()


if __name__ == "__main__":
    launch_dock()
