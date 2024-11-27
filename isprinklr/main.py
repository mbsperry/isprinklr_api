import os, logging
from logging.handlers import RotatingFileHandler
from fastapi import FastAPI, Depends

from isprinklr.paths import logs_path, data_path, config_path

# check to see if logs directory exists, if not create it
if not os.path.exists(logs_path):
    os.makedirs(logs_path)

from isprinklr.system_status import SystemStatus
from isprinklr.routers import scheduler, v1, system, sprinklers, logs

system_status = SystemStatus()

logging.basicConfig(handlers=[RotatingFileHandler(logs_path + '/api.log', maxBytes=1024*1024, backupCount=1, mode='a')],
                    format='%(asctime)s %(name)s %(levelname)s: %(message)s', datefmt='%m-%d-%Y %H:%M:%S',
                    level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI(dependencies=[Depends(lambda: system_status)])

app.include_router(v1.router)
app.include_router(scheduler.router)
app.include_router(system.router)
app.include_router(sprinklers.router)
app.include_router(logs.router)
