#!/usr/bin/env python3
import serial
import time

# ser = serial.Serial('/dev/ttyACM0', 9600, timeout=1)
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

if __name__ == "__main__":
    cmd = (
        bytes([254])
        + bytes([1])
        + bytes([int(8)])
        + bytes([int(2)])
        + bytes([255])
    )
    ser = serial.Serial('/dev/ttyACM0', 9600, timeout=1)
    ser.flush()
    print(ser.name)
    ser.write(cmd)
    time.sleep(0.05)
    data = ser.readline().decode('utf-8').rstrip()
    print(data)
    ser.close

