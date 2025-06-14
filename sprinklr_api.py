import logging
import json
import requests
from logging.handlers import RotatingFileHandler

# Set up logging
file_handler = RotatingFileHandler('logs/api_client.log', maxBytes=1024*1024, backupCount=1, mode='a')
formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s', datefmt='%m-%d-%Y %H:%M:%S')
file_handler.setFormatter(formatter)
logger = logging.getLogger("api_client_log")
logger.setLevel(logging.ERROR)
logger.addHandler(file_handler)
logger.propagate = False

# Read configuration from api.conf
try:
    with open("config/api.conf", "r") as f:
        config = json.load(f)
        ESP_CONTROLLER_IP = config["esp_controller_ip"]
        LOG_LEVEL = config.get("log_level", "ERROR")
        DUMMY_MODE = config.get("dummy_mode", False) == "True"
        BASE_URL = f"http://{ESP_CONTROLLER_IP}"
        logger.setLevel(getattr(logging, LOG_LEVEL, "ERROR"))
        logger.debug(f"ESP controller IP set to: {ESP_CONTROLLER_IP}")
        logger.debug(f"Base URL set to: {BASE_URL}")
        logger.debug(f"Dummy mode set to: {DUMMY_MODE}")
        logger.debug(f"Log level set to: {LOG_LEVEL}")
except Exception as e:
    logger.error(f"Failed to load api.conf: {e}")
    # Set default values
    ESP_CONTROLLER_IP = "localhost"
    BASE_URL = f"http://{ESP_CONTROLLER_IP}"
    DUMMY_MODE = True

def test_awake():
    """
    Check if the ESP controller is connected and responding.
    Returns True if the controller is awake, False otherwise.
    """
    if DUMMY_MODE:
        return True
    
    try:
        response = requests.get(f"{BASE_URL}/api/status", timeout=5)
        if response.status_code == 200:
            status_data = response.json()
            if status_data.get("status") == "ok":
                logger.debug("ESP controller is awake and responding")
                return True
        
        logger.error(f"ESP controller not responding properly: {response.text}")
        return False
    except Exception as e:
        logger.error(f"Error connecting to ESP controller: {str(e)}")
        return False

def start_zone(sprinkler, duration):
    """
    Start a sprinkler zone for the specified duration.
    
    Args:
        sprinkler (int): The zone number (1-20)
        duration (int): Duration in minutes (1-120)
        
    Returns:
        bool: True if successful, False otherwise
    """
    if DUMMY_MODE:
        return True
    
    # Validate inputs
    if not isinstance(sprinkler, int) or sprinkler < 1 or sprinkler > 20:
        logger.error(f"Invalid sprinkler zone: {sprinkler}")
        return False
    
    if not isinstance(duration, int) or duration < 1 or duration > 120:
        logger.error(f"Invalid duration: {duration}")
        return False
    
    try:
        payload = {
            "zone": sprinkler,
            "minutes": duration
        }
        
        response = requests.post(
            f"{BASE_URL}/api/start", 
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        
        if response.status_code == 200:
            response_data = response.json()
            if response_data.get("status") == "started":
                logger.debug(f"Successfully started zone {sprinkler} for {duration} minutes")
                return True
        
        logger.error(f"Failed to start zone {sprinkler}: {response.text}")
        return False
    except Exception as e:
        logger.error(f"Error communicating with ESP controller: {str(e)}")
        return False

def stop_zone(sprinkler):
    """
    Stop a sprinkler zone.
    
    Args:
        sprinkler (int): The zone number (1-20)
        
    Returns:
        bool: True if successful, False otherwise
    """
    if DUMMY_MODE:
        return True
    
    # Validate input
    if not isinstance(sprinkler, int) or sprinkler < 1 or sprinkler > 20:
        logger.error(f"Invalid sprinkler zone: {sprinkler}")
        return False
    
    try:
        payload = {
            "zone": sprinkler
        }
        
        response = requests.post(
            f"{BASE_URL}/api/stop", 
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        
        if response.status_code == 200:
            response_data = response.json()
            if response_data.get("status") == "stopped":
                logger.debug(f"Successfully stopped zone {sprinkler}")
                return True
        
        logger.error(f"Failed to stop zone {sprinkler}: {response.text}")
        return False
    except Exception as e:
        logger.error(f"Error communicating with ESP controller: {str(e)}")
        return False
