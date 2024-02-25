from servo_motor import ServoMotor
from time import sleep

def stop ():
    servoMotors = []

    servoMotors.append(ServoMotor(Channel=0, ZeroOffset=0))
    servoMotors.append(ServoMotor(Channel=1, ZeroOffset=0))
    servoMotors.append(ServoMotor(Channel=2, ZeroOffset=0))
    servoMotors.append(ServoMotor(Channel=3, ZeroOffset=0))

    servoMotors[0].setAngle(52)
    servoMotors[1].setAngle(80)
    servoMotors[2].setAngle(70)
    servoMotors[3].setAngle(0)
    sleep(0.5)


if __name__ == "__main__":
    stop()
