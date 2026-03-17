# NiziPOS API Documentation

The NiziPOS background service exposes a REST API on `http://127.0.0.1:5123` for controlling the connected UART display device.

## Authentication

All `/api/*` requests (except `/api/auth-token`) require an API Key supplied in the `X-API-Key` header.

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

## Error Handling

| Status Code | Description |
| :--- | :--- |
| `200` | OK. Operation completed or data returned. |
| `400` | Bad Request. Missing parameters or invalid data. |
| `401` | Unauthorized. Missing or invalid `X-API-Key`. |
| `403` | Forbidden. Attempted access from non-localhost IP. |
