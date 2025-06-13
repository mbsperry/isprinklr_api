# iSprinklr ESP API Documentation

This document provides details on the REST API endpoints available in the iSprinklr ESP controller. These endpoints allow controlling a Hunter Pro-c sprinkler system via HTTP requests.

## Base URL

All API endpoints are relative to the base URL of your ESP32 device. For example, if your device has the IP address `192.168.1.100`, the base URL would be:

```
http://192.168.1.100
```

## API Endpoints

### Status Check

Get the current status and system information of the device.

**Endpoint**: `/api/status`

**Method**: GET

**Response**:
```json
{
  "status": "ok",
  "uptime_ms": 123456,
  "chip": {
    "model": "ESP32-S3",
    "revision": 1,
    "cores": 2
  },
  "idf_version": "4.4.1",
  "reset_reason": "Power on",
  "memory": {
    "free_heap": 234567,
    "min_free_heap": 123456
  },
  "network": {
    "connected": true,
    "type": "Ethernet",
    "ip": "192.168.1.100",
    "mac": "A1:B2:C3:D4:E5:F6",
    "gateway": "192.168.1.1",
    "subnet": "255.255.255.0",
    "speed": "100 Mbps",
    "duplex": "Full"
  },
  "task": {
    "stack_hwm": 8192
  }
}
```

**Notes**:
- `uptime_ms` provides the system uptime in milliseconds
- `chip` contains information about the ESP32 chip model, revision, and number of cores
- `network` information varies depending on connection type (Ethernet or WiFi)
- For WiFi connections, additional fields like `ssid` and `rssi` are included

### Start Zone

Start a sprinkler zone for a specified duration.

**Endpoint**: `/api/start`

**Method**: POST

**Request Body**:
```json
{
  "zone": 5,
  "minutes": 10
}
```

**Parameters**:
- `zone` (required): Integer between 1-20 representing the sprinkler zone
- `minutes` (required): Integer between 1-120 representing the duration in minutes

**Success Response** (HTTP 200):
```json
{
  "status": "started",
  "zone": 5,
  "minutes": 10
}
```

**Error Response** (HTTP 400 or 500):
```json
{
  "status": "error",
  "zone": 5,
  "minutes": 10,
  "error": "Error message"
}
```

**Possible Errors**:
- Invalid JSON syntax
- Missing required parameters (zone or minutes)
- Invalid parameter types
- Zone out of range (must be 1-20)
- Minutes out of range (must be 1-120)
- Hardware communication error

### Stop Zone

Stop a currently running sprinkler zone.

**Endpoint**: `/api/stop`

**Method**: POST

**Request Body**:
```json
{
  "zone": 5
}
```

**Parameters**:
- `zone` (required): Integer between 1-20 representing the sprinkler zone to stop

**Success Response** (HTTP 200):
```json
{
  "status": "stopped",
  "zone": 5
}
```

**Error Response** (HTTP 400 or 500):
```json
{
  "status": "error",
  "zone": 5,
  "error": "Error message"
}
```

**Possible Errors**:
- Invalid JSON syntax
- Missing required parameter (zone)
- Invalid parameter type
- Zone out of range (must be 1-20)
- Hardware communication error

## Example Usage

### cURL Examples

#### Get System Status
```bash
curl -X GET http://192.168.1.100/api/status
```

#### Start a Zone
```bash
curl -X POST \
  http://192.168.1.100/api/start \
  -H 'Content-Type: application/json' \
  -d '{"zone": 5, "minutes": 10}'
```

#### Stop a Zone
```bash
curl -X POST \
  http://192.168.1.100/api/stop \
  -H 'Content-Type: application/json' \
  -d '{"zone": 5}'
```

### JavaScript Examples

#### Get System Status
```javascript
fetch('http://192.168.1.100/api/status')
  .then(response => response.json())
  .then(data => console.log(data))
  .catch(error => console.error('Error:', error));
```

#### Start a Zone
```javascript
fetch('http://192.168.1.100/api/start', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    zone: 5,
    minutes: 10
  }),
})
.then(response => response.json())
.then(data => console.log(data))
.catch(error => console.error('Error:', error));
```

#### Stop a Zone
```javascript
fetch('http://192.168.1.100/api/stop', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    zone: 5
  }),
})
.then(response => response.json())
.then(data => console.log(data))
.catch(error => console.error('Error:', error));
```

### Python Examples

#### Get System Status
```python
import requests

response = requests.get('http://192.168.1.100/api/status')
data = response.json()
print(data)
```

#### Start a Zone
```python
import requests

payload = {
    "zone": 5,
    "minutes": 10
}
response = requests.post('http://192.168.1.100/api/start', json=payload)
data = response.json()
print(data)
```

#### Stop a Zone
```python
import requests

payload = {
    "zone": 5
}
response = requests.post('http://192.168.1.100/api/stop', json=payload)
data = response.json()
print(data)
```

## Error Handling

The API returns appropriate HTTP status codes along with JSON responses:

- 200 OK: Request was successful
- 400 Bad Request: Client error (invalid input)
- 500 Internal Server Error: Server-side error

Error responses include a descriptive error message in the `error` field to help with debugging.
