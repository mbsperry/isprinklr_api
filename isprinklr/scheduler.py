# Description: reads from a .csv file and starts sprinklers based on the schedule
# The program is run every morning at 4am by a cron job
# Needs to open the csv file and determine which sprinklers need to be run that day and for how long.
# Then it needs to start the sprinklers using the API defined in api.py and wait for them to finish.

import logging
from logging.handlers import RotatingFileHandler
import time
import pandas as pd
import requests

from isprinklr.paths import logs_path, data_path

API_URL = "http://localhost:8080/api/"

day_abbr = {
        0: "Su",
        1: "M",
        2: "Tu",
        3: "W",
        4: "Th",
        5: "F",
        6: "Sa"
        }

# TODO: don't read schedule.csv directly, get schedule from API

def read_schedule():
    """Reads the sprinkler schedule from a .csv file and returns a list of dictionaries"""
    try: 
        df = pd.read_csv(data_path + "/schedule.csv", usecols=["zone", "day", "duration"])
        return df, False
    except Exception as e:
        logging.error(f"Unable to open schedule.csv: {e}")
        return None, True

def parse_schedule(schedule):
    # Schedule format: zone, day, duration
    # Day can be specified at all, a combination of day of the week (ex MWF), or EO for every other day
    # Duration is in minutes
    # Example: 1, MWF, 30

    # Define an array to hold the sprinklers that need to be run
    queue = []

    # Next, iterate through the schedule dataframe
    # If a sprinkler needs to be run, add it to the queue
    # TODO: needs better validation of each schedule item, better yet get schedule from API since that already has validation
    for index, row in schedule.iterrows():
        # If the day is "all", add it to the queue
        if row["day"].upper() == "ALL":
            queue.append({"zone": row["zone"], "day": row["day"], "duration": row["duration"]})
        # If the day is "EO", check if the day is even or odd
        elif row["day"].upper() == "EO":
            # Only run on odd days
            if int(time.strftime("%j")) % 2 != 0:
                # This code runs only on odd days (based on day of the year)
                queue.append({"zone": row["zone"], "day": row["day"], "duration": row["duration"]})
        elif row["day"].upper() == "EE":
            # Only run on even days (based on day of the year)
            # Not currently implemented in API
            if int(time.strftime("%j")) % 2 == 0:
                queue.append({"zone": row["zone"], "day": row["day"], "duration": row["duration"]})
        elif row["day"].upper() == "NONE":
            # Do not run this sprinkler
            pass
        # If the day is a combination of days, check if the sprinkler needs to be run today
        else:
            # If the day is a combination of days, check if the sprinkler needs to be run today
            if day_abbr[int(time.strftime("%w"))] in row["day"]:
                queue.append({"zone": row["zone"], "day": row["day"], "duration": row["duration"]})
    return queue

def check_system_status():
    # Check the API to see if the system is idle
    # If it is, return True, 0
    # If it isn't, return False, duration remaining
    # On error return False, -1
    for attempt in range(3):
        try:
            r = requests.get(API_URL + "status")
            if r.json()["systemStatus"] == "inactive":
                return [True, 0]
            elif r.json()["systemStatus"] == "active":
                return False, r.json()["duration"]
            else:
                # System is in error
                if attempt == 2:
                    logging.debug(f"System is in error state: {r.json()['message']}")
                    return False, -1
                logging.debug(f"Received status: {r.json()['systemStatus']}, retrying")
                time.sleep(180)  # Sleep for 3 minutes (180 seconds)
        except Exception as e:
            logging.debug(f"Attempt {attempt + 1}: Caught exception {e}")
            return False, -1

def run_queue(queue):
    # Iterate through the queue and start the sprinklers
    for sprinkler in queue:
        # First, check to make sure the system is idle
        status = check_system_status()
        if status[0] == False:
            if status[1] == -1:
                # System is in error
                logging.debug("System is in error state")
                return False
            if status[1] > 0:
                # System is active, wait for it to finish
                logging.debug(f"System is active, waiting for {status[1]} minutes")
                time.sleep(status[1]*60)
        # If the system is idle, start the sprinkler
        # Need to wait for each sprinkler to finish before starting the next one
        logging.debug(f"Starting sprinkler {sprinkler['zone']} for {sprinkler['duration']} minutes")
        try:
            r = requests.get(API_URL + f"start_sprinklr/{sprinkler['zone']}/duration/{sprinkler['duration']}")
            if r.json()["systemStatus"] == "active":
                time.sleep(sprinkler["duration"]*60)
            else:
                logging.debug(f"Error starting sprinkler {sprinkler['zone']}")
                return False
        except Exception as e:
            logging.debug(f"Caught exception {e}")
            return False
    return True

def main():
    logging.debug("--------Starting scheduler--------")
    logging.debug(f"Today's day of week/day number: {time.strftime('%A-%j')}")
    try:
        schedule, isError = read_schedule()
        if isError:
            raise Exception("Unable to read schedule.csv")
        queue = parse_schedule(schedule)
        if len(queue) == 0:
            logging.debug("No sprinklers scheduled to run today")
            return
        run_queue(queue)
    except Exception as e:
        logging.error(f"Scheduler Error: {e}")
        return



if __name__ == "__main__":
    logging.basicConfig(handlers=[RotatingFileHandler(logs_path + '/scheduler.log', maxBytes=1024*1024, backupCount=1, mode='a')],
                    format='%(asctime)s %(levelname)s: %(message)s',
                    level=logging.DEBUG) 
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    try:
        r = requests.get(API_URL + "get_schedule_on_off")
        if r.json()["schedule_on_off"] == True:
            main()
        else:
            logging.debug("Schedule is off, not running")
    except Exception as e:
        logging.error(f"Caught exception {e}")
