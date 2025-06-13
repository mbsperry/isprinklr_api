import requests
import logging
import json
import time
import os 

from isprinklr.paths import config_path

# Set up logging using the unified logging interface
logger = logging.getLogger(__name__)

DEFAULT_ESP_CONTROLLER_IP = ""

ESP_CONTROLLER_IP = DEFAULT_ESP_CONTROLLER_IP
DUMMY_MODE = True # Initial safe default

try:
    api_conf_path = os.path.join(config_path, "api.conf")
    # main.py attempts to create a default api.conf. This handles reading it.
    with open(api_conf_path, "r") as f:
        config = json.load(f)
        
        ESP_CONTROLLER_IP = config.get("ESP_controller_IP", DEFAULT_ESP_CONTROLLER_IP)
        
        raw_dummy_mode = config.get("dummy_mode") 

        if raw_dummy_mode is not None:
            if isinstance(raw_dummy_mode, bool):
                DUMMY_MODE = raw_dummy_mode
            else: # Attempt to parse from string
                DUMMY_MODE = str(raw_dummy_mode).lower() == "true"

except FileNotFoundError:
    logger.warning(f"'{api_conf_path}' not found. Using default ESP_CONTROLLER_IP='{DEFAULT_ESP_CONTROLLER_IP}' and DUMMY_MODE=True.")
    ESP_CONTROLLER_IP = DEFAULT_ESP_CONTROLLER_IP
    DUMMY_MODE = True 
except json.JSONDecodeError as e:
    logger.error(f"Error decoding JSON from '{api_conf_path}': {e}. Using default ESP_CONTROLLER_IP='{DEFAULT_ESP_CONTROLLER_IP}' and DUMMY_MODE=True.")
    ESP_CONTROLLER_IP = DEFAULT_ESP_CONTROLLER_IP
    DUMMY_MODE = True
except Exception as e:
    logger.critical(f"Unexpected error loading ESP controller config from '{api_conf_path}': {e}. Using defaults.")
    ESP_CONTROLLER_IP = DEFAULT_ESP_CONTROLLER_IP
    DUMMY_MODE = True

logger.info(f"Effective ESP Controller IP: '{ESP_CONTROLLER_IP}'")
logger.info(f"Effective ESP Controller DUMMY_MODE: {DUMMY_MODE}")

# Build base URL - only if IP is set and not in dummy mode (though requests won't be made in dummy mode)
BASE_URL = f"http://{ESP_CONTROLLER_IP}" if ESP_CONTROLLER_IP else ""

def update_config(new_ip=None, new_dummy_mode=None):
    """Update the ESP controller configuration.
    
    This function updates the ESP controller configuration.
    
    Args:
        new_ip (str, optional): New IP address for the ESP controller. 
                                If None, keeps the current value.
        new_dummy_mode (bool, optional): New dummy mode setting. 
                                         If None, keeps the current value.
    
    Returns:
        dict: The updated configuration with the following keys:
            - ESP_controller_IP (str): The IP address of the ESP controller
            - dummy_mode (bool): Whether to run in dummy mode
            - BASE_URL (str): The base URL for API requests
    """
    global ESP_CONTROLLER_IP, DUMMY_MODE, BASE_URL
    
    # Track whether anything changes
    changed = False
    
    # Update IP if provided
    if new_ip is not None and ESP_CONTROLLER_IP != new_ip:
        ESP_CONTROLLER_IP = new_ip
        changed = True
    
    # Update dummy mode if provided
    if new_dummy_mode is not None and DUMMY_MODE != new_dummy_mode:
        DUMMY_MODE = new_dummy_mode
        changed = True
    
    # Update BASE_URL if IP changed
    if changed:
        BASE_URL = f"http://{ESP_CONTROLLER_IP}" if ESP_CONTROLLER_IP else ""
        logger.info(f"ESP controller configuration updated.")
        logger.info(f"New ESP Controller IP: '{ESP_CONTROLLER_IP}'")
        logger.info(f"New ESP Controller DUMMY_MODE: {DUMMY_MODE}")
    
    return {
        "ESP_controller_IP": ESP_CONTROLLER_IP,
        "dummy_mode": DUMMY_MODE,
        "BASE_URL": BASE_URL
    }

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
                "model": "ESP32-S3 DUMMY_MODE",
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
