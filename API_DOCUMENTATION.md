# NiziPOS API Documentation

The NiziPOS background service exposes a REST API on `http://127.0.0.1:5123` for controlling the connected UART display device.

## Authentication

All `/api/*` requests require an API Key supplied in the `X-API-Key` header.

### How to get your API Key
1. Open the **NiziPOS Tray Application**.
2. Click the **API Settings** button at the bottom.
3. Enter the verification code (`adminhere`).
4. Copy the API Token to your clipboard.

| Header | Description |
| :--- | :--- |
| `X-API-Key` | Your secure API token. |

---

## Endpoints

### 1. Connection Status
**`GET /api/status`**  
Returns the current connection state.

**Response (JSON):**
```json
{
  "connected": true,
  "port": "COM15"
}
```

---

### 2. Connect Device
**`POST /api/connect`**  
Triggers a connection attempt.

**Body (JSON):**
```json
{
  "port": "COM3"
}
```
*Note: Set `"port": null` for auto-detect.*

**Response (JSON):**
```json
{
  "success": true,
  "port": "COM3",
  "error": null
}
```

---

### 3. Disconnect Device
**`POST /api/disconnect`**  
Safely closes the serial connection.

---

### 4. Send Command
**`POST /api/command`**  
Sends a raw command string to the device.

**Body (JSON):**
```json
{
  "command": "IDLE"
}
```

---

### 5. Update Settings
**`POST /api/settings`**  
Updates device parameters.

**Body (JSON):**
```json
{
  "volume": 80,
  "brightness": 100,
  "screentime": 300
}
```

---

### 6. Upload Image
**`POST /api/upload-image`**  
Uploads and displays a JPEG image.

**Form Data:**
- `image`: Binary JPEG file.
- `size`: (Optional) Target size, e.g., `"320x480"`.

---

## WebSocket (Socket.IO) Communication

The background service uses Socket.IO for real-time status updates and command feedback.

**Connection URL:** `ws://127.0.0.1:5123` or `http://127.0.0.1:5123`

### Client-to-Server Events

#### `send_command`
Sends a raw command to the device (alternative to the POST `/api/command` endpoint).

**Payload:**
```json
{
  "command": "IDLE"
}
```

### Server-to-Client Events

#### `device_status`
Emitted immediately upon connection and whenever the device connection state changes.

**Payload:**
```json
{
  "connected": true,
  "port": "COM15"
}
```

#### `command_result`
Emitted after a command sent via `send_command` is processed.

**Payload:**
```json
{
  "command": "IDLE",
  "success": true,
  "error": null
}
```

---

## Error Handling

| Status Code | Description |
| :--- | :--- |
| `200` | OK. Operation completed or data returned. |
| `400` | Bad Request. Missing parameters or invalid data. |
| `401` | Unauthorized. Missing or invalid `X-API-Key`. |
| `403` | Forbidden. Attempted access from non-localhost IP. |
