import os, logging
from logging.handlers import RotatingFileHandler
from fastapi import FastAPI, Depends

from isprinklr.paths import logs_path, data_path, config_path

# check to see if logs directory exists, if not create it
if not os.path.exists(logs_path):
    os.makedirs(logs_path)

# Import singletons from package root
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

# This API is designed to be run inside a secure local netork. As such, there is no need for authentication or CORS middleware
app = FastAPI(dependencies=[
    Depends(get_system_status),
    Depends(get_system_controller),
    Depends(get_schedule_database)
])

app.include_router(scheduler.router)
app.include_router(system.router)
app.include_router(sprinklers.router)
app.include_router(logs.router)
