"""
AuraAccess Launcher
Starts the secure, local-first FastAPI server on 127.0.0.1:8000
and opens the Web Dashboard in your default web browser.
100% Offline & Air-Gapped.
"""

import os
import sys
import tempfile
import webbrowser
import threading
import time
from pathlib import Path

# Set environment
os.environ["MPLCONFIGDIR"] = tempfile.gettempdir()
sys.path.insert(0, str(Path(__file__).resolve().parent))

import uvicorn


def open_browser():
    time.sleep(1.2)
    url = "http://127.0.0.1:8000"
    print(f"\n[Browser] Opening AuraAccess Dashboard at: {url}")
    webbrowser.open(url)


def main():
    print("=" * 65)
    print("  AuraAccess — Zero-Cloud Hands-Free Accessibility System")
    print("  Bound strictly to: http://127.0.0.1:8000 (Localhost only)")
    print("  Privacy: 100% On-Device & Air-Gapped")
    print("=" * 65)

    # Launch browser automatically in background thread
    threading.Thread(target=open_browser, daemon=True).start()

    # Run FastAPI server
    from server.api import app
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")


if __name__ == "__main__":
    main()
