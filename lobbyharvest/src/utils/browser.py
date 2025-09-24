"""Browser management utilities for headless systems"""
import atexit
import os
import subprocess
import time
from contextlib import contextmanager


class XvfbManager:
    """Manages Xvfb virtual display for headless browser automation"""

    def __init__(self, display_num: int = 99, resolution: str = "1920x1080x24"):
        self.display_num = display_num
        self.display = f":{display_num}"
        self.resolution = resolution
        self.xvfb_process = None

    def start(self):
        """Start Xvfb if not already running"""
        # Check if display is already in use
        try:
            result = subprocess.run(
                ["xdpyinfo", "-display", self.display],
                capture_output=True,
                timeout=1
            )
            if result.returncode == 0:
                print(f"Display {self.display} already in use")
                return
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        # Start Xvfb
        cmd = ["Xvfb", self.display, "-screen", "0", self.resolution]
        self.xvfb_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # Set DISPLAY environment variable
        os.environ["DISPLAY"] = self.display

        # Give Xvfb time to start
        time.sleep(1)

        # Register cleanup
        atexit.register(self.stop)

    def stop(self):
        """Stop Xvfb process"""
        if self.xvfb_process:
            self.xvfb_process.terminate()
            try:
                self.xvfb_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.xvfb_process.kill()
            self.xvfb_process = None

# Global Xvfb instance
_xvfb_manager = None

def ensure_display():
    """Ensure a display is available for browser automation"""
    global _xvfb_manager

    # Check if we already have a display
    if os.environ.get("DISPLAY"):
        return

    # Check if we're in a headless environment
    if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        if _xvfb_manager is None:
            _xvfb_manager = XvfbManager()
        _xvfb_manager.start()

@contextmanager
def virtual_display():
    """Context manager for running code with virtual display"""
    manager = XvfbManager()
    try:
        manager.start()
        yield
    finally:
        manager.stop()

def get_browser_args(headless: bool = True) -> dict:
    """Get optimized browser launch arguments"""
    args = {
        "headless": headless,
        "args": [
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--no-first-run",
            "--no-zygote",
            "--single-process",
            "--disable-features=IsolateOrigins",
            "--disable-site-isolation-trials"
        ]
    }

    # Ensure display for non-headless mode
    if not headless:
        ensure_display()

    return args