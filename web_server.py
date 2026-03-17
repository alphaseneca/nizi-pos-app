"""
NiziPOS Web Server
Flask + Flask-SocketIO web server exposing REST API and real-time events
for controlling the NiziPOS UART display device.
"""

import logging
import os
import threading
import io
from PIL import Image

from flask import Flask, jsonify, request, send_from_directory
from flask_socketio import SocketIO

from device_manager import DeviceManager

logger = logging.getLogger(__name__)

# ── Globals ──────────────────────────────────────────────────────────────

app = Flask(__name__, static_folder="static", static_url_path="/static")
app.config["SECRET_KEY"] = "nizipos-secret-key"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

device = DeviceManager()


def _on_device_status(connected: bool, port: str | None):
    """Push connection status to all connected browser clients."""
    socketio.emit("device_status", {"connected": connected, "port": port})


device.set_status_callback(_on_device_status)

# ── Static / UI ──────────────────────────────────────────────────────────


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


# ── REST API ─────────────────────────────────────────────────────────────


@app.route("/api/status")
def api_status():
    return jsonify({"connected": device.connected, "port": device.port})


@app.route("/api/connect", methods=["POST"])
def api_connect():
    data = request.get_json(silent=True) or {}
    port = data.get("port")  # None means auto-detect
    result = device.connect(port)
    return jsonify(result)


@app.route("/api/disconnect", methods=["POST"])
def api_disconnect():
    result = device.disconnect()
    return jsonify(result)


@app.route("/api/command", methods=["POST"])
def api_command():
    data = request.get_json(silent=True) or {}
    command = data.get("command", "")
    if not command:
        return jsonify({"success": False, "error": "No command provided."}), 400
    result = device.send_command(command)
    return jsonify(result)


@app.route("/api/upload-image", methods=["POST"])
def api_upload_image():
    if "image" not in request.files:
        return jsonify({"success": False, "error": "No image file provided."}), 400
    file = request.files["image"]
    raw_data = file.read()
    if not raw_data:
        return jsonify({"success": False, "error": "Empty image file."}), 400

    try:
        # Load the image using Pillow
        img = Image.open(io.BytesIO(raw_data))
        
        # Convert to RGB (to ensure JPEG compatibility, discarding alpha layer if any)
        if img.mode != "RGB":
            img = img.convert("RGB")
            
        # Resize to requested dimensions explicitly
        size_str = request.form.get("size", "320x480")
        try:
            width, height = map(int, size_str.split("x"))
        except ValueError:
            width, height = 320, 480
            
        img = img.resize((width, height), Image.Resampling.LANCZOS)
        
        # Ensure it is under 30KB using a quality reduction loop
        max_size = 30 * 1024
        quality = 95
        jpeg_data = b""
        
        while quality > 5:
            output = io.BytesIO()
            # baseline is default, optimize=False ensures it's as standard as possible
            img.save(output, format="JPEG", quality=quality, optimize=False)
            jpeg_data = output.getvalue()
            
            if len(jpeg_data) <= max_size:
                break
                
            quality -= 5
            
        if len(jpeg_data) > max_size:
            logger.warning(f"Could not compress image under 30KB (size: {len(jpeg_data)} bytes)")

        logger.info(f"Image processed: {len(jpeg_data)} bytes at quality={quality}")

    except Exception as e:
        logger.error(f"Image processing error: {e}")
        return jsonify({"success": False, "error": f"Invalid image format or processing failed: {e}"}), 400

    result = device.upload_image(jpeg_data)
    return jsonify(result)


@app.route("/api/settings", methods=["POST"])
def api_settings():
    data = request.get_json(silent=True) or {}
    results = {}

    if "volume" in data:
        results["volume"] = device.set_volume(int(data["volume"]))
    if "brightness" in data:
        results["brightness"] = device.set_brightness(int(data["brightness"]))
    if "screentime" in data:
        results["screentime"] = device.set_screentime(int(data["screentime"]))

    if not results:
        return jsonify({"success": False, "error": "No settings provided."}), 400
    return jsonify({"success": True, "results": results})


# ── SocketIO events ──────────────────────────────────────────────────────


@socketio.on("connect")
def ws_connect():
    socketio.emit(
        "device_status",
        {"connected": device.connected, "port": device.port},
    )


@socketio.on("send_command")
def ws_send_command(data):
    command = data.get("command", "")
    result = device.send_command(command)
    socketio.emit("command_result", {"command": command, **result})


# ── Server lifecycle ────────────────────────────────────────────────────


def start_server(host="0.0.0.0", port=5123):
    """Start the web server (blocking). Call from a thread."""
    logger.info(f"Starting web server on {host}:{port}")
    socketio.run(app, host=host, port=port, allow_unsafe_werkzeug=True, use_reloader=False)


def start_server_thread(host="0.0.0.0", port=5123) -> threading.Thread:
    """Start the web server in a daemon thread and return the thread."""
    t = threading.Thread(target=start_server, args=(host, port), daemon=True)
    t.start()
    return t


def get_device_manager() -> DeviceManager:
    """Return the singleton DeviceManager instance."""
    return device
