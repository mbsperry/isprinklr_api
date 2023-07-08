import asyncio, pandas as pd, logging, time, math
import sprinklr_serial as hunterserial
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(filename="api.log",
                    format='%(asctime)s %(message)s',
                    filemode='w',
                    level=logging.DEBUG)
logger = logging.getLogger()

app = FastAPI()

origins = [
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:80",
        "http://isprinklr.lan",
        "http://isprinklr.lan:80",
        "http://isprinklr.lan:3000",
]

app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
)


df = pd.read_csv("data/sprinklers.csv", usecols=["zone", "name"])
sprinklers = df.to_dict("records")

# A flag to indicate if the long-running process is running
sprinklr_running = False
active_sprinklr = None
system_error = False
end_time = None
sprinklr_task = None

async def run_sprinklr(sprinklr: int,duration: int):
    global sprinklr_running, active_sprinklr, end_time
    sprinklr_running = True
    active_sprinklr = sprinklr
    end_time = time.time() + duration*60
    logger.debug(f"Starting sprinkler {active_sprinklr}, ending at {end_time}")
    try:
        hunterserial.start_zone(sprinklr, duration)
        await asyncio.sleep(duration*60)  # Simulate a long-running process with a sleep for the given duration
        sprinklr_running = False
    except IOError as exc:
        logger.debug(f"Caught file I/O error {str(exc)}")
        system_error = True
        raise exc

@app.get("/api/start_sprinklr/{sprinklr}/duration/{duration}")
async def start_sprinklr(sprinklr: int, duration: int):
    global sprinklr_running, system_error, sprinklr_task, active_sprinklr, end_time
    if system_error:
        return {"message": "System Error", "systemStatus": "error"}
    if not sprinklr_running:
        try:
            sprinklr_task = asyncio.create_task(run_sprinklr(sprinklr, duration))  # Start the long-running process in the background
            return {"message": f"Started sprinkler {sprinklr} for {duration} minutes", "systemStatus": "active"}
        except IOError as exc:
            return {"message": "Error: Serial Port error", "systemStatus": "error"}
    else:
        return {"message": "Error: system already active", "zone": active_sprinklr, "duration": math.ceil(end_time - time.time()), "systemStatus": "active"}

@app.get("/api/stop_sprinklr/")
def stop_sprinklr():
    global sprinklr_running, system_error, end_time, active_sprinklr, sprinklr_task
    if system_error:
        return {"message": "System Error", "systemStatus": "error"}
    # stop the sprinklr
    logger.debug(f"Stopping sprinkler {active_sprinklr}")
    try:
        hunterserial.stop_zone(active_sprinklr)
        sprinklr_task.cancel()
        sprinklr_running = False
        end_time = 0
        return {"message": f"{active_sprinklr} stopped", "systemStatus": "inactive"}
    except IOError as exc:
        logger.debug(f"Caught file I/O error {str(exc)}")
        system_error = True
        return {"message": "Error: Serial Port error", "systemStatus": "error"}


@app.get("/api/status")
def get_status():
    global sprinklr_running, active_sprinklr, system_error
    if system_error:
        return {"duration": -1, "message": "System Error", "systemStatus": "error"}
    if sprinklr_running:
        logger.debug('Active Sprinklr %s', active_sprinklr)
        return {"systemStatus": "active", "message": f"Zone: {active_sprinklr} running", "zone": active_sprinklr, "duration": math.ceil(end_time - time.time())}
    else:
        logger.debug('System Idle')
        return {"duration": 0, "message": "System inactive", "systemStatus": "inactive"}

# api route to return the list of sprinklers
@app.get("/api/sprinklers")
def get_sprinklers():
    return sprinklers
