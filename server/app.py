#!/usr/bin/env python3
import sys
sys.path.append('/home/pi/active-aero/lib/python3.11/site-packages')
import time
import os
import csv
import threading
import random
from flask import Flask, render_template, render_template_string, request, jsonify, send_from_directory
import RPi.GPIO as GPIO
import smbus2
from adafruit_servokit import ServoKit
from datetime import datetime

sys.path.append('/home/pi/active-aero/')
import main_control as Aero

# Initialize the sensor hardware
Aero.init_gyro_accel()

# Global variable to hold the latest sensor data

LOG_DIR = '/home/pi/active-aero/logs'

latest_sensor_data = {}
imu_data = {
    "accel_x": 0,
    "accel_y": 0,
    "accel_z": 0,
    "gyro_x": 0,
    "gyro_y": 0,
    "gyro_z": 0
}

accel_x_offset = 0
accel_y_offset = 0
accel_z_offset = 0
gyro_x_offset = 0
gyro_y_offset = 0
gyro_z_offset = 0

auto_state = {
    "auto_mode": False,
    "thread": None,
    "stop_flag": threading.Event()
}

# ---- define some functions ---- 
# backround thread that continuously reads sensor data
def sensor_update_loop():
    global latest_sensor_data
    while True:
        # latest_sensor_data = Aero.get_sensor_data()
        imu_data["accel_x"] = random.randint(-16000, 16000)
        imu_data["accel_y"] = random.randint(-16000, 16000)
        imu_data["accel_z"] = random.randint(-16000, 16000)
        imu_data["gyro_x"] = random.randint(-250, 250)
        imu_data["gyro_y"] = random.randint(-250, 250)
        imu_data["gyro_z"] = random.randint(-250, 250)
        latest_sensor_data = imu_data
        time.sleep(1)  # update every second

def auto_mode_loop(flag):
    new_angle = 0
    curr_angle = 0
    while not flag.is_set():
        if auto_state['auto_mode']:
            accel_x,accely,priority = Aero.PriorityDefine(accel_x_offset,accel_y_offset)
            new_angle = Aero.control_wing(curr_angle, accel_x_offset, accel_y_offset, accel_z_offset, gyro_x_offset, gyro_y_offset, gyro_z_offset)
            print("setting wing to ", new_angle, "°")
            time.sleep(.5)
            curr_angle = new_angle

def start_auto_mode_thread():
    if auto_state['thread'] is None or not auto_state['thread'].is_alive():
        auto_state['stop_flag'].clear()
        auto_state['thread'] = threading.Thread(target=auto_mode_loop, args=(auto_state['stop_flag'],), daemon=True)
        auto_state['thread'].start()

def stop_auto_mode_thread():
    auto_state['stop_flag'].set()
    auto_state['thread'] = None

# ---- start flask setup ----
app = Flask(__name__)

# ---- set the routes for http requests ----
# main page
@app.route("/")
def index():
    return render_template("index.html")

# set either auto or manual mode
@app.route('/set_mode', methods=['POST'])
def set_mode():
    data = request.form.get("mode")
    if data == "auto":
        auto_state['auto_mode'] = True
        start_auto_mode_thread()
    elif data == "manual":
        auto_state['auto_mode'] = False
        stop_auto_mode_thread()
    else:
        return jsonify(success=False, message="Invalid mode"), 400
    return jsonify(success=True, message=f"Mode set to {'Auto' if auto_state['auto_mode'] else 'Manual'}")

# control logging state
@app.route('/set_logging', methods=['POST'])
def set_logging():
    mode = request.form.get("logging")
    if mode == "on":
        Aero.logging_active = True
        print("Logging ENABLED")
    elif mode == "off":
        Aero.logging_active = False
        print("Logging DISABLED")
    else:
        return jsonify(success=False, message="Invalid logging state"), 400

    return jsonify(success=True)

# get the latest sensor data
@app.route("/sensor", methods=["GET"])
def sensor():
    return jsonify(latest_sensor_data)

# list the log files
@app.route('/logs')
def list_logs():
    files = [f for f in os.listdir(LOG_DIR) if f.endswith('.csv')]
    return jsonify(files)

# download a log file
@app.route('/logs/download/<filename>')
def get_log(filename):
    return send_from_directory(LOG_DIR, filename)

# view the contents of a log file
@app.route('/logs/view/<filename>')
def view_log_table(filename):
    file = os.path.join(LOG_DIR, filename)
    try:
        with open(file, 'r') as f:
            reader = csv.reader(f)
            rows = list(reader)
    except FileNotFoundError:
        return "Log file not found.", 404

    # Make a simple HTML table
    table_html = "<table border='1'>"
    for i, row in enumerate(rows):
        table_html += "<tr>" + "".join(
            f"<th>{cell}</th>" if i == 0 else f"<td>{cell}</td>"
            for cell in row
        ) + "</tr>"
    table_html += "</table>"

    return render_template_string(f"""
        <html>
        <head><title>Viewing {filename}</title></head>
        <body>
          <h2>Contents of {filename}</h2>
          {table_html}
        </body>
        </html>
    """)

# set the servo angle in maual mode
@app.route("/set_both_servos", methods=["POST"])
def servo():
    try:
        angle = float(request.form.get("angle"))
        Aero.set_servo_angle(angle)
        return jsonify({"status": "success", "angle": angle})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/set_servo_0', methods=['POST'])
def set_servo_1():
    angle = request.form.get("angle")
    if angle is not None:
        # Here, you should call your servo control function
        Aero.set_servo_0(int(angle))
        return jsonify(success=True)
    else:
        return jsonify(success=False, message="Invalid angle"), 400

@app.route('/set_servo_1', methods=['POST'])
def set_servo_2():
    angle = request.form.get("angle")
    if angle is not None:
        # Here, you should call your servo control function
        Aero.set_servo_1(int(angle))
        return jsonify(success=True)
    else:
        return jsonify(success=False, message="Invalid angle"), 400


# calibrate the MPU6050
@app.route("/calibrate", methods=["POST"])
def calibrate():
    try:
        accel_x_offset, accel_y_offset, accel_z_offset, gyro_x_offset, gyro_y_offset, gyro_z_offset = Aero.bootcal()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

# ---- end flask setup ----

# in main, start the sensor update thread and run the Flask app
if __name__ == "__main__":
    sensor_thread = threading.Thread(target=sensor_update_loop)
    sensor_thread.daemon = True
    sensor_thread.start()
    try:
        app.run(host="0.0.0.0", port=5000, debug=True)
    finally:
        GPIO.cleanup()
