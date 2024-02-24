from servo_motor import ServoMotor
from time import sleep



def motor0():
    motor = ServoMotor(Channel=0, ZeroOffset=0)
    motor.setAngle(0)
    motor.cleanup()

def motor1():
    motor = ServoMotor(Channel=5, ZeroOffset=0)
    motor.setAngle(0)
    motor.cleanup()

def motor2():
    motor = ServoMotor(Channel=2, ZeroOffset=0)
    motor.setAngle(0)
    motor.cleanup()

def motor3():
    motor = ServoMotor(Channel=3, ZeroOffset=0)
    motor.setAngle(0)
    motor.cleanup()


def motor4():
    """
    test motor
    """
    motor = ServoMotor(Channel=4, ZeroOffset=0)
    motor.setAngle(0)
    motor.cleanup()




def main():
    #motor0()
    #motor1()
    motor2()
    #motor3()
    pass


if __name__ == "__main__":
    main()
