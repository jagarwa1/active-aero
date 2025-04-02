#!/usr/bin/env python
import smbus2
import time
import RPi.GPIO as GPIO

# MPU6050 setup
MPU6050_ADDR = 0x68
bus = smbus2.SMBus(1)

# Servo setup
SERVO_PIN = 18 # GPIO pin
GPIO.setmode(GPIO.BCM)
GPIO.setup(SERVO_PIN, GPIO.OUT)
servo = GPIO.PWM(SERVO_PIN, 50)
servo.start(7.5) # Neutral position (around 90 degrees)

def set_servo_angle(angle):
    duty = 2 + (angle /18)
    print("changing angle to ", angle)
    GPIO.output(SERVO_PIN, True)
    servo.ChangeDutyCycle(duty)
    time.sleep(0.1)
    GPIO.output(SERVO_PIN, False)
    servo.ChangeDutyCycle(0)

# Main function
if __name__ == "__main__":
    try:
        while True:
            set_servo_angle(0)
            time.sleep(2)
            set_servo_angle(90)
            time.sleep(2)
            set_servo_angle(180)
            time.sleep(2)
            set_servo_angle(90)
            time.sleep(2)
            set_servo_angle(180)
            time.sleep(2)

    except KeyboardInterrupt:
        pass
    finally:
        print("\n\nstopping execution\n\n")
        set_servo_angle(90)
        servo.stop()
        GPIO.cleanup()
