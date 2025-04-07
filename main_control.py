#!/usr/bin/env python3
import time
import numpy as np
import math
import tkinter as tk
from tkinter import ttk
import csv
from datetime import datetime
import argparse
import RPi.GPIO as GPIO
import smbus2
import sys
import os
sys.path.append(os.path.expanduser('~/active-aero/lib/python3.11/site-packages'))
from adafruit_servokit import ServoKit

# PWM servo driver setup
kit = ServoKit(channels=8)

# MPU6050 setup
MPU6050_ADDR = 0x68
bus = smbus2.SMBus(1)

# Logging setup
LOG_DIR = os.path.expanduser('~/active-aero/logs/')
log_filename = os.path.join(LOG_DIR, f"wing_data_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
logging_active = False

# Initialize MPU6050
def init_gyro_accel():
    try:
        bus.write_byte_data(0x68, 0x6B, 0)  # try 0x68
        MPU6050_ADDR = 0x68
    except OSError:
        bus.write_byte_data(0x69, 0x6B, 0)  # try 0x69
        MPU6050_ADDR = 0x69

    bus.write_byte_data(MPU6050_ADDR, 0x1C, 0x10)  # change the AFS_SEL to 2
    print("MPU6050_ADDR", hex(MPU6050_ADDR))
    
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
    # for AFS_SEL = 0
    # accel_x = read_raw_data(0x3B) / 16384.0
    # accel_y = read_raw_data(0x3D) / 16384.0
    # accel_z = read_raw_data(0x3F) / 16384.0

    # for AFS_SEL = 2 
    accel_x = read_raw_data(0x3B) / 4096.0
    accel_y = read_raw_data(0x3D) / 4096.0
    accel_z = read_raw_data(0x3F) / 4096.0

    gyro_x = read_raw_data(0x43) / 131.0
    gyro_y = read_raw_data(0x45) / 131.0
    gyro_z = read_raw_data(0x47) / 131.0

    return accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z

# Control both servos of the wing angle
def set_servo_angle(angle1,angle2,angle3,angle4):
    try:
        kit.servo[0].angle = 180 - angle1
        kit.servo[1].angle = angle2
        kit.servo[2].angle = 180 - angle3
        kit.servo[3].angle = angle4
        return angle
    except Exception as e: print("Error setting servo angle:", e)

# control the angle of servo0 
def set_servo_0(angle):
    try:
        kit.servo[0].angle = 180 - angle
        return angle
    except Exception as e: print("Error setting servo0 angle:", e)

# control the angle of servo1
def set_servo_1(angle):
    try:
        kit.servo[1].angle = angle
        return angle
    except Exception as e: print("Error setting servo1 angle:", e)

# Log data to CSV
def log_data(timestamp, accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z, wing_angle):
    if logging_active:
        print("Logging to", log_filename)
        
        # check if the file exists
        file_exists = os.path.isfile(log_filename)

        with open(log_filename, mode='a', newline='') as file:
            writer = csv.writer(file)
            if not file_exists:
                writer.writerow(["timestamp", "accel_x", "accel_y", "accel_z", "gyro_x", "gyro_y", "gyro_z", "wing_angle"])
        
            writer.writerow([timestamp, accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z, wing_angle])

# Active wing control logic
def control_wing(curr_angle, accel_x_offset, accel_y_offset, accel_z_offset, gyro_x_offset, gyro_y_offset, gyro_z_offset):
    accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z = get_sensor_data()
    accel_x = accel_x - accel_x_offset
    accel_y = accel_y - accel_y_offset
    accel_z = accel_z - accel_z_offset
    gyro_x = gyro_x - gyro_x_offset
    gyro_y = accel_y - gyro_y_offset
    gyro_z = gyro_z - gyro_z_offset
    # print("ACCELERATION")
    # print("x " , accel_x)
    # print("y " , accel_y)
    # print("z " , accel_z)

    # print("\nGYROSCOPE")
    # print("x " , gyro_x)
    # print("y " , gyro_y)
    # print("z " , gyro_z)

    angle = 0

    # Adjust wing based on speed, acceleration, and turning
    if gyro_x < -.5:
        angle = 180  # Braking
#        print("braking: set angle to 180")
    #elif abs(gyro_y) > 30:
    #    angle = 30 if gyro_y > 0 else -30  # Cornering
    #elif speed > 5:
    #    angle = 0  # Flatten for high speeds
    else:
        angle = 90  # Neutral position
#        print("neutral position: set angle to 90")

    if curr_angle != angle:
#        print("no change in curr_angle ", curr_angle)
        new_angle = set_servo_angle(angle)
        log_data(datetime.now().strftime('%H:%M:%S.%f'), accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z, angle)
        return new_angle
    else:
        log_data(datetime.now().strftime('%H:%M:%S.%f'), accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z, angle)
        return curr_angle


# Read calibration parameters from CSV
def read_cal_params(filename):
    cal_offsets = np.array([ [], [], [],
                             [], [], [] ], dtype=object)  # cal vector
    with open(filename, mode='r') as file:
        reader = csv.reader(file)
        iter_ii = 0
        for row in reader:
            if len(row) > 2:
                row_vals = [float(ii) for ii in row[int((len(row)/2) + 1):]]
                cal_offsets[iter_ii] = row_vals
            else:
                cal_offsets[iter_ii] = float(row[1])
            iter_ii += 1
    return cal_offsets

# tkinter GUI Setup
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

def bootcal():
    print("calibrating...")
    CalSamples = 100
    accel_x_cal = [j for j in range(CalSamples)] 
    accel_y_cal = [j for j in range(CalSamples)] 
    accel_z_cal = [j for j in range(CalSamples)] 
    gyro_x_cal = [j for j in range(CalSamples)] 
    gyro_y_cal = [j for j in range(CalSamples)] 
    gyro_z_cal = [j for j in range(CalSamples)] 
    for i in range(CalSamples):
        accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z = get_sensor_data()
        accel_x_cal[i] = accel_x
        accel_y_cal[i] = accel_y
        accel_z_cal[i] = accel_z
        gyro_x_cal[i] = gyro_x
        gyro_y_cal[i] = gyro_y
        gyro_z_cal[i] = gyro_z
        time.sleep(.1)
    accel_x_offset = sum(accel_x_cal)/CalSamples
    accel_y_offset = sum(accel_y_cal)/CalSamples
    accel_z_offset = sum(accel_z_cal)/CalSamples
    gyro_x_offset = sum(gyro_x_cal)/CalSamples
    gyro_y_offset = sum(gyro_y_cal)/CalSamples
    gyro_z_offset = sum(gyro_z_cal)/CalSamples
    print(accel_x_offset)
    print(accel_y_offset)
    print(accel_z_offset)
    print(gyro_x_offset)
    print(gyro_y_offset)
    print(gyro_z_offset)
    print('Calibration Complete')
    time.sleep(1)
    return accel_x_offset,accel_y_offset,accel_z_offset,gyro_x_offset,gyro_y_offset,gyro_z_offset
    
def PriorityDefine(accel_x_offset,accel_y_offset):
    accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z = get_sensor_data()
    accel_x = accel_x - accel_x_offset
    accel_y = (accel_y - accel_y_offset)*1
    if abs(accel_x) > abs(accel_y):
        priority = 1 # forward accel priority
        return accel_x,accel_y,priority
    elif abs(accel_x) < abs(accel_y):
        priority = 0
        return accel_x,accel_y,priority
    
def WingMove(accel_x,accel_y,priority):
    print("implement me!")
    match priority:
    	case 1:
    	# Make Accel Force Graph, log data for Min-Max and develop function
    		WingAngle = -72*ceiling(accel_x)
    		if WingAngle >= 180
    			WingAngle = 180
    		else if WingAngle <= 0
    			WingAngle = 0
    		
    		if accel_x >= 1.5
    			HoodAngle = 180
    		else
    			HoodAngle = 0
    			
    		set_servo_angle(WingAngle,WingAngle,HoodAngle,HoodAngle)
    		Angle1 = WingAngle
    		Angle2 = WingAngle
    		Angle3 = HoodAngle
    		Angle4 = HoodAngle
    	case 2:
    	# Make Accel Force Graph, log data for Min-Max and develop function
    		WingAngleY = 72*ceiling(accel_x)
    		if WingAngleY > 0
    			if WingAngleY >= 180
    				WingAngleY = 180
    			else if WingAngleY <= 0
    				WingAngleY = 0
				WingAngleY2 = 0
    		else if WingAngleY < 0
    			if WingAngleY2 >= 180
    				WingAngleY2 = 180
    			else if WingAngle <= 0
    				WingAngleY2 = 0
    			WingAngleY = 0
    			HoodAngle = 0
    		set_servo_angle(WingAngleY,WingAngleY2,HoodAngle,HoodAngle)
    		Angle1 = WingAngleY
    		Angle2 = WingAngleY2
    		Angle3 = HoodAngle
    		Angle4 = HoodAngle
    		
	return Angle1,Angle2,Angle3,Angle4	

    
# Main function
if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser(description="Active Aerodynamics Control")
        parser.add_argument("-l", "--log", action="store_true", help="Enable logging to CSV")
        parser.add_argument("-g", "--gui", action="store_true", help="Enable GUI")
        parser.add_argument("-c", "--calibrate", action="store_true", help="Enable calibration mode")        
        args = parser.parse_args()
        init_gyro_accel()
        accel_x_offset = 0
        accel_y_offset = 0
        accel_z_offset = 0
        gyro_x_offset = 0
        gyro_y_offset = 0
        gyro_z_offset = 0
        
        if args.log:
            print("Logging enabled")
            logging_active = True
        
        if args.calibrate:
            print("Calibrating...")
            accel_x_offset,accel_y_offset,accel_z_offset,gyro_x_offset,gyro_y_offset,gyro_z_offset = bootcal()
        
        if args.gui:
            app = WingControlGUI()
            app.mainloop()
        else:
            curr_angle = 0
            testval = 0
            while True:
                accel_x, accely, priority = PriorityDefine(accel_x_offset, accel_y_offset)
                # = control_wing(curr_angle,accel_x_offset,accel_y_offset,accel_z_offset,gyro_x_offset,gyro_y_offset,gyro_z_offset)
                Angle1,Angle2,Angle3,Angle4 = WingMove(accel_x,accel_y,priority)
                curr_angle = new_angle

    except KeyboardInterrupt:
        pass
    finally:
        print("\n\nstopping execution\n\n")
        set_servo_angle(180)
        GPIO.cleanup()
