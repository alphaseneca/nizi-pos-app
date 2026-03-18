"""
NiziPOS Background Application — Entry Point

Starts:
  1. Flask web server (daemon thread) on port 9121
  2. System tray icon (main thread)

The tray icon provides connect/disconnect/open dashboard/quit controls.
Visit http://localhost:9121 for the full web dashboard.
"""

import logging
import os
import sys

# ── Logging ──────────────────────────────────────────────────────────────

from config import config

# Ensure log directory exists
log_file = config.config_dir / "app.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("nizipos")

# ── Resolve paths when running as frozen exe ─────────────────────────────

if getattr(sys, "frozen", False):
    # Running as PyInstaller bundle
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Ensure Flask can find the static folder
os.chdir(BASE_DIR)


def main():
    from web_server import start_server_thread, get_device_manager
    from tray_app import TrayApp

    logger.info("═" * 50)
    logger.info("  NiziPOS Background App starting …")
    logger.info("═" * 50)

    # Start web server in a background thread
    try:
        server_thread = start_server_thread()
        logger.info(f"Web server thread started → http://{config.server_host}:{config.server_port}")
    except Exception as e:
        logger.error(f"Failed to start web server: {e}")
        # On macOS bundle failure, we might want to alert the user or just keep the tray running

    # Get the shared device manager from the web server module
    device = get_device_manager()

    # Start auto-connect polling
    device.start_auto_connect()

    # Quit handler — called when user clicks "Quit" in system tray
    def on_quit():
        logger.info("Shutting down …")
        device.disconnect()
        os._exit(0)  # Ensure all threads are terminated immediately

    # Create the PyQt6 Application
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtGui import QIcon
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # Set global application icon
    icon_path = os.path.join(BASE_DIR, "icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # Create the floating PyQt UI
    from ui_app import TrayFlyout
    ui = TrayFlyout(device_manager=device, web_port=config.server_port, on_quit=on_quit)

    # Run system tray on the main thread
    tray = TrayApp(device_manager=device, ui_app=ui, on_quit=on_quit)
    
    # Run UI on main thread (required by Qt)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
