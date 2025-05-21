# iSprinklr API Documentation

This document provides comprehensive documentation for all API endpoints in the iSprinklr system, including parameters, return values, and error responses.

## Table of Contents

1. [System Endpoints](#system-endpoints)
2. [Sprinkler Endpoints](#sprinkler-endpoints)
3. [Scheduler Endpoints](#scheduler-endpoints)
4. [Logs Endpoints](#logs-endpoints)
5. [ESP Controller API](#esp-controller-api)

---

## System Endpoints

Endpoints for checking system status and retrieving system information.

### Get System Status

Get the current system status including hardware connectivity, active zones, and ESP32 controller details.

**Endpoint**: `GET /api/system/status`

**Parameters**: None

**Returns**:
```json
{
  "systemStatus": "active",
  "message": null,
  "active_zone": 1,
  "duration": 300,
  "esp_status": {
    "status": "ok",
    "uptime_ms": 123456,
    "chip": {
      "model": "ESP32-S3",
      "revision": 1,
      "cores": 2
    },
    "memory": {
      "free_heap": 234567,
      "min_free_heap": 123456
    },
    "network": {
      "connected": true,
      "type": "Ethernet",
      "ip": "192.168.1.100",
      "mac": "A1:B2:C3:D4:E5:F6"
    },
    "reset_reason": "Power on",
    "idf_version": "4.4.1",
    "task": {
      "stack_hwm": 8192
    }
  }
}
```

**Possible Errors**:
- `500 Internal Server Error`: "Failed to get system status, see logs for details"

### Get Last Sprinkler Run

Get information about the last manually run zone.

**Endpoint**: `GET /api/system/last-sprinkler-run`

**Parameters**: None

**Returns**:
```json
{
  "zone": 1,
  "timestamp": 1706914800.123
}
```
or `null` if no zone has been run.

**Possible Errors**:
- `500 Internal Server Error`: "Failed to get last zone run status, see logs for details"

### Get Last Schedule Run

Get information about the last schedule that was run.

**Endpoint**: `GET /api/system/last-schedule-run`

**Parameters**: None

**Returns**:
```json
{
  "name": "Evening Schedule",
  "timestamp": 1706914800.123,
  "message": "Success"
}
```
or `null` if no schedule has been run.

**Possible Errors**:
- `500 Internal Server Error`: "Failed to get last schedule run status, see logs for details"

### Get API Configuration

Get the current API configuration settings.

**Endpoint**: `GET /api/system/config`

**Parameters**: None

**Returns**:
```json
{
  "ESP_controller_IP": "192.168.88.24",
  "domain": "127.0.0.1",
  "dummy_mode": true,
  "schedule_on_off": true,
  "log_level": "DEBUG",
  "USE_STRICT_CORS": false
}
```

**Possible Errors**:
- `500 Internal Server Error`: "Failed to get API configuration, see logs for details"

### Update API Configuration

Update the API configuration settings.

**Endpoint**: `PUT /api/system/config`

**Parameters**:
```json
{
  "ESP_controller_IP": "192.168.88.24",
  "domain": "127.0.0.1",
  "dummy_mode": true,
  "schedule_on_off": true,
  "log_level": "DEBUG",
  "USE_STRICT_CORS": false
}
```

**Field Validation**:
- `ESP_controller_IP`: Must be a valid IP address
- `domain`: Domain address for the API server
- `dummy_mode`: Boolean value (true/false)
- `schedule_on_off`: Boolean value (true/false)
- `log_level`: Must be one of: "DEBUG", "INFO", "WARNING", "WARN", "ERROR", "CRITICAL", "FATAL" (case insensitive, stored as uppercase)
- `USE_STRICT_CORS`: Boolean value (true/false)

**Returns**:
```json
{
  "ESP_controller_IP": "192.168.88.24",
  "domain": "127.0.0.1",
  "dummy_mode": true,
  "schedule_on_off": true,
  "log_level": "DEBUG",
  "USE_STRICT_CORS": false
}
```

**Important Note**:
Changes to certain configuration parameters (`domain` and `USE_STRICT_CORS`) will be saved to the configuration file but will not affect the running application until the API server is restarted. This is because these values are used to configure the CORS middleware during application startup.

**Possible Errors**:
- `400 Bad Request`: "Invalid configuration: [validation error details]"
- `500 Internal Server Error`: "Failed to update API configuration: [error details]"

---

## Sprinkler Endpoints

Endpoints for managing and controlling sprinkler zones.

### Get All Sprinklers

Get all configured sprinkler zones and their names.

**Endpoint**: `GET /api/sprinklers`

**Parameters**: None

**Returns**:
```json
[
  {
    "zone": 1,
    "name": "Front Lawn"
  },
  {
    "zone": 2,
    "name": "Back Lawn"
  },
  {
    "zone": 3,
    "name": "Garden"
  }
]
```

**Possible Errors**:
- `500 Internal Server Error`: "Failed to load sprinklers data, see logs for details"

### Update Sprinklers

Update the configuration of multiple sprinkler zones.

**Endpoint**: `PUT /api/sprinklers`

**Parameters**:
```json
[
  {
    "zone": 1,
    "name": "Front Lawn"
  },
  {
    "zone": 2,
    "name": "Back Lawn"
  },
  {
    "zone": 3,
    "name": "Garden"
  }
]
```

**Returns**:
```json
{
  "message": "Success",
  "zones": [
    {
      "zone": 1,
      "name": "Front Lawn"
    },
    {
      "zone": 2,
      "name": "Back Lawn"
    },
    {
      "zone": 3,
      "name": "Garden"
    }
  ]
}
```

**Possible Errors**:
- `400 Bad Request`: "Failed to update sprinklers, invalid data: Duplicate zone numbers"
- `500 Internal Server Error`: "Failed to update sprinklers, see logs for details"

### Start Sprinkler

Start a specific sprinkler zone for a given duration.

**Endpoint**: `POST /api/sprinklers/start`

**Parameters**:
```json
{
  "zone": 1,
  "duration": 300
}
```
- `zone` (int): Zone number to start
- `duration` (int): Duration in seconds

**Returns**:
```json
{
  "message": "Zone 1 started"
}
```

**Possible Errors**:
- `400 Bad Request`: "Zone 1 not found"
- `409 Conflict`: "Failed to start zone 2, system already active. Active zone: 1"
- `500 Internal Server Error`: "Unexpected error starting sprinkler: see logs for details"
- `503 Service Unavailable`: "Hardware communication error: Command Failed"

### Stop System

Stop all running sprinkler zones.

**Endpoint**: `POST /api/sprinklers/stop`

**Parameters**: None

**Returns**:
```json
{
  "message": "System stopped"
}
```

**Possible Errors**:
- `500 Internal Server Error`: "Failed to stop system, see logs for details"

---

## Scheduler Endpoints

Endpoints for managing sprinkler schedules.

### Get All Schedules

Get all available schedules.

**Endpoint**: `GET /api/scheduler/schedules`

**Parameters**: None

**Returns**:
```json
[
  {
    "schedule_name": "Evening Schedule",
    "schedule_items": [
      {
        "zone": 1,
        "day": "M",
        "duration": 300
      }
    ]
  }, 
  {
    "schedule_name": "Morning Schedule",
    "schedule_items": [
      {
        "zone": 2,
        "day": "T",
        "duration": 300
      }
    ]
  }
]
```

**Possible Errors**: None

### Get Specific Schedule

Get a specific schedule by name.

**Endpoint**: `GET /api/scheduler/schedule/{schedule_name}`

**Parameters**:
- `schedule_name` (string): Name of the schedule to retrieve

**Returns**:
```json
{
  "schedule_name": "Evening Schedule",
  "schedule_items": [
    {
      "zone": 1,
      "day": "M",
      "duration": 300
    }
  ]
}
```

**Possible Errors**:
- `404 Not Found`: "Schedule 'Evening Schedule' not found"

### Create Schedule

Create a new schedule.

**Endpoint**: `POST /api/scheduler/schedule`

**Parameters**:
```json
{
  "schedule_name": "New Schedule",
  "schedule_items": [
    {
      "zone": 1,
      "day": "M",
      "duration": 300
    }
  ]
}
```

**Returns**:
```json
{
  "message": "Success",
  "schedule": {
    "schedule_name": "New Schedule",
    "schedule_items": [
      {
        "zone": 1,
        "day": "M",
        "duration": 300
      }
    ]
  }
}
```

**Possible Errors**:
- `400 Bad Request`: "Invalid schedule data: Duplicate schedule name"
- `500 Internal Server Error`: "Internal server error"

### Update Schedule

Update an existing schedule.

**Endpoint**: `PUT /api/scheduler/schedule`

**Parameters**:
```json
{
  "schedule_name": "Updated Schedule",
  "schedule_items": [
    {
      "zone": 1,
      "day": "M",
      "duration": 300
    }
  ]
}
```

**Returns**:
```json
{
  "message": "Success",
  "schedule": {
    "schedule_name": "Updated Schedule",
    "schedule_items": [
      {
        "zone": 1,
        "day": "M",
        "duration": 300
      }
    ]
  }
}
```

**Possible Errors**:
- `400 Bad Request`: "Invalid schedule data"
- `500 Internal Server Error`: "Internal server error"

### Delete Schedule

Delete a schedule by name.

**Endpoint**: `DELETE /api/scheduler/schedule/{schedule_name}`

**Parameters**:
- `schedule_name` (string): Name of the schedule to delete

**Returns**:
```json
{
  "message": "Success"
}
```

**Possible Errors**:
- `404 Not Found`: "Schedule not found"
- `500 Internal Server Error`: "Internal server error"

### Get Active Schedule

Get the currently active schedule.

**Endpoint**: `GET /api/scheduler/active`

**Parameters**: None

**Returns**:
```json
{
  "schedule_name": "Evening Schedule",
  "schedule_items": [
    {
      "zone": 1,
      "day": "M",
      "duration": 300
    }
  ]
}
```

**Possible Errors**:
- `404 Not Found`: "No active schedule set"

### Set Active Schedule

Set the active schedule.

**Endpoint**: `PUT /api/scheduler/active/{schedule_name}`

**Parameters**:
- `schedule_name` (string): Name of the schedule to set as active

**Returns**:
```json
{
  "message": "Success",
  "active_schedule": {
    "schedule_name": "Evening Schedule",
    "schedule_items": [
      {
        "zone": 1,
        "day": "M",
        "duration": 300
      }
    ]
  }
}
```

**Possible Errors**:
- `404 Not Found`: "Schedule 'Evening Schedule' not found"
- `500 Internal Server Error`: "Internal server error"

### Get Schedule On/Off Status

Get whether the automated schedule is currently enabled or disabled.

**Endpoint**: `GET /api/scheduler/on_off`

**Parameters**: None

**Returns**:
```json
{
  "schedule_on_off": true
}
```

**Possible Errors**: None

### Update Schedule On/Off Status

Enable or disable the automated schedule.

**Endpoint**: `PUT /api/scheduler/on_off`

**Parameters**:
```json
{
  "schedule_on_off": true
}
```

**Returns**:
```json
{
  "schedule_on_off": true
}
```

**Possible Errors**:
- `500 Internal Server Error`: "Internal server error"

### Run Active Schedule

Run the active schedule immediately.

**Endpoint**: `POST /api/scheduler/active/run`

**Parameters**: None

**Returns**:
```json
{
  "message": "Started running active schedule",
  "zones": [
    {
      "zone": 1,
      "duration": 300
    }
  ]
}
```
or
```json
{
  "message": "No zones scheduled for today",
  "zones": []
}
```

**Possible Errors**:
- `404 Not Found`: "No active schedule set"
- `409 Conflict`: "System is already running zone 1"
- `500 Internal Server Error`: "Internal server error"

### Run Specific Schedule

Run a specific schedule immediately.

**Endpoint**: `POST /api/scheduler/schedule/{schedule_name}/run`

**Parameters**:
- `schedule_name` (string): Name of the schedule to run

**Returns**:
```json
{
  "message": "Started running schedule",
  "zones": [
    {
      "zone": 1,
      "duration": 300
    }
  ]
}
```
or
```json
{
  "message": "No zones scheduled for today",
  "zones": []
}
```

**Possible Errors**:
- `404 Not Found`: "Schedule not found"
- `409 Conflict`: "System is already running zone 1"
- `500 Internal Server Error`: "Internal server error"

---

## Logs Endpoints

Endpoints for accessing system logs.

### Get Logs

Retrieve and filter system logs.

**Endpoint**: `GET /api/logs`

**Parameters**:
- `module_name` (string, optional): Filter logs by module name (e.g., 'sprinkler_service')
- `debug_level` (string, optional): Filter logs by debug level (DEBUG, INFO, ERROR, etc.)
- `lines` (int, optional): Number of most recent log lines to return (1-200, default: 100)

**Returns**:
```json
[
  "2024-02-02 21:45:00 sprinkler_service INFO: Started zone 1"
]
```

**Possible Errors**:
- `400 Bad Request`: "Invalid number of lines"
- `404 Not Found`: "Log file not found"
- `500 Internal Server Error`: "An error occurred: Permission denied"

### Get Module List

Retrieve all unique module names from the system logs.

**Endpoint**: `GET /api/logs/module_list`

**Parameters**: None

**Returns**:
```json
[
  "sprinkler_service",
  "system_controller",
  "scheduler"
]
```

**Possible Errors**:
- `404 Not Found`: "Log file not found"
- `500 Internal Server Error`: "An error occurred: Permission denied"

---

## ESP Controller API

The ESP32 controller provides its own API endpoints. This section documents those endpoints.

### Base URL

All ESP controller API endpoints are relative to the base URL of your ESP32 device. For example: `http://192.168.1.100`

### Get ESP Status

Get the current status and system information of the ESP32 device.

**Endpoint**: `GET /api/status`

**Parameters**: None

**Returns**:
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

**Possible Errors**: None specified

### Start Zone (ESP Controller)

Start a sprinkler zone for a specified duration.

**Endpoint**: `POST /api/start`

**Parameters**:
```json
{
  "zone": 5,
  "minutes": 10
}
```
- `zone` (int): Integer between 1-20 representing the sprinkler zone
- `minutes` (int): Integer between 1-120 representing the duration in minutes

**Returns**:
```json
{
  "status": "started",
  "zone": 5,
  "minutes": 10
}
```

**Possible Errors**:
- `400 Bad Request` or `500 Internal Server Error`:
  ```json
  {
    "status": "error",
    "zone": 5,
    "minutes": 10,
    "error": "Error message"
  }
  ```

Possible error messages:
- Invalid JSON syntax
- Missing required parameters (zone or minutes)
- Invalid parameter types
- Zone out of range (must be 1-20)
- Minutes out of range (must be 1-120)
- Hardware communication error

### Stop Zone (ESP Controller)

Stop a currently running sprinkler zone.

**Endpoint**: `POST /api/stop`

**Parameters**:
```json
{
  "zone": 5
}
```
- `zone` (int): Integer between 1-20 representing the sprinkler zone to stop

**Returns**:
```json
{
  "status": "stopped",
  "zone": 5
}
```

**Possible Errors**:
- `400 Bad Request` or `500 Internal Server Error`:
  ```json
  {
    "status": "error",
    "zone": 5,
    "error": "Error message"
  }
  ```

Possible error messages:
- Invalid JSON syntax
- Missing required parameter (zone)
- Invalid parameter type
- Zone out of range (must be 1-20)
- Hardware communication error

---

## Data Schemas

### Schedule Schema

```json
{
  "schedule_name": "string",
  "schedule_items": [
    {
      "zone": "integer",
      "day": "string",
      "duration": "integer"
    }
  ]
}
```

- `schedule_name` (string): Name of the schedule
- `schedule_items` (array): List of schedule items
  - `zone` (integer): Zone number
  - `day` (string): Day abbreviation ("Su", "M", "Tu", "W", "Th", "F", "Sa")
  - `duration` (integer): Duration in seconds

### SprinklerCommand Schema

```json
{
  "zone": "integer",
  "duration": "integer"
}
```

- `zone` (integer): Zone number
- `duration` (integer): Duration in seconds

### SprinklerConfig Schema

```json
{
  "zone": "integer",
  "name": "string"
}
```

- `zone` (integer): Zone number
- `name` (string): Zone name
