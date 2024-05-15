# iSprinklr API

iSprinklr uses an arduino to control a Hunter Pro-c sprinkler system.

There are 3 components:
- iSprinklr_arduino (https://github.com/mbsperry/iSprinklr_arduino) is self expalanatory and runs on the arduino. It accepts commands from a serial interface. 
- iSprinklr_api (https://github.com/mbsperry/isprinklr_api) is an API build with python and FastAPI. It provides a RESTful interface for serial control of the arduino.
- iSprinklr_react (https://github.com/mbsperry/iSprinklr_react) is the front end web app built in react. It provides a web interface for the API.

## Hardware layout
Connect LED_BUILTIN pin (pin 13) to REM pin on the Hunter Pro-C. Excellent overview on how to connect the arduino to the Pro-c here: https://github.com/ecodina/hunter-wifi/blob/master/docs/pages/hunterconnection.md
Connect arduino to a raspberry pi (or similar) via USB on the programming port.

## Installation
- Build and install iSprinklr_arduino using PlatformIO
- Git clone iSprinklr_api. Create a virtual environment and install requirements.txt using pip. 
- Rename example.conf to api.conf and adjust to your setup.
- Adjust data/sprinklers.csv to match your existing sprinkler zones and data/schedule.csv to your watering schedule.
- Run the API using uvicorn.
- Git clone iSprinklr_react. Build and serve via nginx or node serve. 
- If you want to use the scheduling feature you will need to setup a cron job to run the scheduler.py script daily.

Credit:
iSprinklr_arduino relies on the HunterRoam library from ecodina (https://github.com/ecodina/hunter-wifi) to actually control the Hunter Pro-c.