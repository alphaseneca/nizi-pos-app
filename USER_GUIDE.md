# NiziPOS User Guide

NiziPOS is a background service that allows web applications and local systems to communicate with the NiziPOS UART display device.

## Getting Started

### 1. Launching the App
Run the `NiziPOS` executable. On first launch, it will generate a secure API key stored in your user configuration folder.

### 2. System Tray
Look for the NiziPOS icon in your system tray:
- **Green Icon**: Device is connected.
- **Gray Icon**: Device is disconnected.

**Right-click the icon to:**
- **Show Menu**: Open the floating dashboard.
- **Connect Device**: Trigger auto-detection of the UART device.
- **Disconnect**: Safely disconnect the current device.
- **Quit NiziPOS**: Shut down the service.

---

## Using the Dashboard

The dashboard provides a quick way to interact with your device.

### Connection
You can enter a specific COM port (e.g., `COM3` on Windows or `/dev/ttyUSB0` on Linux) or leave it blank to let NiziPOS auto-detect the hardware.

### Display Controls
- **Status Screens**: Send pre-formatted Success, Waiting, or Error screens to the hardware.
- **QR Codes**: Display payment or information QR codes by pasting the payload.
- **Text Display**: Show custom titles, subtitles, and messages.
- **Image Upload**: Drag and drop a JPEG image to display it on the device. NiziPOS handles resizing and compression automatically.

### System Actions
- **IDLE/WAKE**: Put the display into low-power mode or wake it up.
- **RESET**: Reboot the device.
- **FORMAT**: Clear internal flash storage (use with caution).

---

## Remote Access & Integration

NiziPOS runs a local web server on `http://127.0.0.1:5123`.

- **Web Dashboard**: Open your browser to `http://localhost:5123` to access the full control panel.
- **API**: Third-party POS systems can send commands to the device using the REST API. See [API_DOCUMENTATION.md](./API_DOCUMENTATION.md) for details.

---

## Security
- NiziPOS is bound to **localhost only**. It cannot be accessed by other computers on your network.
- Every API request requires a valid **API Key** generated locally.
