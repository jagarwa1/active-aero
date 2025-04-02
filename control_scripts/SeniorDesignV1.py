#!/usr/bin/env python3
import smbus2
import time
import RPi.GPIO as GPIO
import math
import tkinter as tk
from tkinter import ttk
import csv
from datetime import datetime
import sys
sys.path.append('/home/benchh1/active-aero/lib/python3.11/site-packages')
from adafruit_servokit import ServoKit

# PWM servo driver setup
kit = ServoKit(channels=8)

# MPU6050 setup
MPU6050_ADDR = 0x69
bus = smbus2.SMBus(1)

# Servo setup


# Speedometer setup (Wheel Encoder)


# Logging setup
log_filename = f"wing_data_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
logging_active = True

# Wheel Encoder Callback




# Initialize MPU6050
def init_gyro_accel():
    bus.write_byte_data(MPU6050_ADDR, 0x6B, 0)  # Wake up the MPU6050

# Read raw data from MPU6050
def read_raw_data(addr):
    high = bus.read_byte_data(MPU6050_ADDR, addr)
    low = bus.read_byte_data(MPU6050_ADDR, addr + 1)
    value = (high << 8) | low
    if value > 32768:
        value -= 65536
    return value

# Convert raw data to acceleration (in g) and gyro data (in degrees/sec)
def get_sensor_data():
    accel_x = read_raw_data(0x3B) / 16384.0
    accel_y = read_raw_data(0x3D) / 16384.0
    accel_z = read_raw_data(0x3F) / 16384.0

    gyro_x = read_raw_data(0x43) / 131.0
    gyro_y = read_raw_data(0x45) / 131.0
    gyro_z = read_raw_data(0x47) / 131.0

    return accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z

# Calculate speed from pulse count
#def calculate_speed():
   # global pulse_count, last_time, speed_mps
   # current_time = time.time()
   # elapsed_time = current_time - last_time

    #if elapsed_time > 0.1:
     #   rotations = pulse_count
    #    pulse_count = 0
    #    speed_mps = (rotations * WHEEL_CIRCUMFERENCE) / elapsed_time
     #   last_time = current_time
   # return speed_mps

# Control the servo angle
def set_servo_angle(angle):
    kit.servo[0].angle = 180-angle
    kit.servo[1].angle = 180-angle

# Log data to CSV
def log_data(timestamp, accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z, wing_angle):
    if logging_active:
        with open(log_filename, mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([timestamp, accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z, wing_angle])

# GUI Setup
class WingControlGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Active Wing Control")
        self.geometry("500x500")

        self.auto_mode = tk.BooleanVar(value=True)

        # Labels for sensor data
        self.accel_label = ttk.Label(self, text="Accelerometer: (X, Y, Z)")
        self.accel_label.pack(pady=5)

        self.gyro_label = ttk.Label(self, text="Gyroscope: (X, Y, Z)")
        self.gyro_label.pack(pady=5)

        self.speed_label = ttk.Label(self, text="Speed: 0.00 m/s")
        self.speed_label.pack(pady=5)

        self.angle_label = ttk.Label(self, text="Current Wing Angle: 0°")
        self.angle_label.pack(pady=5)

        # Manual wing control slider
        self.slider_label = ttk.Label(self, text="Manual Wing Angle:")
        self.slider_label.pack(pady=5)

        self.angle_slider = ttk.Scale(self, from_=0, to=180, orient="horizontal", command=self.manual_adjust)
        self.angle_slider.pack(pady=5)

        # Toggle for auto/manual mode
        self.auto_mode_check = ttk.Checkbutton(self, text="Automatic Mode", variable=self.auto_mode)
        self.auto_mode_check.pack(pady=10)

        # Logging status
        self.log_status = ttk.Label(self, text=f"Logging to {log_filename}")
        self.log_status.pack(pady=5)

        # Start the update loop
        self.update_loop()

    def manual_adjust(self, value):
        if not self.auto_mode.get():
            angle = float(value)
            set_servo_angle(angle)
            accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z = get_sensor_data()
            #speed = calculate_speed()
            self.update_sensor_labels(accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z, angle)
            log_data(datetime.now().strftime('%H:%M:%S.%f'), accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z, angle)

    # Active wing control logic
    def control_wing(self):
        accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z = get_sensor_data()
        #speed = calculate_speed()
        angle = 0

        # Adjust wing based on speed, acceleration, and turning
        if accel_x < -0.5:
            angle = 45  # Braking
        elif abs(gyro_y) > 30:
            angle = 30 if gyro_y > 0 else -30  # Cornering
       # elif speed > 5:
         #   angle = -10  # Flatten for high speeds
        else:
            angle = 0  # Neutral position

        set_servo_angle(angle)
        # Update GUI and log data
        self.update_sensor_labels(accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z, angle)
        log_data(datetime.now().strftime('%H:%M:%S.%f'), accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z, angle)

    def update_loop(self):
        if self.auto_mode.get():
           self.control_wing()
        self.after(50, self.update_loop)

    # Update sensor labels on the GUI
    def update_sensor_labels(self, accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z, angle):
        self.accel_label.config(text=f"Accelerometer: X={accel_x:.2f}, Y={accel_y:.2f}, Z={accel_z:.2f}")
        self.gyro_label.config(text=f"Gyroscope: X={gyro_x:.2f}, Y={gyro_y:.2f}, Z={gyro_z:.2f}")
        #self.speed_label.config(text=f"Speed: {speed:.2f} m/s")
        self.angle_label.config(text=f"Current Wing Angle: {angle:.1f}°")

# Main function
if __name__ == "__main__":
    try:
        init_gyro_accel()
        # Initialize log file with headers
        with open(log_filename, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["Timestamp", "Accel_X", "Accel_Y", "Accel_Z", "Gyro_X", "Gyro_Y", "Gyro_Z", "Speed_mps", "Wing_Angle"])

        app = WingControlGUI()
        app.mainloop()
    except KeyboardInterrupt:
        pass
    finally:
        #servo.stop()
        GPIO.cleanup()
