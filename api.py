import asyncio, pandas as pd, logging, time, math, json
import sprinklr_serial as hunterserial
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing_extensions import TypedDict
from typing import List

logging.basicConfig(filename="api.log",
                    format='%(asctime)s %(message)s',
                    filemode='a',
                    level=logging.DEBUG)
logger = logging.getLogger()

app = FastAPI()

# TODO: api path to update sprinkler names

class ScheduleItem(TypedDict):
    zone: int
    day: str
    duration: int

# Read configuration (api.conf) file which contains a JSON object. 
with open("api.conf", "r") as f:
    config = json.load(f)
    DOMAIN = config["domain"]

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

try:
    df = pd.read_csv("data/sprinklers.csv", usecols=["zone", "name"])
    sprinklers = df.to_dict("records")
except Exception as e:
    logger.error(f"Failed to load sprinklers data: {e}")
    sprinklers = []

try:
    schedule_df = pd.read_csv("data/schedule.csv", usecols=["zone", "day", "duration"])
    schedule = schedule_df.to_dict("records")
except Exception as e:
    logger.error(f"Failed to load schedule data: {e}")
    schedule = []

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

def validate_schedule(schedule: list[ScheduleItem]):
    # check that each zone is only used once
    if len(schedule) != len(set([x["zone"] for x in schedule])):
        logger.debug(f"Duplicate zones in schedule: {schedule}")
        return False

    # check if the zone number is valid
    for item in schedule:
        if item["zone"] not in [x["zone"] for x in sprinklers]:
            logger.debug(f"Invalid zone in schedule: {item}")
            return False

    # check to make sure the duration is valid
    for item in schedule:
        if item["duration"] < 0 or item["duration"] > 60:
            logger.debug(f"Invalid duration in schedule: {item}")
            return False

    # check to make sure the day is valid
    # the day field can contain any combination of M,Tu,W,Th,F,Sa,Su OR ALL, NONE, EO
    valid_days = {"M", "Tu", "W", "Th", "F", "Sa", "Su", "ALL", "NONE", "EO"}
    for item in schedule:
        days = item["day"].split(':')
        if not all(day in valid_days for day in days):
            logger.debug(f"Invalid day in schedule: {item}")
            return False
    for item in schedule:
        days = item["day"].split(':')
        if "ALL" in days or "NONE" in days or "EO" in days:
            if len(days) > 1:
                logger.debug(f"Invalid day in schedule: {item}")
                return False
    return True
    


@app.get("/api/reset_system")
async def reset_system():
    global system_error
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
    if not sprinklers:
        raise HTTPException(status_code=500, detail="Failed to load sprinklers data")
    return sprinklers

# api route to set the schedule
# TODO: validate the new schedule
# TODO: write the new schedule to CSV file
@app.post("/api/set_schedule")
def set_schedule(new_schedule: list[ScheduleItem]):
    global schedule
    logger.debug(f"Setting schedule: {new_schedule}")
    if validate_schedule(new_schedule):
        schedule = new_schedule
    else:
        raise HTTPException(status_code=400, detail="Invalid schedule")
    import pandas as pd
    df = pd.DataFrame(schedule)
    try:
        df.to_csv('data/schedule.csv', mode='w', index=False)
        logger.debug("Schedule written to schedule.csv successfully")
    except Exception as e:
        logger.error(f"Failed to write schedule to schedule.csv: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to write schedule to schedule.csv: {e}")
    return {"message": "Schedule updated successfully", "status": "success"}

# api route to return the list of schedule records
@app.get("/api/get_schedule")
def get_schedule():
    if not schedule:
        raise HTTPException(status_code=500, detail="Failed to load schedule data")
    return schedule

# api route to display the tail from the api.log file
@app.get("/api/api_log")
def get_api_log():
    try:
        with open("api.log", "r") as f:
            return f.readlines()[-100:]
    except FileNotFoundError:
        logger.error("API Log file not found")
        raise HTTPException(status_code=404, detail="Log file not found")
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

#api route to display the tail from the scheduler.log file
@app.get("/api/scheduler_log")
def get_scheduler_log():
    try:
        with open("scheduler.log", "r") as f:
            return f.readlines()[-100:]
    except FileNotFoundError:
        logger.error("Scheduler Log file not found")
        raise HTTPException(status_code=404, detail="Log file not found")
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

#api route to display the tail from the serial.log file
@app.get("/api/serial_log")
def get_serial_log():
    try:
        with open("serial.log", "r") as f:
            return f.readlines()[-100:]
    except FileNotFoundError:
        logger.error("Serial Log file not found")
        raise HTTPException(status_code=404, detail="Log file not found")
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

