from servo_motor import ServoMotor
from time import sleep

# Define the channel and zero offset for your servo motor
channel = 0
zero_offset = 0

# Create an instance of the ServoMotor class
servo_motor = ServoMotor(channel, zero_offset)

# Set the angle of the servo motor
servo_motor.set_angle(100)

# Cleanup the servo motor
servo_motor.cleanup()
