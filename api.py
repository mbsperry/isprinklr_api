import asyncio, pandas as pd, logging, time, math
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(filename="api.log",
                    format='%(asctime)s %(message)s',
                    filemode='w')
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

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

async def run_sprinklr(sprinklr: int,duration: int):
    global sprinklr_running, active_sprinklr, end_time
    sprinklr_running = True
    active_sprinklr = sprinklr
    end_time = time.time() + duration
    await asyncio.sleep(duration)  # Simulate a long-running process with a sleep for the given duration
    sprinklr_running = False

@app.get("/api/start_sprinklr/{sprinklr}/duration/{duration}")
async def start_sprinklr(sprinklr: int, duration: int):
    global sprinklr_running, system_error
    if system_error:
        return {"message": "System Error"}
    if not sprinklr_running:
        asyncio.create_task(run_sprinklr(sprinklr, duration))  # Start the long-running process in the background
        return {"message": f"Started sprinkler {sprinklr} for {duration} seconds"}
    else:
        return {"message": "System Running"}

@app.get("/api/status")
def get_status():
    global sprinklr_running, active_sprinklr, system_error
    if system_error:
        return {"duration": -1, "message": "System Error"}
    if sprinklr_running:
        logger.debug('Test')
        logger.debug('Active Sprinklr %s', active_sprinklr)
        return {"message": f"Zone: {active_sprinklr} running", "zone": active_sprinklr, "duration": math.ceil(end_time - time.time())}
    else:
        return {"duration": 0, "message": "System Idle"}

# api route to return the list of sprinklers
@app.get("/api/sprinklers")
def get_sprinklers():
    return sprinklers
