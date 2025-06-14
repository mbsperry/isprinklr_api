## Overview

iSprinklr uses an ESP32 to control a Hunter Pro-c sprinkler system.

![Version](https://img.shields.io/badge/version-2.1.1-blue)

There are 3 components:
- iSprinklr_esp (https://github.com/mbsperry/isprinklr_esp) is the ESP32 controller which has a very simple REST API for turning the sprinkler system on/off
- iSprinklr_api (https://github.com/mbsperry/isprinklr_api) is an API built with Python and FastAPI. It provides a much more powerful API for controlling the system including monitoring which system is active and running user created schedules. 
- iSprinklr_react (https://github.com/mbsperry/iSprinklr_react) is the front end web app built in React. It provides a web interface for the API.

## iSprinklr_api Features
- Central source of truth for system state (on, off, duration remaining, etc).
- Track last time system was run, last time a schedule was run. 
- Allows for naming different sprinkler zones.
- Edit and run different schedules.
- Automated schedule execution using APScheduler (configurable timing)
- Read system logs to debug any connection issues.

### Installation Steps
1. Build and install iSprinklr_esp using PlatformIO with your preferred network configuration. The ESP32 will print out its IP address to the serial monitor when it connects to the network. Make note of this IP. 
2. Git clone iSprinklr_api. Create a virtual environment and install requirements.txt using pip. 
   **Initial configuration can be performed using one of the following options:**
   - **Option 1 (Recommended):** Run the interactive CLI configuration tool:  
     `python configure.py`
   - **Option 2:** Start the API, then use the web interface at `http://API_IP:8000/docs` to configure the system:
     - Set system settings at:  
       `http://API_IP:8000/docs#/system/update_config_api_system_config_put`
     - Configure sprinkler zones at:  
       `http://API_IP:8000/docs#/sprinklers/update_sprinklers_api_sprinklers__put`
   After configuration, run the API using `fastapi run main.py` from inside the isprinklr directory.
3. Optional: setup systemd daemon to make sure isprinklr_api runs after restart, power outage, etc. PM2 (requires node) is another option that is *much* easier to setup.  
4. Git clone iSprinklr_react. Update src/config.js. Build and serve via nginx or node serve.

Credit:
iSprinklr_esp relies on the HunterRoam library from ecodina (https://github.com/ecodina/hunter-wifi) to actually control the Hunter Pro-c.

## Versioning

Moves to semantic versioning. 

For a detailed changelog of versions and features, see the [CHANGELOG.md](CHANGELOG.md) file.
