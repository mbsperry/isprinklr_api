import asyncio, pandas as pd, logging, time, math, json
import sprinklr_serial as hunterserial
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(filename="api.log",
                    format='%(asctime)s %(message)s',
                    filemode='a',
                    level=logging.DEBUG)
logger = logging.getLogger()

app = FastAPI()

# Read configuration (api.conf) file which contains a JSON object. 
with open("api.conf", "r") as f:
    config = json.load(f)
    DOMAIN = config["domain"]
    # DUMMY_MODE is a flag to indicate if the system is running in dummy mode (i.e. no Arduino connected, don't attempt to use serial port)
    # if config["dummy_mode"] == "True":
    #     DUMMY_MODE = True
    # else:
    #     DUMMY_MODE = False
    DUMMY_MODE = False

origins = [
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:80",
        f'http://{DOMAIN}',
        f'http://{DOMAIN}:80',
        f'http://{DOMAIN}:3000'
]

app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
)

df = pd.read_csv("data/sprinklers.csv", usecols=["zone", "name"])
sprinklers = df.to_dict("records")

schedule_df = pd.read_csv("data/schedule.csv", usecols=["zone", "day", "duration"])
schedule = schedule_df.to_dict("records")

# A flag to indicate if the long-running process is running
sprinklr_running = False
active_sprinklr = None
system_error = False
end_time = None
sprinklr_task = None

# Dummy function that just sleeps until the duration expires so that I know when the sprinkler turns off
async def run_sprinklr(sprinklr: int,duration: int):
    global sprinklr_running, active_sprinklr, end_time
    sprinklr_running = True
    active_sprinklr = sprinklr
    end_time = time.time() + duration*60
    await asyncio.sleep(duration*60)  # Simulate a long-running process with a sleep for the given duration
    sprinklr_running = False

@app.get("/api/reset_system")
async def reset_system():
    global system_error
    if not DUMMY_MODE:
        try:
            if (hunterserial.test_awake()):
                system_error = False
                return {"message": "System Reset, arduino connected"}
            else:
                system_error = True
                return {"message": "Arduino not responding", "systemStatus": "error"}
        except IOError as exc:
            system_error = True
            return {"message": "Error: Serial port error", "systemStatus": "error"}
    
@app.get("/api/start_sprinklr/{sprinklr}/duration/{duration}")
async def start_sprinklr(sprinklr: int, duration: int):
    global sprinklr_running, system_error, sprinklr_task, active_sprinklr, end_time
    if system_error:
        return {"message": "System Error", "systemStatus": "error"}
    if not sprinklr_running:
        try:
            if not DUMMY_MODE:
                if (hunterserial.start_zone(sprinklr, duration)):
                    logger.debug(f"Started sprinkler {sprinklr} for {duration} minutes: success")
                else:
                    logger.debug(f"Started sprinkler {sprinklr} for {duration} minutes: failed")
                    # raise an IOError
                    raise IOError("Command Failed")
            sprinklr_task = asyncio.create_task(run_sprinklr(sprinklr, duration))  # Start the long-running process in the background
            return {"message": f"Started sprinkler {sprinklr} for {duration} minutes", "systemStatus": "active", "zone": sprinklr}
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
    try:
        if not DUMMY_MODE:
            if (hunterserial.stop_zone(active_sprinklr)):
                logger.debug(f"Stopped sprinkler {active_sprinklr}: success")
            else:
                logger.debug(f"Stopped sprinkler {active_sprinklr}: failed")
                # raise an IOError
                raise IOError("Command Failed")
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
#    if system_error:
#        return {"duration": -1, "message": "System Error", "systemStatus": "error"}
    if sprinklr_running:
        logger.debug('Active Sprinklr %s', active_sprinklr)
        return {"systemStatus": "active", "message": f"Zone: {active_sprinklr} running", "zone": active_sprinklr, "duration": math.ceil(end_time - time.time())}
    else:
        try:
            if not DUMMY_MODE:
                if (hunterserial.test_awake()):
                    logger.debug('System Idle')
                    system_error = False
                    return {"duration": 0, "message": "System inactive", "systemStatus": "inactive"}
                else:
                    system_error = True
                    logger.debug('Arduino not responding')
                    return {"duration": -1, "message": "Arduino not responding", "systemStatus": "error"}
        except IOError as exc:
            system_error = True
            logger.debug(f"Caught file I/O error {str(exc)}")
            return {"duration": -1, "message": "Error: Serial Port error", "systemStatus": "error"}

# api route to return the list of sprinklers
@app.get("/api/sprinklers")
def get_sprinklers():
    return sprinklers

# api route to set the schedule for a sprinkler
@app.get("/api/set_schedule/{zone}/{day}/{duration}")
def set_schedule(zone: int, day: str, duration: int):
    global schedule
    # Validate the input
    if not (0 < zone <= len(sprinklers)):
        return {"message": "Invalid zone", "status": "error"}
    if duration <= 0:
        return {"message": "Invalid duration", "status": "error"}
    if day not in ["EO", "EE", "MWF", "TuTh", "MTu", "SaSu", "all", "SuTh"]:
        return {"message": "Invalid day specification", "status": "error"}

    # Update the schedule
    updated = False
    for i, sched in enumerate(schedule):
        if sched['zone'] == zone:
            schedule[i] = {'zone': zone, 'day': day, 'duration': duration}
            updated = True
            break

    if not updated:
        schedule.append({'zone': zone, 'day': day, 'duration': duration})

    # Convert schedule to a dataframe and write to CSV
    write_df = pd.DataFrame(schedule)
    write_df.to_csv('data/schedule.csv', index=False)

    return {"message": "Schedule updated successfully", "status": "success"}

# api route to return the list of schedule records
@app.get("/api/get_schedule")
def get_schedule():
    return schedule

# api route to display the tail from the api.log file
@app.get("/api/api_log")
def get_api_log():
    with open("api.log", "r") as f:
        return f.readlines()[-100:]

#api route to display the tail from the scheduler.log file
@app.get("/api/scheduler_log")
def get_scheduler_log():
    with open("scheduler.log", "r") as f:
        return f.readlines()[-100:]

#api route to display the tail from the serial.log file
@app.get("/api/serial_log")
def get_serial_log():
    with open("serial.log", "r") as f:
        return f.readlines()[-100:]

