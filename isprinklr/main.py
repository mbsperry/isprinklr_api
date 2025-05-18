import os, logging, json 
from logging.handlers import RotatingFileHandler
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

# defaults
USE_STRICT_CORS = False
DOMAIN = "localhost" 

from isprinklr.paths import logs_path, data_path, config_path

logging.basicConfig(handlers=[RotatingFileHandler(logs_path + '/api.log', maxBytes=1024*1024, backupCount=1, mode='a')],
                    format='%(asctime)s %(name)s %(levelname)s: %(message)s', datefmt='%m-%d-%Y %H:%M:%S',
                    level=logging.DEBUG)
logger = logging.getLogger(__name__)

# check to see if logs directory exists, if not create it
if not os.path.exists(logs_path):
    os.makedirs(logs_path)

# check to see if data directory exists, if not create it
if not os.path.exists(data_path):
    os.makedirs(data_path)

# check to see if config directory exists, if not create it
if not os.path.exists(config_path):
    os.makedirs(config_path)

# Ensure api.conf exists with default values if not present.
# This is done before importing system_status, as system_status (and esp_controller)
# will attempt to read this file immediately upon import.
api_conf_file_path = os.path.join(config_path, "api.conf")
if not os.path.exists(api_conf_file_path):
    logger.info(f"'{api_conf_file_path}' not found. Creating a default version.")
    default_api_config = {
        "ESP_controller_IP": "",
        "domain": "localhost",
        "dummy_mode": True, # Set to True for testing without ESP controller
        "schedule_on_off": False,
        "log_level": "DEBUG",
        "USE_STRICT_CORS": False # Controls whether to use strict CORS settings
    }
    try:
        with open(api_conf_file_path, "w") as f:
            json.dump(default_api_config, f, indent=2)
        logger.info(f"Default '{api_conf_file_path}' created successfully. "
                          f"Please review and update it with your specific settings (especially ESP_controller_IP).")
    except Exception as e:
        logger.error(f"CRITICAL: Failed to create default '{api_conf_file_path}': {e}. "
                           f"The application might not work correctly without it.")

# Read settings from api.conf after ensuring the file exists
try:
    with open(api_conf_file_path, "r") as f:
        config = json.load(f)
        # Get domain with default localhost if not present
        DOMAIN = config.get("domain", "localhost")
        if not DOMAIN:  # Handle empty string or null
            logger.warning(f"'domain' in '{api_conf_file_path}' is empty or null. Using default: 'localhost'.")
            DOMAIN = "localhost"
        
        # Get USE_STRICT_CORS with default false if not present
        USE_STRICT_CORS = config.get("USE_STRICT_CORS", False)
        if isinstance(USE_STRICT_CORS, str):
            # Convert string value to boolean 
            USE_STRICT_CORS = USE_STRICT_CORS.lower() in ["true", "yes", "on", "1"]
    logger.info(f"Using domain: {DOMAIN}")
    logger.info(f"Using CORS security setting: Strict={USE_STRICT_CORS}")
except Exception as e:
    logger.error(f"Error reading settings from '{api_conf_file_path}': {e}. Using defaults: domain='localhost', USE_STRICT_CORS=False")
    DOMAIN = "localhost"
    USE_STRICT_CORS = False

from isprinklr.system_status import system_status, schedule_database
from isprinklr.system_controller import system_controller
from isprinklr.routers import scheduler, system, sprinklers, logs

# Define dependencies
async def get_system_status():
    return system_status

async def get_system_controller():
    return system_controller

async def get_schedule_database():
    return schedule_database

app = FastAPI(dependencies=[
    Depends(get_system_status),
    Depends(get_system_controller),
    Depends(get_schedule_database)
])

# Add CORS middleware to allow requests from the frontend
if USE_STRICT_CORS:
    logger.info("Using strict CORS - only allowing specific origins")
    allowed_origins = [
        f"http://{DOMAIN}:3000", 
        f"http://{DOMAIN}:80", 
        f"http://{DOMAIN}",
        "http://localhost:3000",
        "http://localhost:80",
        "http://localhost"
    ]
else:
    logger.info("Using non-strict CORS - allowing all origins")
    allowed_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False if "*" in allowed_origins else True,  # Must be False when allow_origins=["*"]
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
)

app.include_router(scheduler.router)
app.include_router(system.router)
app.include_router(sprinklers.router)
app.include_router(logs.router)
