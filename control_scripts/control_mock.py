import unittest
from unittest.mock import MagicMock, patch
import time
import smbus2
import RPi.GPIO as GPIO
from datetime import datetime


# Mocking the RPi.GPIO
GPIO.setmode = MagicMock()
GPIO.setup = MagicMock()
GPIO.PWM = MagicMock(return_value=MagicMock(start=MagicMock(), ChangeDutyCycle=MagicMock()))
GPIO.output = MagicMock()
GPIO.cleanup = MagicMock()

# Mocking the smbus2
mock_bus = MagicMock(spec=smbus2.SMBus)
mock_bus.read_byte_data.return_value = 0  # Mocking sensor reads to return 0
mock_bus.write_byte_data = MagicMock()  # Mocking the write function

# Mocking the time-related functions
time.time = MagicMock(return_value=1234567890)  # Fake time for testing
time.sleep = MagicMock()  # No actual sleep

# Your test function
def test_mpu_control():
    with patch('smbus2.SMBus', return_value=mock_bus), patch('RPi.GPIO', GPIO):
        # Setup the mock bus
        bus = smbus2.SMBus(1)

        # Mock the actual sensor data
        mock_bus.read_byte_data.return_value = 100  # Simulate a raw reading for the sensor

        # Initialize the MPU6050
        def init_gyro_accel():
            bus.write_byte_data(MPU6050_ADDR, 0x6B, 0)  # Wake up the MPU6050

        # Get mocked data
        def get_sensor_data():
            accel_x = 1.0  # Mocked value
            accel_y = 0.5  # Mocked value
            accel_z = 0.0  # Mocked value
            gyro_x = 0.1  # Mocked value
            gyro_y = 0.2  # Mocked value
            gyro_z = 0.3  # Mocked value
            return accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z

        # Mock control logic
        def control_wing(curr_angle):
            accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z = get_sensor_data()
            speed = 2.0  # Mocked speed
            angle = 90  # Mocked angle

            if accel_x < -0.5:
                angle = 180  # Braking
            else:
                angle = 90  # Neutral position

            if curr_angle != angle:
                return angle
            return curr_angle

        # Test control logic
        curr_angle = 0
        new_angle = control_wing(curr_angle)

        # Assertions
        assert new_angle == 90  # Should be 90 based on mock accel_x and other values

        # Verify that the mock functions were called as expected
        GPIO.PWM.assert_called_with(18, 50)
        GPIO.output.assert_called()  # Check if GPIO.output was called
        mock_bus.write_byte_data.assert_called_with(MPU6050_ADDR, 0x6B, 0)  # Check if wakeup was called

if __name__ == "__main__":
    unittest.main()
