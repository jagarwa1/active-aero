import sys
sys.path.append('/home/benchh1/active-aero/lib/python3.11/site-packages')
from flask import Flask, render_template
import datetime

# Initialize variables
gyro_x, gyro_y, gyro_z = 0.0, 0.0, 0.0
accel_x, accel_y, accel_z = 0.0, 0.0, 0.0
angle = 0.0

app = Flask(__name__)

# Set up routes for Flask
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/set_manual_angle', methods=['POST'])
def set_manual_angle():
    global angle
    angle = float(request.form['manual_angle'])
    return 'Manual wing angle set to: {}'.format(angle)

@app.route('/toggle_auto_mode', methods=['POST'])
def toggle_auto_mode():
    global auto_mode
    if request.form['auto_mode'] == 'on':
        auto_mode = True
    else:
        auto_mode = False
    return 'Auto mode toggled'

@app.route('/update_sensor_data', methods=['GET'])
def update_sensor_data():
    # Update sensor data from sensors (accelerometer, gyroscope)
    global gyro_x, gyro_y, gyro_z, accel_x, accel_y, accel_z
    # Replace this with actual sensor data acquisition code
    gyro_x = 10.0
    gyro_y = 20.0
    gyro_z = 30.0
    accel_x = 40.0
    accel_y = 50.0
    accel_z = 60.0
    return 'Sensor data updated: gyro={}'.format(gyro_x)

@app.route('/update_wing_angle', methods=['GET'])
def update_wing_angle():
    global angle
    # Update wing angle based on sensor data
    if auto_mode:
        # Replace this with actual control logic code
        angle = 45
    return 'Wing angle updated to: {}'.format(angle)

@app.route('/log_data', methods=['POST'])
def log_data():
    global gyro_x, gyro_y, gyro_z, accel_x, accel_y, accel_z, angle
    # Log sensor data and wing angle to file
    with open('log.txt', 'a') as f:
        f.write('Gyroscope: X={:.2f}, Y={:.2f}, Z={:.2f}\n'.format(gyro_x, gyro_y, gyro_z))
        f.write('Accelerometer: X={:.2f}, Y={:.2f}, Z={:.2f}\n'.format(accel_x, accel_y, accel_z))
        f.write('Wing Angle: {:.1f}°\n'.format(angle))
    return 'Data logged'

# Run the application
if __name__ == '__main__':
    app.run(debug=True)
