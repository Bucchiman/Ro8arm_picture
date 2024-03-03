from random import randint
from servo_motor import ServoMotor
from time import sleep


def line_base(position: int):
    pass

def sky():
    num_line = randint(-2, 16)
    position = randint(10, 150)

def snow (servoMotors):
    # 稜線
    #track_lst = [
    #             [59, 81, 75, 22],
    #             [61, 81, 75, 22],
    #             [63, 81, 75, 22],
    #             [65, 81, 75, 25],
    #             [67, 81, 75, 25],
    #             [68, 81, 75, 25],
    #             [70, 81, 75, 25],
    #             [72, 81, 75, 20],
    #             [74, 81, 75, 15],
    #             [75, 81, 75, 15],
    #             [76, 81, 75, 10],
    #             [77, 81, 75, 8],
    #             [78, 81, 75, 8],
    #             [79, 82, 75, 9],
    #             [80, 82, 75, 8],
    #             [81, 82, 75, 8],
    #             [82, 82, 75, 8],
    #             [83, 82, 75, 8],
    #             [84, 82, 75, 8],
    #             [85, 82, 75, 8],
    #             [86, 82, 75, 8],
    #             [87, 82, 75, 8],
    #             [88, 82, 75, 8],
    #             [89, 82, 75, 8],
    #             [90, 82, 75, 8],
    #             [91, 82, 75, 8],
    #             [92, 82, 75, 10],
    #             [93, 82, 75, 12],
    #             [94, 82, 75, 13],
    #             [95, 82, 75, 15],
    #             [96, 82, 75, 15],
    #             [97, 82, 75, 17],
    #             [98, 82, 75, 17],
    #             [100, 82, 75, 20],
    #             [101, 82, 75, 22],
    #             [102, 82, 75, 22],

    #            ]
    #for track_path in track_lst:
    #    print(track_path)
    #    servoMotors[0].setAngle(track_path[0])
    #    servoMotors[1].setAngle(track_path[1])
    #    servoMotors[2].setAngle(track_path[2])
    #    servoMotors[3].setAngle(track_path[3])
    #    sleep(0.5)


    # 尾根
    #track_lst = [
    #             [57, 81, 75, 22],
    #             [57, 81, 75, 10],
    #             [58, 81, 75, 0],
    #             [59, 78, 79, 5],
    #             [59, 78, 79, 0],
    #             [60, 76, 83, 0],
    #             [60, 75, 85, 0],
    #             [61, 75, 86, 0],
    #             [62, 73, 90, 4],
    #             [62, 72, 91, 0],
    #             [63, 69, 95, 2],
    #             [66, 71, 95, 2],
    #             [70, 71, 97, 0],
    #            ]
    #for track_path in track_lst:
    #    print(track_path)
    #    servoMotors[0].setAngle(track_path[0])
    #    servoMotors[1].setAngle(track_path[1])
    #    servoMotors[2].setAngle(track_path[2])
    #    servoMotors[3].setAngle(track_path[3])
    #    sleep(0.5)


    # 斜面
    track_lst = [
                 [53, 75, 85, 0],
                 [54, 75, 85, 0],
                 [55, 75, 85, 0],
                 [56, 75, 85, 0],
                 [57, 75, 85, 0],
                 [58, 75, 85, 0],
                 [59, 75, 85, 0],

                 [46, 71, 91, 0],
                 [47, 71, 91, 0],
                 [48, 71, 91, 0],
                 [49, 72, 91, 0],
                 [50, 72, 91, 0],
                 [51, 72, 91, 0],

                 [52, 72, 91, 0],
                 [53, 72, 91, 0],
                 [54, 72, 91, 0],
                 [55, 72, 91, 0],
                 [56, 72, 91, 0],
                 [57, 72, 91, 0],
                 [58, 72, 91, 0],
                 [42, 69, 95, 2],
                 [43, 69, 95, 2],
                 [44, 69, 95, 2],
                 [45, 69, 95, 2],
                 [46, 69, 95, 2],
                 [47, 69, 95, 2],
                 [48, 69, 95, 2],
                 [49, 69, 95, 2],
                 [50, 69, 95, 2],
                 [51, 69, 95, 2],
                 [52, 69, 95, 2],
                 [53, 69, 95, 2],
                 [54, 69, 95, 2],

                 [39, 67, 97, 0],
                 [40, 67, 97, 0],
                 [41, 67, 97, 0],
                 [42, 67, 97, 0],
                 [43, 67, 97, 0],
                 [44, 67, 97, 0],
                 [45, 67, 97, 0],
                 [46, 67, 97, 0],
                 [47, 67, 97, 0],
                 [48, 67, 97, 0],
                 [49, 67, 97, 0],
                 [50, 67, 97, 0],
                 [51, 67, 97, 0],
                 [52, 67, 97, 0],

                 [34, 65, 100, 0],
                 [35, 65, 100, 0],
                 [36, 65, 100, 0],
                 [37, 65, 100, 0],
                 [38, 65, 100, 0],
                 [39, 65, 100, 0],
                 [40, 65, 100, 0],
                 [41, 65, 100, 0],
                 [42, 65, 100, 0],
                 [43, 65, 100, 0],
                 [44, 65, 100, 0],
                 [45, 65, 100, 0],
                 [46, 65, 100, 0],
                 [47, 65, 100, 0],
                 [48, 65, 100, 0],
                 [49, 65, 100, 0],
                 [50, 65, 100, 0],
                ]

    for track_path in track_lst:
        print(track_path)
        servoMotors[0].setAngle(track_path[0])
        servoMotors[1].setAngle(track_path[1])
        servoMotors[2].setAngle(track_path[2])
        servoMotors[3].setAngle(track_path[3])
        sleep(0.5)


def internal_mountain (servoMotors):
    # p25
    #for motor00 in range(-13, 83):
    #    print(motor00)
    #    if motor00 < 10:
    #        servoMotors[0].setAngle(motor00)
    #        servoMotors[1].setAngle(48)
    #        servoMotors[2].setAngle(120)
    #        servoMotors[3].setAngle(0)
    #    elif 10 <= motor00 and motor00 <= 40:
    #        servoMotors[0].setAngle(motor00)
    #        servoMotors[1].setAngle(49)
    #        servoMotors[2].setAngle(120)
    #        servoMotors[3].setAngle(0)
    #    else:
    #        servoMotors[0].setAngle(motor00)
    #        servoMotors[1].setAngle(51)
    #        servoMotors[2].setAngle(120)
    #        servoMotors[3].setAngle(0)
    #    #sleep(2.0)
    #    sleep(0.5)

 
    # p23
    #for motor00 in range(-13, 99):
    #    print(motor00)
    #    if motor00 < 13:
    #        servoMotors[0].setAngle(motor00)
    #        servoMotors[1].setAngle(51)
    #        servoMotors[2].setAngle(118)
    #        servoMotors[3].setAngle(0)
    #    elif 13 <= motor00 and motor00 < 70:
    #        servoMotors[0].setAngle(motor00)
    #        servoMotors[1].setAngle(51)
    #        servoMotors[2].setAngle(119)
    #        servoMotors[3].setAngle(0)
    #    else:
    #        servoMotors[0].setAngle(motor00)
    #        servoMotors[1].setAngle(51)
    #        servoMotors[2].setAngle(120)
    #        servoMotors[3].setAngle(0)


    #    sleep(0.5)


    for motor00 in range(-13, 99):
        print(motor00)
        if motor00 < 13:
            servoMotors[0].setAngle(motor00)
            servoMotors[1].setAngle(53)
            servoMotors[2].setAngle(115)
            servoMotors[3].setAngle(0)
        else:
            servoMotors[0].setAngle(motor00)
            servoMotors[1].setAngle(53)
            servoMotors[2].setAngle(116)
            servoMotors[3].setAngle(0)
        #else:
        #    servoMotors[0].setAngle(motor00)
        #    servoMotors[1].setAngle(53)
        #    servoMotors[2].setAngle(117)
        #    servoMotors[3].setAngle(0)
        sleep(0.5)





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
    #line_of_mountain(servoMotors)
    #snow(servoMotors)

    internal_mountain(servoMotors)

    pass

if __name__ == "__main__":
    main()
