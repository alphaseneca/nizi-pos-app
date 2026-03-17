# NiziPOS Build Guide

This guide explains how to compile the NiziPOS application into a standalone executable for Windows, macOS, and Linux.

## Prerequisites

1. **Python 3.10+**: Ensure Python is installed on your system.
2. **Virtual Environment**: It is highly recommended to use a virtual environment.
   ```bash
   python -m venv venv
   ```
3. **Activate Environment**:
   - **Windows**: `.\venv\Scripts\activate`
   - **Linux/macOS**: `source venv/bin/activate`
4. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

---

## Building Executables

PyInstaller does not support cross-compilation. You must run the build command on the specific operating system you want to target.

### Windows (PowerShell)
1. Ensure the `venv` is active.
2. Run the build command:
   ```powershell
   pyinstaller build.spec
   ```
3. The output `NiziPOS.exe` will be located in the `dist/` directory.

### Linux (Ubuntu/Debian)
1. Install system dependencies for tray and UI:
   ```bash
   sudo apt update
   sudo apt install binutils libappindicator3-1
   ```
2. Run the build command:
   ```bash
   pyinstaller build.spec
   ```
3. The binary `NiziPOS` will be located in the `dist/` directory.

### macOS
1. Run the build command:
   ```bash
   pyinstaller build.spec
   ```
2. The `NiziPOS.app` bundle will be located in the `dist/` directory.
   - *Note: For distribution, you should codesign and notarize the app using an Apple Developer account.*

---

## Troubleshooting

- **Missing Backend**: If the tray icon doesn't appear on Linux, ensure `libappindicator` is installed.
- **UPX**: If you have [UPX](https://upx.github.io/) installed and available in your PATH, PyInstaller will use it to compress the binaries automatically.
- **Hook Errors**: The `build.spec` is already configured with necessary hidden imports like `flask_socketio` and `pystray` OS-specific backends.
