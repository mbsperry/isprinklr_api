## Overview

iSprinklr uses an ESP32 to control a Hunter Pro-c sprinkler system.

There are 3 components:
- iSprinklr_esp (https://github.com/mbsperry/isprinklr_esp) is the ESP32 controller which has a very simple REST API for turning the sprinkler system on/off
- iSprinklr_api (https://github.com/mbsperry/isprinklr_api) is an API built with Python and FastAPI. It provides a much more powerful API for controlling the system including monitoring which system is active and running user created schedules. 
- iSprinklr_react (https://github.com/mbsperry/iSprinklr_react) is the front end web app built in React. It provides a web interface for the API.

## iSprinklr_api Features
- Central source of truth for system state (on, off, duration remaining, etc).
- Track last time system was run, last time a schedule was run. 
- Allows for naming different sprinkler zones.
- Edit and run different schedules.
- Read system logs to debug any connection issues.

### Installation Steps
1. Build and install iSprinklr_esp using PlatformIO with your preferred network configuration. The ESP32 will print out its IP address to the serial monitor when it connects to the network. Make note of this IP. 
2. Git clone iSprinklr_api. Create a virtual environment and install requirements.txt using pip. Create config/api.conf following the example.conf file. Put the IP of the ESP32 in the config/api.conf file. Assuming iSprinklr_api and the iSprinklr_react frontend are run on the same server, put the domain name in api.conf. Run the API using `fastapi run main.py` from inside the isprinklr directory.
3. Optional: setup daemon to make sure isprinklr_api runs after restart, power outage, etc. 
4. Git clone iSprinklr_react. Update src/config.js. Build and serve via nginx or node serve.
5. If you want to use the scheduling feature you will need to setup a cron job to run the `scheduler.py` script daily.

Credit:
iSprinklr_esp relies on the HunterRoam library from ecodina (https://github.com/ecodina/hunter-wifi) to actually control the Hunter Pro-c.
