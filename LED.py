
import sys
import os
sys.path.append(os.path.expanduser('~/active-aero/lib/python3.11/site-packages'))
import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BOARD)  # Use physical board numbering
GPIO.setup(11, GPIO.OUT)
GPIO.setup(13, GPIO.OUT)
GPIO.setup(15, GPIO.OUT)

# state must be 1 or 0
def control_third_light(state):
    if state == 1:
        GPIO.output(13, GPIO.HIGH)
    elif state == 0:
        GPIO.output(13, GPIO.LOW)

def control_tail_lights(state):
    if state == 1:
        GPIO.output(15, GPIO.HIGH)
    elif state == 0:
        GPIO.output(15, GPIO.LOW)

def control_turbo_lights(state):
    if state == 1:
        GPIO.output(15, GPIO.HIGH)
    elif state == 0:
        GPIO.output(15, GPIO.LOW)

def blink_third_light():
    for x in range(3):
        control_third_light(1)        
        time.sleep(.1)
        
        control_third_light(0)       
        time.sleep(.1)

if __name__ == "__main__":
    control_tail_lights(1)
    while True:
        blink_third_light()
        time.sleep(1)

    GPIO.cleanup()