import requests
import logging
import json
import time

from isprinklr.paths import config_path

# Set up logging using the unified logging interface
logger = logging.getLogger(__name__)

# Read configuration from api.conf
with open(config_path + "/api.conf", "r") as f:
    config = json.load(f)
    ESP_CONTROLLER_IP = config.get("ESP_controller_IP", "")
    # DUMMY_MODE is a flag to indicate if the system is running in dummy mode (no ESP controller connected)
    DUMMY_MODE = config.get("dummy_mode", False) == "True"
    
    logger.debug(f"ESP Controller IP set to: {ESP_CONTROLLER_IP}")
    logger.debug(f"Dummy mode set to: {DUMMY_MODE}")

# Build base URL
BASE_URL = f"http://{ESP_CONTROLLER_IP}"

def test_awake():
    """Check if the ESP controller is responding.
    
    Returns:
        dict: Full status data from the ESP controller if connected in normal mode
              or a realistic mock response in dummy mode
        
    Raises:
        Exception: If ESP controller is not responding or connection error occurs
    """
    if DUMMY_MODE:
        # In dummy mode, return example values from documentation
        return {
            "status": "ok",
            "dummy_mode": True,
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
                "connected": True,
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
    
    try:
        # Try to get the status from the ESP controller
        url = f"{BASE_URL}/api/status"
        logger.debug(f"Checking ESP controller status: GET {url}")
        
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            status_data = response.json()
            logger.debug(f"ESP controller status: {status_data}")
            return status_data
        else:
            logger.error(f"ESP controller returned error status: {response.status_code}")
            raise Exception(f"I/O: ESP controller returned error status: {response.status_code}")
    except requests.exceptions.RequestException as exc:
        logger.error(f"Error connecting to ESP controller: {str(exc)}")
        raise Exception(f"I/O: ESP controller connection error: {str(exc)}")

def start_zone(zone, duration_minutes):
    """Start a sprinkler zone for a specified duration.
    
    Args:
        zone (int): Zone number (1-20)
        duration_minutes (int): Duration in minutes (1-120)
        
    Returns:
        bool: True if the command was successful
        
    Raises:
        IOError: If the command fails
    """
    if DUMMY_MODE:
        logger.debug(f"Dummy mode: Starting zone {zone} for {duration_minutes} minutes")
        # In dummy mode, log the action and return success
        return True
    
    try:
        url = f"{BASE_URL}/api/start"
        payload = {
            "zone": zone,
            "minutes": duration_minutes
        }
        
        logger.debug(f"Starting zone {zone} for {duration_minutes} minutes: POST {url} {payload}")
        
        response = requests.post(url, json=payload, timeout=5)
        
        if response.status_code == 200:
            try:
                data = response.json()
                logger.debug(f"Response: {data}")
                if data.get("status") == "started":
                    return True
                else:
                    logger.error(f"Unexpected response: {data}")
                    raise IOError(f"Command Failed: {data.get('error', 'Unexpected response')}")
            except ValueError as exc:
                logger.error(f"Invalid JSON response: {response.text}")
                raise IOError(f"Invalid response format: {str(exc)}")
        else:
            try:
                error_data = response.json() if response.text else {"error": f"HTTP {response.status_code}"}
                error_msg = error_data.get('error', f"HTTP {response.status_code}")
            except ValueError:
                error_msg = f"HTTP {response.status_code}: {response.text}"
            logger.error(f"Failed to start zone: {error_msg}")
            raise IOError(f"Command Failed: {error_msg}")
    except requests.exceptions.RequestException as exc:
        logger.error(f"Error connecting to ESP controller: {str(exc)}")
        raise IOError(f"Communication Error: {str(exc)}")

def stop_zone(zone):
    """Stop a sprinkler zone.
    
    Args:
        zone (int): Zone number (1-20)
        
    Returns:
        bool: True if the command was successful
        
    Raises:
        IOError: If the command fails
    """
    if DUMMY_MODE:
        logger.debug(f"Dummy mode: Stopping zone {zone}")
        # In dummy mode, log the action and return success
        return True
    
    try:
        url = f"{BASE_URL}/api/stop"
        payload = {
            "zone": zone
        }
        
        logger.debug(f"Stopping zone {zone}: POST {url} {payload}")
        
        response = requests.post(url, json=payload, timeout=5)
        
        if response.status_code == 200:
            try:
                data = response.json()
                logger.debug(f"Response: {data}")
                if data.get("status") == "stopped":
                    return True
                else:
                    logger.error(f"Unexpected response: {data}")
                    raise IOError(f"Command Failed: {data.get('error', 'Unexpected response')}")
            except ValueError as exc:
                logger.error(f"Invalid JSON response: {response.text}")
                raise IOError(f"Invalid response format: {str(exc)}")
        else:
            try:
                error_data = response.json() if response.text else {"error": f"HTTP {response.status_code}"}
                error_msg = error_data.get('error', f"HTTP {response.status_code}")
            except ValueError:
                error_msg = f"HTTP {response.status_code}: {response.text}"
            logger.error(f"Failed to stop zone: {error_msg}")
            raise IOError(f"Command Failed: {error_msg}")
    except requests.exceptions.RequestException as exc:
        logger.error(f"Error connecting to ESP controller: {str(exc)}")
        raise IOError(f"Communication Error: {str(exc)}")
