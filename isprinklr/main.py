import os, logging
from logging.handlers import RotatingFileHandler
from fastapi import FastAPI, Depends

from isprinklr.paths import logs_path, data_path, config_path

# check to see if logs directory exists, if not create it
if not os.path.exists(logs_path):
    os.makedirs(logs_path)

# Import singletons from package root
from isprinklr import system_status, system_controller
from isprinklr.routers import scheduler, v1, system, sprinklers, logs

logging.basicConfig(handlers=[RotatingFileHandler(logs_path + '/api.log', maxBytes=1024*1024, backupCount=1, mode='a')],
                    format='%(asctime)s %(name)s %(levelname)s: %(message)s', datefmt='%m-%d-%Y %H:%M:%S',
                    level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Define dependencies
async def get_system_status():
    return system_status

async def get_system_controller():
    return system_controller

app = FastAPI(dependencies=[
    Depends(get_system_status),
    Depends(get_system_controller)
])

app.include_router(v1.router)
app.include_router(scheduler.router)
app.include_router(system.router)
app.include_router(sprinklers.router)
app.include_router(logs.router)
