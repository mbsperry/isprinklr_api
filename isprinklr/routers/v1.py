from fastapi import APIRouter, HTTPException
import logging, json, time, asyncio, math, pandas as pd

from ..paths import logs_path, data_path, config_path
from ..schemas import ScheduleItem, ScheduleOnOff
router = APIRouter(
    prefix = "/v1/api",
    tags = ["v1"]
)

import isprinklr.sprinklr_serial as hunterserial
logger = logging.getLogger(__name__)


# Read configuration (api.conf) file which contains a JSON object. 
try:
    with open(config_path + "/api.conf", "r") as f:
        config = json.load(f)
        DOMAIN = config["domain"]
        SCHEDULE_ON_OFF=config.get("schedule_on_off", False) 
        if not isinstance(SCHEDULE_ON_OFF, bool):
            SCHEDULE_ON_OFF = SCHEDULE_ON_OFF.lower() in ["true", "yes", "on"]
        LOG_LEVEL=config.get("log_level", "ERROR")
        logger.setLevel(getattr(logging, LOG_LEVEL, "ERROR"))
        logger.debug("Starting API")
        logger.debug(f"Run schedule is set to: {SCHEDULE_ON_OFF}")
        logger.debug(f"Log level set to {LOG_LEVEL}")
except Exception as e:
    logger.critical(f"Failed to load api.conf: {e}")


def validate_sprinklers(sprinklers: list[dict]):
    # check to make sure no more than 12 sprinklers are defined
    # This is arbitrary but we don't want files that are too large
    if len(sprinklers) > 12:
        logger.error(f"Too many sprinklers defined: {sprinklers}")
        return False
    # check that each zone is only used once
    if len(sprinklers) != len(set([x["zone"] for x in sprinklers])):
        logger.error(f"Duplicate zones in sprinklers: {sprinklers}")
        return False
    # check that each name is unique
    if len(sprinklers) != len(set([x["name"] for x in sprinklers])):
        logger.error(f"Duplicate names in sprinklers: {sprinklers}")
        return False
    return True

def validate_schedule(schedule: list[ScheduleItem]):
    valid_days = {"M", "Tu", "W", "Th", "F", "Sa", "Su", "ALL", "NONE", "EO"}
    sprinkler_zones = [x["zone"] for x in sprinklers]
    # check that each zone is only used once
    if len(schedule) != len(set([x["zone"] for x in schedule])):
        logger.error(f"Duplicate zones in schedule: {schedule}")
        return False
    for item in schedule:
        # Check if the zone is valid
        if item["zone"] not in sprinkler_zones:
            logger.error(f"Invalid zone in schedule: {item}")
            return False
        # Check if the duration is valid
        if item["duration"] < 0 or item["duration"] > 60:
            logger.error(f"Invalid duration in schedule: {item}")
            return False
        # Check if the day is valid
        days = item["day"].split(':')
        if not all(day in valid_days for day in days):
            logger.error(f"Invalid day in schedule: {item}")
            return False
        if "ALL" in days or "NONE" in days or "EO" in days:
            if len(days) > 1:
                logger.error(f"Invalid day definition in schedule. Cannot contain multiple day selector and specified days: {item}")
                return False
    return True

try:
    df = pd.read_csv(data_path + "/sprinklers.csv", usecols=["zone", "name"])
    sprinklers = df.to_dict("records")
    if not validate_sprinklers(sprinklers):
        schedule = []
except Exception as e:
    logger.error(f"Failed to load sprinklers data: {e}")
    sprinklers = []

try:
    schedule_df = pd.read_csv(data_path + "/schedule.csv", usecols=["zone", "day", "duration"])
    schedule = schedule_df.to_dict("records")
    if not validate_schedule(schedule):
        logger.error(f"Schedule.csv contained invalid sprinkler definitions")
        schedule = []
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


@router.get("/reset_system")
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
    
@router.get("/start_sprinklr/{sprinklr}/duration/{duration}")
async def start_sprinklr(sprinklr: int, duration: int):
    global sprinklr_running, system_error, sprinklr_task, active_sprinklr, end_time
    if system_error:
        return {"message": "System Error", "systemStatus": "error"}
    if not sprinklr_running:
        try:
            if (hunterserial.start_zone(sprinklr, duration)):
                logger.debug(f"Started sprinkler {sprinklr} for {duration} minutes: success")
            else:
                logger.error(f"Started sprinkler {sprinklr} for {duration} minutes: failed")
                # raise an IOError
                raise IOError("Command Failed")
            sprinklr_task = asyncio.create_task(run_sprinklr(sprinklr, duration))  # Start the long-running process in the background
            return {"message": f"Started sprinkler {sprinklr} for {duration} minutes", "systemStatus": "active", "zone": sprinklr}
        except IOError as exc:
            return {"message": "Error: Serial Port error", "systemStatus": "error"}
    else:
        return {"message": "Error: system already active", "zone": active_sprinklr, "duration": math.ceil(end_time - time.time()), "systemStatus": "active"}

@router.get("/stop_sprinklr/")
def stop_sprinklr():
    global sprinklr_running, system_error, end_time, active_sprinklr, sprinklr_task
    if system_error:
        return {"message": "System Error", "systemStatus": "error"}
    # stop the sprinklr
    try:
        if (hunterserial.stop_zone(active_sprinklr)):
            logger.debug(f"Stopped sprinkler {active_sprinklr}: success")
        else:
            logger.error(f"Stopped sprinkler {active_sprinklr}: failed")
            # raise an IOError
            raise IOError("Command Failed")
        sprinklr_task.cancel()
        sprinklr_running = False
        end_time = 0
        return {"message": f"{active_sprinklr} stopped", "systemStatus": "inactive"}
    except IOError as exc:
        logger.error(f"Caught file I/O error {str(exc)}")
        system_error = True
        return {"message": "Error: Serial Port error", "systemStatus": "error"}


@router.get("/status")
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
                logger.error('Arduino not responding')
                return {"duration": -1, "message": "Arduino not responding", "systemStatus": "error"}
        except IOError as exc:
            system_error = True
            logger.error(f"Caught file I/O error {str(exc)}")
            return {"duration": -1, "message": "Error: Serial Port error", "systemStatus": "error"}

# api route to return the list of sprinklers
@router.get("/sprinklers")
def get_sprinklers():
    if not sprinklers:
        raise HTTPException(status_code=500, detail="Failed to load sprinklers data, see logs for details")
    return sprinklers

# api route to set the schedule
# TODO: validate the new schedule
# TODO: write the new schedule to CSV file
@router.post("/set_schedule")
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
        df.to_csv(data_path + "/schedule.csv", mode='w', index=False)
        logger.debug("Schedule written to schedule.csv successfully")
    except Exception as e:
        logger.error(f"Failed to write schedule to schedule.csv: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to write schedule to schedule.csv: {e}")
    return {"message": "Schedule updated successfully", "status": "success"}

# api route to return the list of schedule records
@router.get("/get_schedule")
def get_schedule():
    if not schedule:
        raise HTTPException(status_code=500, detail="Failed to load schedule data")
    return schedule

@router.get("/get_schedule_on_off")
def get_schedule_on_off():
    return {"schedule_on_off": SCHEDULE_ON_OFF}

@router.post("/set_schedule_on_off")
def set_schedule_on_off(on_off: ScheduleOnOff):
    global SCHEDULE_ON_OFF
    SCHEDULE_ON_OFF = on_off.schedule_on_off
    config["schedule_on_off"] = SCHEDULE_ON_OFF
    try:
        with open(config_path + "/api.conf", "w") as f:
            json.dump(config, f)
    except Exception as e:
        logger.error(f"Failed to write schedule on off to api.conf: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to write schedule on off to api.conf: {e}")
    return {"message": "Schedule on off updated successfully", "status": "success"}

# api route to display the tail from the api.log file
@router.get("/api_log")
def get_api_log():
    try:
        with open(logs_path + "/api.log", "r") as f:
            return f.readlines()[-100:]
    except FileNotFoundError:
        logger.error("API Log file not found")
        raise HTTPException(status_code=404, detail="Log file not found")
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

#api route to display the tail from the scheduler.log file
@router.get("/scheduler_log")
def get_scheduler_log():
    try:
        with open(logs_path + "/scheduler.log", "r") as f:
            return f.readlines()[-100:]
    except FileNotFoundError:
        logger.error("Scheduler Log file not found")
        raise HTTPException(status_code=404, detail="Log file not found")
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

#api route to display the tail from the serial.log file
@router.get("/serial_log")
def get_serial_log():
    try:
        with open(logs_path + "/serial.log", "r") as f:
            return f.readlines()[-100:]
    except FileNotFoundError:
        logger.error("Serial Log file not found")
        raise HTTPException(status_code=404, detail="Log file not found")
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")