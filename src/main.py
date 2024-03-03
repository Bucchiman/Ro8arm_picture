from random import randint
from servo_motor import ServoMotor
from time import sleep


def line_base(position: int):
    pass

def sky():
    num_line = randint(-2, 16)
    position = randint(10, 150)



def line_of_mountain (servoMotors):
    track_lst = [[3, 81, 73, 0],
                 [4, 78, 75, 0],
                 [6, 77, 79, 5],
                 [9, 77, 79, 0],
                 [10, 75, 81, 0],
                 [11, 75, 81, 0],

                 [14, 74, 83, 0],
                 [15, 74, 83, 0],
                 [16, 74, 83, 0],
                 [17, 74, 83, 0],
                 [18, 74, 83, 0],
                 [19, 74, 83, 0],
                 [20, 74, 83, 0],
                 [21, 74, 83, 0],
                 [22, 74, 83, 0],
                 [23, 74, 83, 0],
                 [24, 74, 83, 0],
                 [25, 74, 83, 0],
                 [26, 74, 83, 0],
                 [27, 74, 83, 0],
                 [28, 74, 83, 0],
                 [29, 74, 83, 0],
                 [30, 74, 83, 0],
                 [31, 74, 83, 3],
                 [32, 74, 83, 4],
#                 [33, 74, 83, 6],
                 [34, 74, 83, 6],
                 [35, 74, 83, 6],
                 [38, 78, 79, 4],
                 [39, 78, 79, 4],
                 [40, 78, 79, 4],
                 [42, 80, 75, 0],
                 [44, 80, 75, 0],
                 [45, 80, 75, 2],
                 [47, 80, 75, 10],
                 [48, 80, 75, 10],
                 [49, 80, 75, 10],
                 [50, 80, 75, 12],
                 [51, 81, 75, 14],
                 [53, 81, 75, 17],

                 [55, 81, 75, 21],
                 [57, 81, 75, 25],
                 [59, 81, 75, 25],
                 [61, 81, 75, 25],
                 [63, 81, 75, 25],

                 [65, 81, 75, 28],
                 [67, 81, 75, 28],
                 [68, 81, 75, 28],

                 [70, 81, 75, 28],
                 [72, 81, 75, 25],
                 [74, 81, 75, 23],
                 [75, 81, 75, 23],
                 [76, 81, 75, 16],
                 [77, 81, 75, 13],
                 [78, 81, 75, 13],
                 [79, 82, 75, 12],
                 [80, 82, 75, 11],
                 [81, 82, 75, 11],
                 [82, 82, 75, 11],
                 [83, 82, 75, 11],
                 [84, 82, 75, 11],
                 [85, 82, 75, 11],
                 [86, 82, 75, 11],
                 [87, 82, 75, 11],
                 [88, 82, 75, 11],
                 [89, 82, 75, 11],

                 [90, 82, 75, 11],
                 [91, 82, 75, 11],
                 [92, 82, 75, 13],
                 [93, 82, 75, 15],
                 [94, 82, 75, 16],
                 [95, 82, 75, 18],
                 [96, 82, 75, 18],
                 [97, 82, 75, 20],
                 [98, 82, 75, 20],
                 [100, 82, 75, 23],
                 [101, 82, 75, 25],
                 [102, 82, 75, 25],

                ]
    for track_path in track_lst:
        print(track_path)
        servoMotors[0].setAngle(track_path[0])
        servoMotors[1].setAngle(track_path[1])
        servoMotors[2].setAngle(track_path[2])
        servoMotors[3].setAngle(track_path[3])
        sleep(0.5)


def main():
    servoMotors = []

    servoMotors.append(ServoMotor(Channel=0, ZeroOffset=0))
    servoMotors.append(ServoMotor(Channel=1, ZeroOffset=0))
    servoMotors.append(ServoMotor(Channel=2, ZeroOffset=0))
    servoMotors.append(ServoMotor(Channel=3, ZeroOffset=0))
    line_of_mountain(servoMotors)

    pass

if __name__ == "__main__":
    main()
