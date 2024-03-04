from servo_motor import ServoMotor
from fuji import Fuji


def line_base(position: int):
    pass


def main():
    servoMotors = []

    servoMotors.append(ServoMotor(Channel=0, ZeroOffset=0))
    servoMotors.append(ServoMotor(Channel=1, ZeroOffset=0))
    servoMotors.append(ServoMotor(Channel=2, ZeroOffset=0))
    servoMotors.append(ServoMotor(Channel=3, ZeroOffset=0))
    fuji = Fuji(servoMotors)
    #line_of_mountain(servoMotors)
    #snow(servoMotors)

    fuji.internal_mountain()


if __name__ == "__main__":
    main()
