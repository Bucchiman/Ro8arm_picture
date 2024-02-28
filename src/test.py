from servo_motor import ServoMotor
from time import sleep





def get_args():
    import argparse
    base_parser = argparse.ArgumentParser(add_help=False)
    base_parser.add_argument('--m00_min', type=int, default=10, help="")
    base_parser.add_argument('--m00_max', type=int, default=120, help="")
    base_parser.add_argument('--m01', type=int, default=70, help="")
    base_parser.add_argument('--m02', type=int, default=90, help="")
    base_parser.add_argument('--m03', type=int, default=0, help="")
    base_parser.add_argument('--test', action='store_true')  # flag
    args = vars(base_parser.parse_args())
    return args




def test ():
    args = get_args()
    m00_min = args["m00_min"]
    m00_max = args["m00_max"]

    #if args["test"]:
    #    test

    servoMotors = []

    servoMotors.append(ServoMotor(Channel=0, ZeroOffset=0))
    servoMotors.append(ServoMotor(Channel=1, ZeroOffset=0))
    servoMotors.append(ServoMotor(Channel=2, ZeroOffset=0))
    servoMotors.append(ServoMotor(Channel=3, ZeroOffset=0))

    for motor00 in range(m00_min, m00_max):
        print(motor00, args["m01"], args["m02"], args["m03"])

        servoMotors[0].setAngle(motor00)
        servoMotors[1].setAngle(args["m01"])
        servoMotors[2].setAngle(args["m02"])
        servoMotors[3].setAngle(args["m03"])
        sleep(0.5)

    #servoMotors[0].cleanup()
    #servoMotors[1].cleanup()
    #servoMotors[2].cleanup()
    #servoMotors[3].cleanup()



def main ():
    test()


if __name__ == "__main__":
    main()
