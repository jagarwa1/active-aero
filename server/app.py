#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.expanduser('~/active-aero/'))
sys.path.append(os.path.expanduser('~/active-aero/lib/python3.11/site-packages'))
import main_control as Aero
import time
import csv
import threading
import random
from flask import Flask, render_template, render_template_string, request, jsonify, send_from_directory
from datetime import datetime

# Initialize the sensor hardware
Aero.init_gyro_accel()

# set log directory
LOG_DIR = os.path.expanduser('~/active-aero/logs/')

# set the global sensor data
latest_sensor_data = {
    "accel_x": 0,
    "accel_y": 0,
    "accel_z": 0,
    "gyro_x": 0,
    "gyro_y": 0,
    "gyro_z": 0
}

calibration_status = {'status': False}
accel_x_offset = 0
accel_y_offset = 0
accel_z_offset = 0
gyro_x_offset = 0
gyro_y_offset = 0
gyro_z_offset = 0

curr_angle = 0
Angle1 = 0
Angle2 = 0
Angle3 = 0
Angle4 = 0

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
        ax, ay, az, gx, gy, gz = Aero.get_sensor_data()
        latest_sensor_data = {
            "accel_x": ax - accel_x_offset,
            "accel_y": ay - accel_y_offset,
            "accel_z": az - accel_z_offset,
            "gyro_x": gx - gyro_x_offset,
            "gyro_y": gy - gyro_y_offset,
            "gyro_z": gz - gyro_z_offset
        }
        if Aero.logging_active and not auto_state["auto_mode"]:
            Aero.log_data(datetime.now().strftime('%H:%M:%S.%f'), 
            latest_sensor_data['accel_x'], 
            latest_sensor_data['accel_y'], 
            latest_sensor_data['accel_z'], 
            latest_sensor_data['gyro_x'], 
            latest_sensor_data['gyro_y'], 
            latest_sensor_data['gyro_z'], 
            Angle1,
            Angle2,
            Angle3,
            Angle4)
        

# background thread for auto control
def auto_mode_loop(flag):
    global accel_x_offset, accel_y_offset, accel_z_offset, gyro_x_offset, gyro_y_offset, gyro_z_offset
    while not flag.is_set():
        if auto_state['auto_mode']:
            accel_x, accel_y, priority = Aero.PriorityDefine(accel_x_offset, accel_y_offset)
            Angle1, Angle2, Angle3, Angle4 = Aero.WingMove(accel_x, accel_y, priority)
            # print("angle1: ", Angle1)
            # print("angle2: ", Angle2)
            # print("angle3: ", Angle3)
            # print("angle4: ", Angle4)
            if Aero.logging_active:
                Aero.log_data(datetime.now().strftime('%H:%M:%S.%f'), 
                latest_sensor_data['accel_x'], 
                latest_sensor_data['accel_y'], 
                latest_sensor_data['accel_z'], 
                latest_sensor_data['gyro_x'], 
                latest_sensor_data['gyro_y'], 
                latest_sensor_data['gyro_z'], 
                Angle1,
                Angle2,
                Angle3,
                Angle4)

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
        if Aero.logging_active: # name the file auto mode
            Aero.log_filename = os.path.join(LOG_DIR, f"auto_mode_data_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    elif data == "manual":
        auto_state['auto_mode'] = False
        stop_auto_mode_thread()
        if Aero.logging_active: # name the file manual mode
            Aero.log_filename = os.path.join(LOG_DIR, f"manual_mode_data_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    else:
        return jsonify(success=False, message="Invalid mode"), 400
    return jsonify(success=True, message=f"Mode set to {'Auto' if auto_state['auto_mode'] else 'Manual'}")

# control logging state
@app.route('/set_logging', methods=['POST'])
def set_logging():
    mode = request.form.get("logging")
    if mode == "on":
        Aero.logging_active = True
        
        if auto_state["auto_mode"]: # name the file in acccordance to its mode
            Aero.log_filename = os.path.join(LOG_DIR, f"auto_mode_data_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        else:
            Aero.log_filename = os.path.join(LOG_DIR, f"manual_mode_data_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")

        print("------Logging ENABLED------")
    elif mode == "off":
        Aero.logging_active = False
        print("------Logging DISABLED-----")
    else:
        return jsonify(success=False, message="Invalid logging state"), 400

    return jsonify(success=True)

# get the latest sensor data
@app.route("/sensor", methods=["GET"])
def sensor():
    if Aero.logging_active and not auto_state["auto_mode"]:
        global latest_sensor_data
        Aero.log_data(
            datetime.now().strftime('%H:%M:%S.%f'),
            latest_sensor_data.get("accel_x"),
            latest_sensor_data.get("accel_y"),
            latest_sensor_data.get("accel_z"),
            latest_sensor_data.get("gyro_x"),
            latest_sensor_data.get("gyro_y"),
            latest_sensor_data.get("gyro_z"),
            Angle1,
            Angle2,
            Angle3,
            Angle4
        )
    
    data_with_angles = {
            "accel_x": latest_sensor_data['accel_x'], 
            "accel_y": latest_sensor_data['accel_y'], 
            "accel_z": latest_sensor_data['accel_z'], 
            "gyro_x": latest_sensor_data['gyro_x'], 
            "gyro_y": latest_sensor_data['gyro_y'], 
            "gyro_z": latest_sensor_data['gyro_z'], 
            "Angle1": Angle1,
            "Angle2": Angle2,
            "Angle3": Angle3,
            "Angle4": Angle4
    }
    return jsonify(data_with_angles)

# list the log files
@app.route('/logs')
def list_logs():
    files = [f for f in os.listdir(LOG_DIR) if f.endswith('.csv')]
    files.sort() # sort by name
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
        <a href="/logs/download/{filename}" download>
            <button style="margin-bottom: 20px;">⬇ Download CSV</button>
        </a>
        {table_html}
        </body>
        </html>
    """)

# set the servo angle in maual mode
@app.route("/set_all_servos", methods=['POST'])
def servo():
    try:
        angle = float(request.form.get("angle"))
        Aero.set_servo_angle(angle, angle, angle, angle)
        return jsonify({"status": "success", "angle": angle})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route("/set_wing_servos", methods=['POST'])
def servo_wing():
    try:
        angle = float(request.form.get("angle"))
        Aero.set_wing_angle(angle, angle)
        return jsonify({"status": "success", "angle": angle})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route("/set_roof_servos", methods=['POST'])
def servo_roof():
    try:
        angle = float(request.form.get("angle"))
        Aero.set_roof_angle(angle, angle)
        return jsonify({"status": "success", "angle": angle})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/set_servo_0', methods=['POST'])
def set_servo_0():
    angle = request.form.get("angle")
    if angle is not None:
        Aero.set_servo_0(int(angle))
        return jsonify(success=True)
    else:
        return jsonify(success=False, message="Invalid angle"), 400

@app.route('/set_servo_1', methods=['POST'])
def set_servo_1():
    angle = request.form.get("angle")
    if angle is not None:
        Aero.set_servo_1(int(angle))
        return jsonify(success=True)
    else:
        return jsonify(success=False, message="Invalid angle"), 400

@app.route('/set_servo_2', methods=['POST'])
def set_servo_2():
    angle = request.form.get("angle")
    if angle is not None:
        Aero.set_servo_2(int(angle))
        return jsonify(success=True)
    else:
        return jsonify(success=False, message="Invalid angle"), 400

@app.route('/set_servo_3', methods=['POST'])
def set_servo_3():
    angle = request.form.get("angle")
    if angle is not None:
        Aero.set_servo_3(int(angle))
        return jsonify(success=True)
    else:
        return jsonify(success=False, message="Invalid angle"), 400


# calibrate the MPU6050
# as of now it calibrates on each page load, not on a restart of the app
@app.route("/calibrate", methods=['POST'])
def calibrate():
    global accel_x_offset, accel_y_offset, accel_z_offset, gyro_x_offset, gyro_y_offset, gyro_z_offset
    try:
        accel_x_offset, accel_y_offset, accel_z_offset, gyro_x_offset, gyro_y_offset, gyro_z_offset = Aero.bootcal()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route("/calibration_status", methods=['GET'])
def calibration_status():
    global calibration_status
    return jsonify(calibration_status)

# ---- end flask setup ----

# in main, start the sensor update thread and run the Flask app
if __name__ == "__main__":
    sensor_thread = threading.Thread(target=sensor_update_loop)
    sensor_thread.daemon = True
    sensor_thread.start()
    try:
        app.run(host="0.0.0.0", port=5000, debug=True)
    finally:
        print("exiting app")
