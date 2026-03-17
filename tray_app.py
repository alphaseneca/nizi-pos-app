"""
NiziPOS System Tray Application
Provides a system tray icon with connect/disconnect/open dashboard/quit options.
Icon color changes based on device connection state.
"""

import logging
import threading
import webbrowser

from PIL import Image, ImageDraw
import pystray

logger = logging.getLogger(__name__)

WEB_PORT = 5123
ICON_SIZE = 64


def _create_icon_image(connected: bool) -> Image.Image:
    """Generate a simple colored icon: green if connected, gray if not."""
    img = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Background circle
    bg_color = (16, 185, 129, 255) if connected else (100, 116, 139, 255)
    draw.ellipse([4, 4, ICON_SIZE - 4, ICON_SIZE - 4], fill=bg_color)

    # Inner "N" letter approximation using lines
    inner_color = (255, 255, 255, 255)
    m = 18  # margin
    # N shape: left bar, diagonal, right bar
    draw.line([(m, ICON_SIZE - m), (m, m)], fill=inner_color, width=4)
    draw.line([(m, m), (ICON_SIZE - m, ICON_SIZE - m)], fill=inner_color, width=4)
    draw.line([(ICON_SIZE - m, ICON_SIZE - m), (ICON_SIZE - m, m)], fill=inner_color, width=4)

    return img


class TrayApp:
    """System tray application for NiziPOS background service."""

    def __init__(self, device_manager, ui_app=None, on_quit=None):
        self._device = device_manager
        self._ui_app = ui_app
        self._on_quit = on_quit
        self._icon: pystray.Icon | None = None
        self._connected = device_manager.connected

        # Listen for device status changes
        original_callback = device_manager._on_status_change

        def _status_wrapper(connected, port):
            self._connected = connected
            self._update_icon()
            if original_callback:
                original_callback(connected, port)

        device_manager.set_status_callback(_status_wrapper)

    def _update_icon(self):
        """Update the tray icon image to reflect connection state."""
        if self._icon:
            self._icon.icon = _create_icon_image(self._connected)
            tip = "NiziPOS — Connected" if self._connected else "NiziPOS — Disconnected"
            self._icon.title = tip

    def _on_connect(self, icon, item):
        """Menu: Connect device (auto-detect)."""
        def _do():
            result = self._device.connect()
            if result["success"]:
                logger.info(f"Tray: connected on {result['port']}")
            else:
                logger.warning(f"Tray: connect failed — {result['error']}")
        threading.Thread(target=_do, daemon=True).start()

    def _on_disconnect(self, icon, item):
        """Menu: Disconnect device."""
        self._device.disconnect()

    def _on_toggle_ui(self, icon, item):
        """Menu: Show the native popup UI."""
        if self._ui_app:
            self._ui_app.toggle()

    def _on_exit(self, icon, item):
        """Menu: Quit the application."""
        logger.info("Tray: quit requested")
        self._device.disconnect()
        icon.stop()
        if self._on_quit:
            self._on_quit()

    def _build_menu(self):
        return pystray.Menu(
            pystray.MenuItem("Show Menu", self._on_toggle_ui, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Connect Device", self._on_connect),
            pystray.MenuItem("Disconnect", self._on_disconnect),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit NiziPOS", self._on_exit),
        )

    def run(self):
        """
        Run the system tray icon (blocking — must be called on the main
        thread on Windows).
        """
        self._icon = pystray.Icon(
            name="NiziPOS",
            icon=_create_icon_image(self._connected),
            title="NiziPOS — Connected" if self._connected else "NiziPOS — Disconnected",
            menu=self._build_menu(),
        )
        logger.info("System tray started")
        self._icon.run()

    def stop(self):
        """Stop the tray icon programmatically."""
        if self._icon:
            self._icon.stop()
