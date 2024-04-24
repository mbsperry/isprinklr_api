# Description: reads from a .csv file and starts sprinklers based on the schedule
# The program is run every morning at 4am by a cron job
# Needs to open the csv file and determine which sprinklers need to be run that day and for how long.
# Then it needs to start the sprinklers using the API defined in api.py and wait for them to finish.

import logging
import time
import pandas as pd
import requests

#API_URL = "http://isprinklr.lan:8080/api/"
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


def read_schedule():
    """Reads the sprinkler schedule from a .csv file and returns a list of dictionaries"""
    df = pd.read_csv("data/schedule.csv", usecols=["zone", "day", "duration"])
    return df

def parse_schedule(schedule):
    # Schedule format: zone, day, duration
    # Day can be specified at all, a combination of day of the week (ex MWF), or EO for every other day
    # Duration is in minutes
    # Example: 1, MWF, 30

    # Define an array to hold the sprinklers that need to be run
    queue = []

    # Next, iterate through the schedule dataframe
    # If a sprinkler needs to be run, add it to the queue
    for index, row in schedule.iterrows():
        # If the day is "all", add it to the queue
        if row["day"] == "all":
            queue.append(row)
        # If the day is "EO", check if the day is even or odd
        elif row["day"] == "EO":
            # Only run on odd days
            if int(time.strftime("%j")) % 2 != 0:
                # This code runs only on odd days (based on day of the year)
                queue.append(row)
        elif row["day"] == "EE":
            # Only run on even days (based on day of the year)
            if int(time.strftime("%j")) % 2 == 0:
                queue.append(row)
        # If the day is a combination of days, check if the sprinkler needs to be run today
        else:
            # If the day is a combination of days, check if the sprinkler needs to be run today
            if day_abbr[int(time.strftime("%w"))] in row["day"]:
                queue.append(row)
    return queue

def check_system_status():
    # Check the API to see if the system is idle
    # If it is, return True, 0
    # If it isn't, return False, duration remaining
    # On error return False, -1
    try:
        r = requests.get(API_URL + "status")
        if r.json()["systemStatus"] == "inactive":
            return [True, 0]
        elif r.json()["systemStatus"] == "active":
            return False, r.json()["duration"]
        else:
            # System is in error
            logging.debug(f"System is in error state: {r.json()['message']}")
            return False, -1
    except Exception as e:
        logging.debug(f"Caught exception {e}")
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
    schedule = read_schedule()
    queue = parse_schedule(schedule)
    run_queue(queue)


if __name__ == "__main__":
    logging.basicConfig(filename="scheduler.log",
                        format='%(asctime)s %(levelname)s: %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S',
                        filemode='a')
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    main()
