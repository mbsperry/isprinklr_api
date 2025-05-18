import os, logging, json # Added json
from logging.handlers import RotatingFileHandler
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

# Import DOMAIN from system_status
from isprinklr.system_status import DOMAIN

from isprinklr.paths import logs_path, data_path, config_path

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
    # Use a temporary logger for this setup task, as the main logger is configured further down.
    # This ensures messages about api.conf creation are visible.
    setup_logger = logging.getLogger(__name__ + "_setup_apiconf")
    if not setup_logger.hasHandlers(): # Avoid adding duplicate handlers on re-runs if any
        setup_handler = logging.StreamHandler() # Outputs to stderr by default
        # Basic formatter for setup messages
        setup_formatter = logging.Formatter('%(asctime)s [%(name)s] %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        setup_handler.setFormatter(setup_formatter)
        setup_logger.addHandler(setup_handler)
        setup_logger.setLevel(logging.INFO) # Ensure INFO messages are shown

    setup_logger.info(f"'{api_conf_file_path}' not found. Creating a default version.")
    default_api_config = {
        "ESP_controller_IP": "",
        "domain": "localhost",
        "dummy_mode": True, # Set to True for testing without ESP controller
        "schedule_on_off": False,
        "log_level": "DEBUG"
    }
    try:
        with open(api_conf_file_path, "w") as f:
            json.dump(default_api_config, f, indent=2)
        setup_logger.info(f"Default '{api_conf_file_path}' created successfully. "
                          f"Please review and update it with your specific settings (especially ESP_controller_IP).")
    except Exception as e:
        setup_logger.error(f"CRITICAL: Failed to create default '{api_conf_file_path}': {e}. "
                           f"The application might not work correctly without it.")

# Import singletons from package root
# These imports will trigger reading of api.conf (now expected to exist)
from isprinklr.system_status import system_status, schedule_database
from isprinklr.system_controller import system_controller
from isprinklr.routers import scheduler, system, sprinklers, logs

logging.basicConfig(handlers=[RotatingFileHandler(logs_path + '/api.log', maxBytes=1024*1024, backupCount=1, mode='a')],
                    format='%(asctime)s %(name)s %(levelname)s: %(message)s', datefmt='%m-%d-%Y %H:%M:%S',
                    level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Define dependencies
async def get_system_status():
    return system_status

async def get_system_controller():
    return system_controller

async def get_schedule_database():
    return schedule_database

# This API is designed to be run inside a secure local network, but we need CORS for browser access
app = FastAPI(dependencies=[
    Depends(get_system_status),
    Depends(get_system_controller),
    Depends(get_schedule_database)
])

# Add CORS middleware to allow requests from the frontend
# Allow both development (port 3000) and production (port 80) origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        f"http://{DOMAIN}:3000", 
        f"http://{DOMAIN}:80", 
        f"http://{DOMAIN}",
        "http://localhost:3000",
        "http://localhost:80",
        "http://localhost"
    ],  # Frontend origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],  # Allow all headers
)

app.include_router(scheduler.router)
app.include_router(system.router)
app.include_router(sprinklers.router)
app.include_router(logs.router)
