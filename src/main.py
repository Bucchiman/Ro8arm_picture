from servo_motor import ServoMotor
from time import sleep

servoMotors = []

servoMotors.append(ServoMotor(Channel=0, ZeroOffset=0))
servoMotors.append(ServoMotor(Channel=1, ZeroOffset=0))
servoMotors.append(ServoMotor(Channel=2, ZeroOffset=0))
servoMotors.append(ServoMotor(Channel=3, ZeroOffset=0))

# stable
# servoMotors[0].setAngle(10)
# servoMotors[1].setAngle(-20)
# servoMotors[2].setAngle(25)
# servoMotors[3].setAngle(0)


for i in range(180):
    servoMotors[0].setAngle(i)
    servoMotors[1].setAngle(-20)
    servoMotors[2].setAngle(25)
    servoMotors[3].setAngle(0)

    sleep(1)

servoMotors[0].cleanup()
servoMotors[1].cleanup()
servoMotors[2].cleanup()
servoMotors[3].cleanup()

