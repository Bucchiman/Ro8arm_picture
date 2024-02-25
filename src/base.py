from servo_motor import ServoMotor
from time import sleep


def set_pos_xx ():

    servoMotors = []

    servoMotors.append(ServoMotor(Channel=0, ZeroOffset=0))
    servoMotors.append(ServoMotor(Channel=1, ZeroOffset=0))
    servoMotors.append(ServoMotor(Channel=2, ZeroOffset=0))
    servoMotors.append(ServoMotor(Channel=3, ZeroOffset=0))

    min_angle = 20
    max_angle = 30

    servoMotors[0].setAngle(0)
    servoMotors[1].setAngle(-20)
    servoMotors[2].setAngle(0)
    servoMotors[3].setAngle(0)
    sleep(5)

    servoMotors[0].cleanup()
    servoMotors[1].cleanup()
    servoMotors[2].cleanup()
    servoMotors[3].cleanup()



def main ():
    set_pos_xx()


if __name__ == "__main__":
    main()
