#!/usr/bin/env python3
import serial
import time
import logging

""" Command format:
- Send 0xFE to initiate command
- Terminate command with 0xFF
- Actual command is 3 bytes
- First byte is an integer with values of 1, 2, or 3
	1: Start zone, requires other 2 bytes to specify zone 
	and duration
	2: Stop zone, 2nd byte is zone, 3rd byte is ignored
	3: run program. Not yet implemented """

# Serial ports:
# /dev/tty*** for production, /dev/pts/* for virtual serial testing



def start_zone(zone, duration):
    cmd = (
        bytes([254])
        + bytes([1])
        + bytes([int(zone)])
        + bytes([int(duration)])
        + bytes([255])
    )
    write_to_serial(cmd)
    """
    try:
        arduino = serial.Serial('/dev/ttyACM0', 9600, timeout=1)
        print(arduino)
        arduino.flush()
        arduino.write(cmd)
        time.sleep(0.05)
        data = arduino.readline()
        print(data)
        arduino.close()

    except IOError as exc:
        print('Caught file I/O error' + str(exc))
        raise exc
    """

def stop_zone(zone):
    cmd = bytes([254]) + bytes([2]) + bytes([int(zone)]) + bytes([0]) + bytes([255])
    write_to_serial(cmd)


def write_to_serial(cmd):
    try:
        arduino = serial.Serial('/dev/ttyACM1', 9600, timeout=1)
        arduino.flush()
        arduino.write(cmd)
        logging.debug(f'Wrote {cmd} to serial')
        time.sleep(0.05)
        while(arduino.inWaiting() > 0):
            data = arduino.readline().decode('utf-8').rstrip()
            logging.debug(data)
            time.sleep(0.05)
        arduino.close()
        logging.debug('Closed serial connection')

    except IOError as exc:
        logging.debug(f'Caught file I/O error {str(exc)}')
        raise exc

if __name__ == "__main__":
    logging.basicConfig(filename="serial.log",
                        format='%(asctime)s %(message)s',
                        filemode='w')
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    cmd = (
        bytes([254])
        + bytes([6])
        + bytes([int(8)])
        + bytes([int(2)])
        + bytes([255])
    )
    ser = serial.Serial('/dev/ttyACM0', 9600, timeout=1)
    ser.flush()
    print(ser.name)
    ser.write(cmd)
    time.sleep(0.05)
    while(ser.inWaiting() > 0):
        data = ser.readline().decode('utf-8').rstrip()
        print(data)
        time.sleep(0.05)
    ser.close

