#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# FileName:     Fuji
# Author:       8ucchiman
# CreatedDate:  2024-03-04 11:30:01
# LastModified: 2024-03-04 12:41:13
# Reference:    8ucchiman.jp
# Description:  ---
#

from random import randint
from time import sleep


class Fuji (object):
    def __init__(self, servoMotors):
        self.servoMotors = servoMotors

    def __call__(self):
        pass

    def snow_ridge_line(self):
        """
            稜線 (白)
        """
        track_lst = [
                     [59, 81, 75, 22],
                     [61, 81, 75, 22],
                     [63, 81, 75, 22],
                     [65, 81, 75, 25],
                     [67, 81, 75, 25],
                     [68, 81, 75, 25],
                     [70, 81, 75, 25],
                     [72, 81, 75, 20],
                     [74, 81, 75, 15],
                     [75, 81, 75, 15],
                     [76, 81, 75, 10],
                     [77, 81, 75, 8],
                     [78, 81, 75, 8],
                     [79, 82, 75, 9],
                     [80, 82, 75, 8],
                     [81, 82, 75, 8],
                     [82, 82, 75, 8],
                     [83, 82, 75, 8],
                     [84, 82, 75, 8],
                     [85, 82, 75, 8],
                     [86, 82, 75, 8],
                     [87, 82, 75, 8],
                     [88, 82, 75, 8],
                     [89, 82, 75, 8],
                     [90, 82, 75, 8],
                     [91, 82, 75, 8],
                     [92, 82, 75, 10],
                     [93, 82, 75, 12],
                     [94, 82, 75, 13],
                     [95, 82, 75, 15],
                     [96, 82, 75, 15],
                     [97, 82, 75, 17],
                     [98, 82, 75, 17],
                     [100, 82, 75, 20],
                     [101, 82, 75, 22],
                     [102, 82, 75, 22],

                    ]
        for track_path in track_lst:
            print(track_path)
            self.servoMotors[0].setAngle(track_path[0])
            self.servoMotors[1].setAngle(track_path[1])
            self.servoMotors[2].setAngle(track_path[2])
            self.servoMotors[3].setAngle(track_path[3])
            sleep(0.5)

    def snow_ridge(self):
        """
            尾根 (白)
        """
        track_lst = [
                     [57, 81, 75, 22],
                     [57, 81, 75, 10],
                     [58, 81, 75, 0],
                     [59, 78, 79, 5],
                     [59, 78, 79, 0],
                     [60, 76, 83, 0],
                     [60, 75, 85, 0],
                     [61, 75, 86, 0],
                     [62, 73, 90, 4],
                     [62, 72, 91, 0],
                     [63, 69, 95, 2],
                     [66, 71, 95, 2],
                     [70, 71, 97, 0],
                    ]
        for track_path in track_lst:
            print(track_path)
            self.servoMotors[0].setAngle(track_path[0])
            self.servoMotors[1].setAngle(track_path[1])
            self.servoMotors[2].setAngle(track_path[2])
            self.servoMotors[3].setAngle(track_path[3])
            sleep(0.5)

    def snow_slope(self):
        """
            斜面 (白)
        """
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
            self.servoMotors[0].setAngle(track_path[0])
            self.servoMotors[1].setAngle(track_path[1])
            self.servoMotors[2].setAngle(track_path[2])
            self.servoMotors[3].setAngle(track_path[3])
            sleep(0.5)

    def sky(self):
        """
            空 (赤:オレンジ:黄緑:白:青=1:3:3:1:2)
            乱数
        """
        num_line = randint(-2, 16)
        position = randint(10, 150)
        # line_base
        #for motor00 in range(12, 100):
        #    print(motor00)
        #    self.servoMotors[0].setAngle(motor00)
        #    self.servoMotors[1].setAngle(89)
        #    self.servoMotors[2].setAngle(58)
        #    self.servoMotors[3].setAngle(0)
        #    sleep(0.5)

        # m01
        #for motor00 in range(12, 98):
        #    print(motor00)
        #    if motor00 < 60:
        #        self.servoMotors[0].setAngle(motor00)
        #        self.servoMotors[1].setAngle(93)
        #        self.servoMotors[2].setAngle(52)
        #        self.servoMotors[3].setAngle(0)
        #    elif 60 <= motor00 and motor00 < 75:
        #        self.servoMotors[0].setAngle(motor00)
        #        self.servoMotors[1].setAngle(94)
        #        self.servoMotors[2].setAngle(52)
        #        self.servoMotors[3].setAngle(0)
        #    else:
        #        self.servoMotors[0].setAngle(motor00)
        #        self.servoMotors[1].setAngle(95)
        #        self.servoMotors[2].setAngle(52)
        #        self.servoMotors[3].setAngle(0)

        #    sleep(0.5)

        # m02
        #for motor00 in range(15, 95):
        #    print(motor00)
        #    if motor00 < 30:
        #        self.servoMotors[0].setAngle(motor00)
        #        self.servoMotors[1].setAngle(95)
        #        self.servoMotors[2].setAngle(48)
        #        self.servoMotors[3].setAngle(0)
        #    elif 30 <= motor00 and motor00 < 60:
        #        self.servoMotors[0].setAngle(motor00)
        #        self.servoMotors[1].setAngle(96)
        #        self.servoMotors[2].setAngle(48)
        #        self.servoMotors[3].setAngle(0)
        #    else:
        #        self.servoMotors[0].setAngle(motor00)
        #        self.servoMotors[1].setAngle(97)
        #        self.servoMotors[2].setAngle(49)
        #        self.servoMotors[3].setAngle(0)

        #    sleep(0.5)



    def internal_mountain(self):
        """
            山の内部
            ベースとなる色 (黒, 紺)
        """
        # p25
        #for motor00 in range(-13, 83):
        #    print(motor00)
        #    if motor00 < 10:
        #        self.servoMotors[0].setAngle(motor00)
        #        self.servoMotors[1].setAngle(48)
        #        self.servoMotors[2].setAngle(120)
        #        self.servoMotors[3].setAngle(0)
        #    elif 10 <= motor00 and motor00 <= 40:
        #        self.servoMotors[0].setAngle(motor00)
        #        self.servoMotors[1].setAngle(49)
        #        self.servoMotors[2].setAngle(120)
        #        self.servoMotors[3].setAngle(0)
        #    else:
        #        self.servoMotors[0].setAngle(motor00)
        #        self.servoMotors[1].setAngle(51)
        #        self.servoMotors[2].setAngle(120)
        #        self.servoMotors[3].setAngle(0)
        #    #sleep(2.0)
        #    sleep(0.5)


        ## p23
        #for motor00 in range(-13, 85):
        #    print(motor00)
        #    if motor00 < 13:
        #        self.servoMotors[0].setAngle(motor00)
        #        self.servoMotors[1].setAngle(51)
        #        self.servoMotors[2].setAngle(118)
        #        self.servoMotors[3].setAngle(0)
        #    elif 13 <= motor00 and motor00 < 70:
        #        self.servoMotors[0].setAngle(motor00)
        #        self.servoMotors[1].setAngle(51)
        #        self.servoMotors[2].setAngle(119)
        #        self.servoMotors[3].setAngle(0)
        #    else:
        #        self.servoMotors[0].setAngle(motor00)
        #        self.servoMotors[1].setAngle(51)
        #        self.servoMotors[2].setAngle(120)
        #        self.servoMotors[3].setAngle(0)
        #    sleep(0.5)


        #for motor00 in range(-13, 90):
        #    print(motor00)
        #    if motor00 < 13:
        #        self.servoMotors[0].setAngle(motor00)
        #        self.servoMotors[1].setAngle(53)
        #        self.servoMotors[2].setAngle(115)
        #        self.servoMotors[3].setAngle(0)
        #    else:
        #        self.servoMotors[0].setAngle(motor00)
        #        self.servoMotors[1].setAngle(53)
        #        self.servoMotors[2].setAngle(116)
        #        self.servoMotors[3].setAngle(0)
        #    #else:
        #    #    self.servoMotors[0].setAngle(motor00)
        #    #    self.servoMotors[1].setAngle(53)
        #    #    self.servoMotors[2].setAngle(117)
        #    #    self.servoMotors[3].setAngle(0)
        #    sleep(0.5)

        # p21
        #for motor00 in range(-13, 95):
        #    print(motor00)
        #    #if motor00 < 13:
        #    self.servoMotors[0].setAngle(motor00)
        #    self.servoMotors[1].setAngle(56)
        #    self.servoMotors[2].setAngle(113)
        #    self.servoMotors[3].setAngle(0)
        #    #else:
        #    #    self.servoMotors[0].setAngle(motor00)
        #    #    self.servoMotors[1].setAngle(53)
        #    #    self.servoMotors[2].setAngle(116)
        #    #    self.servoMotors[3].setAngle(0)
        #    #else:
        #    #    self.servoMotors[0].setAngle(motor00)
        #    #    self.servoMotors[1].setAngle(53)
        #    #    self.servoMotors[2].setAngle(117)
        #    #    self.servoMotors[3].setAngle(0)
        #    sleep(0.5)

        #p20
        #for motor00 in range(-13, 102):
        #    print(motor00)
        #    #if motor00 < 13:
        #    self.servoMotors[0].setAngle(motor00)
        #    self.servoMotors[1].setAngle(60)
        #    self.servoMotors[2].setAngle(108)
        #    self.servoMotors[3].setAngle(0)
        #    #else:
        #    #    self.servoMotors[0].setAngle(motor00)
        #    #    self.servoMotors[1].setAngle(53)
        #    #    self.servoMotors[2].setAngle(116)
        #    #    self.servoMotors[3].setAngle(0)
        #    #else:
        #    #    self.servoMotors[0].setAngle(motor00)
        #    #    self.servoMotors[1].setAngle(53)
        #    #    self.servoMotors[2].setAngle(117)
        #    #    self.servoMotors[3].setAngle(0)
        #    sleep(0.5)

        #p19
        #for motor00 in range(-13, 109):
        #    print(motor00)
        #    #if motor00 < 13:
        #    self.servoMotors[0].setAngle(motor00)
        #    self.servoMotors[1].setAngle(61)
        #    self.servoMotors[2].setAngle(106)
        #    self.servoMotors[3].setAngle(0)
        #    #else:
        #    #    self.servoMotors[0].setAngle(motor00)
        #    #    self.servoMotors[1].setAngle(53)
        #    #    self.servoMotors[2].setAngle(116)
        #    #    self.servoMotors[3].setAngle(0)
        #    #else:
        #    #    self.servoMotors[0].setAngle(motor00)
        #    #    self.servoMotors[1].setAngle(53)
        #    #    self.servoMotors[2].setAngle(117)
        #    #    self.servoMotors[3].setAngle(0)
        #    sleep(0.5)

        # p18
        #for motor00 in range(-13, 109):
        #    print(motor00)
        #    if motor00 < 24:
        #        self.servoMotors[0].setAngle(motor00)
        #        self.servoMotors[1].setAngle(62)
        #        self.servoMotors[2].setAngle(104)
        #        self.servoMotors[3].setAngle(0)
        #    elif 24 <= motor00 and motor00 < 92:
        #        self.servoMotors[0].setAngle(motor00)
        #        self.servoMotors[1].setAngle(63)
        #        self.servoMotors[2].setAngle(104)
        #        self.servoMotors[3].setAngle(0)
        #    else:
        #        self.servoMotors[0].setAngle(motor00)
        #        self.servoMotors[1].setAngle(64)
        #        self.servoMotors[2].setAngle(104)
        #        self.servoMotors[3].setAngle(0)
        #    sleep(0.5)

        # p17
        #for motor00 in range(-13, 113):
        #    print(motor00)
        #    if motor00 < 19:
        #        self.servoMotors[0].setAngle(motor00)
        #        self.servoMotors[1].setAngle(62)
        #        self.servoMotors[2].setAngle(102)
        #        self.servoMotors[3].setAngle(0)
        #    elif 19 <= motor00 and motor00 <38:
        #        self.servoMotors[0].setAngle(motor00)
        #        self.servoMotors[1].setAngle(63)
        #        self.servoMotors[2].setAngle(102)
        #        self.servoMotors[3].setAngle(0)
        #    elif 38 <= motor00 and motor00 < 57:
        #        self.servoMotors[0].setAngle(motor00)
        #        self.servoMotors[1].setAngle(65)
        #        self.servoMotors[2].setAngle(102)
        #        self.servoMotors[3].setAngle(0)
        #    else:
        #        self.servoMotors[0].setAngle(motor00)
        #        self.servoMotors[1].setAngle(66)
        #        self.servoMotors[2].setAngle(102)
        #        self.servoMotors[3].setAngle(0)
        #    sleep(0.5)


        # p16
        #for motor00 in range(-13, 117):
        #    print(motor00)
        #    if motor00 < 19:
        #        self.servoMotors[0].setAngle(motor00)
        #        self.servoMotors[1].setAngle(64)
        #        self.servoMotors[2].setAngle(100)
        #        self.servoMotors[3].setAngle(0)
        #    elif 19 <= motor00 and motor00 < 49:
        #        self.servoMotors[0].setAngle(motor00)
        #        self.servoMotors[1].setAngle(65)
        #        self.servoMotors[2].setAngle(100)
        #        self.servoMotors[3].setAngle(0)
        #    elif 49 <= motor00 and motor00 < 95:
        #        self.servoMotors[0].setAngle(motor00)
        #        self.servoMotors[1].setAngle(66)
        #        self.servoMotors[2].setAngle(100)
        #        self.servoMotors[3].setAngle(0)
        #    else:
        #        self.servoMotors[0].setAngle(motor00)
        #        self.servoMotors[1].setAngle(68)
        #        self.servoMotors[2].setAngle(100)
        #        self.servoMotors[3].setAngle(0)
        #    sleep(0.5)


        # p15
        #for motor00 in range(-13, 113):
        #    print(motor00)
        #    if motor00 < 13:
        #        self.servoMotors[0].setAngle(motor00)
        #        self.servoMotors[1].setAngle(65)
        #        self.servoMotors[2].setAngle(97)
        #        self.servoMotors[3].setAngle(0)
        #    elif 13 <= motor00 and motor00 < 37:
        #        self.servoMotors[0].setAngle(motor00)
        #        self.servoMotors[1].setAngle(66)
        #        self.servoMotors[2].setAngle(97)
        #        self.servoMotors[3].setAngle(0)
        #    elif 37 <= motor00 and motor00 < 64:
        #        self.servoMotors[0].setAngle(motor00)
        #        self.servoMotors[1].setAngle(68)
        #        self.servoMotors[2].setAngle(97)
        #        self.servoMotors[3].setAngle(0)
        #    else:
        #        self.servoMotors[0].setAngle(motor00)
        #        self.servoMotors[1].setAngle(69)
        #        self.servoMotors[2].setAngle(97)
        #        self.servoMotors[3].setAngle(0)
        #    sleep(0.3)

        # p14
        #for motor00 in range(-13, 119):
        #    print(motor00)
        #    if motor00 < 10:
        #        self.servoMotors[0].setAngle(motor00)
        #        self.servoMotors[1].setAngle(66)
        #        self.servoMotors[2].setAngle(95)
        #        self.servoMotors[3].setAngle(2)
        #    elif 10 <= motor00 and motor00 < 39:
        #        self.servoMotors[0].setAngle(motor00)
        #        self.servoMotors[1].setAngle(68)
        #        self.servoMotors[2].setAngle(95)
        #        self.servoMotors[3].setAngle(2)
        #    elif 39 <= motor00 and motor00 < 85:
        #        self.servoMotors[0].setAngle(motor00)
        #        self.servoMotors[1].setAngle(69)
        #        self.servoMotors[2].setAngle(95)
        #        self.servoMotors[3].setAngle(2)
        #    else:
        #        self.servoMotors[0].setAngle(motor00)
        #        self.servoMotors[1].setAngle(70)
        #        self.servoMotors[2].setAngle(95)
        #        self.servoMotors[3].setAngle(2)
        #    sleep(0.3)


        # p13
        #for motor00 in range(-13, 119):
        #    print(motor00)
        #    if motor00 < 15:
        #        self.servoMotors[0].setAngle(motor00)
        #        self.servoMotors[1].setAngle(69)
        #        self.servoMotors[2].setAngle(91)
        #        self.servoMotors[3].setAngle(0)
        #    elif 15 <= motor00 and motor00 < 65:
        #        self.servoMotors[0].setAngle(motor00)
        #        self.servoMotors[1].setAngle(71)
        #        self.servoMotors[2].setAngle(91)
        #        self.servoMotors[3].setAngle(0)
        #    elif 65 <= motor00 and motor00 < 85:
        #        self.servoMotors[0].setAngle(motor00)
        #        self.servoMotors[1].setAngle(72)
        #        self.servoMotors[2].setAngle(91)
        #        self.servoMotors[3].setAngle(0)

        #    else:
        #        self.servoMotors[0].setAngle(motor00)
        #        self.servoMotors[1].setAngle(73)
        #        self.servoMotors[2].setAngle(91)
        #        self.servoMotors[3].setAngle(0)
        #    sleep(0.3)

        # p12
        #for motor00 in range(-8, 125):
        #    print(motor00)
        #    if motor00 < 15:
        #        self.servoMotors[0].setAngle(motor00)
        #        self.servoMotors[1].setAngle(62)
        #        self.servoMotors[2].setAngle(98)
        #        self.servoMotors[3].setAngle(30)
        #    elif 15 <= motor00 and motor00 < 40:
        #        self.servoMotors[0].setAngle(motor00)
        #        self.servoMotors[1].setAngle(64)
        #        self.servoMotors[2].setAngle(98)
        #        self.servoMotors[3].setAngle(30)
        #    elif 40 <= motor00 and motor00 < 77:
        #        self.servoMotors[0].setAngle(motor00)
        #        self.servoMotors[1].setAngle(65)
        #        self.servoMotors[2].setAngle(98)
        #        self.servoMotors[3].setAngle(30)
        #    else:
        #        self.servoMotors[0].setAngle(motor00)
        #        self.servoMotors[1].setAngle(66)
        #        self.servoMotors[2].setAngle(98)
        #        self.servoMotors[3].setAngle(30)
        #    sleep(0.3)

        # p11
        #for motor00 in range(-13, 120):
        #    print(motor00)
        #    if motor00 < 15:
        #        self.servoMotors[0].setAngle(motor00)
        #        self.servoMotors[1].setAngle(73)
        #        self.servoMotors[2].setAngle(85)
        #        self.servoMotors[3].setAngle(0)
        #    elif 15 <= motor00 and motor00 < 40:
        #        self.servoMotors[0].setAngle(motor00)
        #        self.servoMotors[1].setAngle(74)
        #        self.servoMotors[2].setAngle(85)
        #        self.servoMotors[3].setAngle(0)
        #    elif 40 <= motor00 and motor00 < 77:
        #        self.servoMotors[0].setAngle(motor00)
        #        self.servoMotors[1].setAngle(75)
        #        self.servoMotors[2].setAngle(85)
        #        self.servoMotors[3].setAngle(0)
        #    else:
        #        self.servoMotors[0].setAngle(motor00)
        #        self.servoMotors[1].setAngle(76)
        #        self.servoMotors[2].setAngle(85)
        #        self.servoMotors[3].setAngle(0)
        #    sleep(0.3)

        # p10
        #for motor00 in range(-15, 122):
        #    print(motor00)
        #    if motor00 < 20:
        #        self.servoMotors[0].setAngle(motor00)
        #        self.servoMotors[1].setAngle(74)
        #        self.servoMotors[2].setAngle(83)
        #        self.servoMotors[3].setAngle(0)
        #    elif 20 <= motor00 and motor00 < 65:
        #        self.servoMotors[0].setAngle(motor00)
        #        self.servoMotors[1].setAngle(76)
        #        self.servoMotors[2].setAngle(83)
        #        self.servoMotors[3].setAngle(0)
        #    elif 65 <= motor00 and motor00 < 80:
        #        self.servoMotors[0].setAngle(motor00)
        #        self.servoMotors[1].setAngle(77)
        #        self.servoMotors[2].setAngle(83)
        #        self.servoMotors[3].setAngle(0)

        #    else:
        #        self.servoMotors[0].setAngle(motor00)
        #        self.servoMotors[1].setAngle(78)
        #        self.servoMotors[2].setAngle(83)
        #        self.servoMotors[3].setAngle(0)
        #    sleep(0.3)

        # p09
        #for motor00 in range(-13, 110):
        #    print(motor00)
        #    if motor00 < 9:
        #        self.servoMotors[0].setAngle(motor00)
        #        self.servoMotors[1].setAngle(77)
        #        self.servoMotors[2].setAngle(79)
        #        self.servoMotors[3].setAngle(0)
        #    #elif 9 <= motor00 and motor00 < 36:
        #    #    self.servoMotors[0].setAngle(motor00)
        #    #    self.servoMotors[1].setAngle(78)
        #    #    self.servoMotors[2].setAngle(79)
        #    #    self.servoMotors[3].setAngle(0)
        #    elif 36 <= motor00 and motor00 < 70:
        #        self.servoMotors[0].setAngle(motor00)
        #        self.servoMotors[1].setAngle(78)
        #        self.servoMotors[2].setAngle(80)
        #        self.servoMotors[3].setAngle(0)
        #    elif 70 <= motor00:
        #        self.servoMotors[0].setAngle(motor00)
        #        self.servoMotors[1].setAngle(80)
        #        self.servoMotors[2].setAngle(79)
        #        self.servoMotors[3].setAngle(0)
        #    else:
        #        pass
        #    sleep(0.3)

        # p08
        #for motor00 in range(-10, 114):
        #    print(motor00)
        #    if motor00 < 9:
        #        self.servoMotors[0].setAngle(motor00)
        #        self.servoMotors[1].setAngle(77)
        #        self.servoMotors[2].setAngle(79)
        #        self.servoMotors[3].setAngle(5)
        #    #elif 9 <= motor00 and motor00 < 38:
        #    #    self.servoMotors[0].setAngle(motor00)
        #    #    self.servoMotors[1].setAngle(77)
        #    #    self.servoMotors[2].setAngle(79)
        #    #    self.servoMotors[3].setAngle(5)
        #    elif 38 <= motor00 and motor00 < 70:
        #        self.servoMotors[0].setAngle(motor00)
        #        self.servoMotors[1].setAngle(79)
        #        self.servoMotors[2].setAngle(79)
        #        self.servoMotors[3].setAngle(5)
        #    elif 70 <= motor00:
        #        self.servoMotors[0].setAngle(motor00)
        #        self.servoMotors[1].setAngle(80)
        #        self.servoMotors[2].setAngle(79)
        #        self.servoMotors[3].setAngle(5)
        #    else:
        #        pass
        #    sleep(0.3)

        # p07
        #for motor00 in range(-5, 110):
        #    print(motor00)
        #    if motor00 < 7:
        #        self.servoMotors[0].setAngle(motor00)
        #        self.servoMotors[1].setAngle(79)
        #        self.servoMotors[2].setAngle(75)
        #        self.servoMotors[3].setAngle(0)
        #    #elif 7 <= motor00 and motor00 < 43:
        #    #    self.servoMotors[0].setAngle(motor00)
        #    #    self.servoMotors[1].setAngle(77)
        #    #    self.servoMotors[2].setAngle(79)
        #    #    self.servoMotors[3].setAngle(5)
        #    elif 43 <= motor00 and motor00 < 70:
        #        self.servoMotors[0].setAngle(motor00)
        #        self.servoMotors[1].setAngle(81)
        #        self.servoMotors[2].setAngle(75)
        #        self.servoMotors[3].setAngle(0)
        #    elif 70 <= motor00:
        #        self.servoMotors[0].setAngle(motor00)
        #        self.servoMotors[1].setAngle(82)
        #        self.servoMotors[2].setAngle(75)
        #        self.servoMotors[3].setAngle(0)
        #    else:
        #        pass
        #    sleep(0.3)

        # p06
        #for motor00 in range(-3, 110):
        #    print(motor00)
        #    if motor00 < 4:
        #        self.servoMotors[0].setAngle(motor00)
        #        self.servoMotors[1].setAngle(80)
        #        self.servoMotors[2].setAngle(73)
        #        self.servoMotors[3].setAngle(0)
        #    #elif 7 <= motor00 and motor00 < 43:
        #    #    self.servoMotors[0].setAngle(motor00)
        #    #    self.servoMotors[1].setAngle(80)
        #    #    self.servoMotors[2].setAngle(73)
        #    #    self.servoMotors[3].setAngle(0)
        #    elif 44 <= motor00 and motor00 < 70:
        #        self.servoMotors[0].setAngle(motor00)
        #        self.servoMotors[1].setAngle(82)
        #        self.servoMotors[2].setAngle(73)
        #        self.servoMotors[3].setAngle(0)
        #    elif 70 <= motor00:
        #        self.servoMotors[0].setAngle(motor00)
        #        self.servoMotors[1].setAngle(83)
        #        self.servoMotors[2].setAngle(73)
        #        self.servoMotors[3].setAngle(0)
        #    else:
        #        pass
        #    sleep(0.3)

        # p05
        #for motor00 in range(-1, 109):
        #    print(motor00)
        #    if motor00 < 3:
        #        self.servoMotors[0].setAngle(motor00)
        #        self.servoMotors[1].setAngle(82)
        #        self.servoMotors[2].setAngle(70)
        #        self.servoMotors[3].setAngle(0)
        #    #elif 7 <= motor00 and motor00 < 43:
        #    #    self.servoMotors[0].setAngle(motor00)
        #    #    self.servoMotors[1].setAngle(80)
        #    #    self.servoMotors[2].setAngle(73)
        #    #    self.servoMotors[3].setAngle(0)
        #    elif 52 <= motor00 and motor00 < 70:
        #        self.servoMotors[0].setAngle(motor00)
        #        self.servoMotors[1].setAngle(84)
        #        self.servoMotors[2].setAngle(70)
        #        self.servoMotors[3].setAngle(0)
        #    elif 70 <= motor00:
        #        self.servoMotors[0].setAngle(motor00)
        #        self.servoMotors[1].setAngle(85)
        #        self.servoMotors[2].setAngle(70)
        #        self.servoMotors[3].setAngle(0)
        #    else:
        #        pass
        #    sleep(0.3)

        # 04
        for motor00 in range(51, 70):
            print(motor00)
            #if motor00 < 3:
            self.servoMotors[0].setAngle(motor00)
            self.servoMotors[1].setAngle(82)
            self.servoMotors[2].setAngle(73)
            self.servoMotors[3].setAngle(8)
            #elif 7 <= motor00 and motor00 < 43:
            #    self.servoMotors[0].setAngle(motor00)
            #    self.servoMotors[1].setAngle(80)
            #    self.servoMotors[2].setAngle(73)
            #    self.servoMotors[3].setAngle(0)
            #elif 52 <= motor00 and motor00 < 70:
            #    self.servoMotors[0].setAngle(motor00)
            #    self.servoMotors[1].setAngle(84)
            #    self.servoMotors[2].setAngle(70)
            #    self.servoMotors[3].setAngle(0)
            #elif 70 <= motor00:
            #    self.servoMotors[0].setAngle(motor00)
            #    self.servoMotors[1].setAngle(85)
            #    self.servoMotors[2].setAngle(70)
            #    self.servoMotors[3].setAngle(0)
            #else:
            #    pass
            sleep(0.3)

    def blue_slope (self):
        """
            斜面 (雲色)
        """
        track_lst = [
                     [53, 84, 70, 5],
                     [54, 84, 70, 5],
                     [55, 84, 70, 5],
                     [56, 84, 70, 5],
                     [57, 84, 70, 5],

                     [51, 83, 70, 0],
                     [52, 83, 70, 0],
                     [53, 83, 70, 0],
                     [54, 83, 70, 0],
                     [55, 83, 70, 0],
                     [56, 83, 70, 0],

                     [45, 82, 73, 0],
                     [46, 82, 73, 0],
                     [47, 82, 73, 0],
                     [48, 82, 73, 0],
                     [49, 82, 73, 0],
                     [50, 82, 73, 0],
                     [51, 82, 73, 0],
                     [52, 82, 73, 0],
                     [53, 82, 73, 0],
                     [54, 82, 73, 0],
                     [55, 82, 73, 0],
                     [56, 82, 73, 0],
                     [57, 82, 73, 0],
                     [58, 82, 73, 0],

                     [43, 80, 75, 0],
                     [44, 80, 75, 0],
                     [45, 80, 75, 0],
                     [46, 80, 75, 0],
                     [47, 80, 75, 0],
                     [48, 80, 75, 0],
                     [49, 80, 75, 0],
                     [50, 80, 75, 0],
                     [51, 80, 75, 0],
                     [52, 80, 75, 0],
                     [53, 80, 75, 0],
                     [54, 80, 75, 0],
                     [55, 80, 75, 0],
                     [56, 80, 75, 0],
                     [57, 80, 75, 0],
                     [58, 80, 75, 0],
                     [59, 80, 75, 0],

                     [39, 77, 80, 5],
                     [40, 77, 80, 5],
                     [41, 77, 80, 5],
                     [42, 77, 80, 5],
                     [43, 77, 80, 5],
                     [44, 77, 80, 5],
                     [45, 77, 80, 5],
                     [46, 77, 80, 5],
                     [47, 77, 80, 5],
                     [48, 77, 80, 5],
                     [49, 77, 80, 5],
                     [50, 77, 80, 5],
                     [51, 77, 80, 5],
                     [52, 77, 80, 5],
                     [53, 77, 80, 5],
                     [54, 77, 80, 5],
                     [55, 77, 80, 5],
                     [56, 77, 80, 5],
                     [57, 77, 80, 5],
                     [58, 77, 80, 5],
                     [59, 77, 80, 5],

                     [10, 75, 83, 5],
                     [11, 75, 83, 5],
                     [12, 75, 83, 5],
                     [13, 75, 83, 5],
                     [14, 75, 83, 5],
                     [15, 75, 83, 5],
                     [16, 75, 83, 5],
                     [17, 75, 83, 5],
                     [18, 75, 83, 5],
                     [19, 75, 83, 5],
                     [20, 75, 83, 5],
                     [21, 75, 83, 5],
                     [22, 75, 83, 5],
                     [23, 75, 83, 5],
                     [24, 75, 83, 5],
                     [25, 75, 83, 5],
                     [26, 75, 83, 5],
                     [27, 75, 83, 5],
                     [28, 75, 83, 5],
                     [29, 75, 83, 5],
                     [30, 75, 83, 5],
                     [31, 75, 83, 5],
                     [32, 75, 83, 5],
                     [33, 75, 83, 5],
                     [34, 75, 83, 5],
                     [35, 75, 83, 5],
                     [36, 75, 83, 5],
                     [37, 75, 83, 5],
                     [38, 75, 83, 5],
                     [39, 75, 83, 5],
                     [40, 75, 83, 5],
                     [41, 75, 83, 5],
                     [42, 75, 83, 5],
                     [43, 75, 83, 5],
                     [44, 75, 83, 5],
                     [45, 75, 83, 5],
                     [46, 75, 83, 5],
                     [47, 75, 83, 5],
                     [48, 75, 83, 5],
                     [49, 75, 83, 5],
                     [50, 75, 83, 5],
                     [51, 75, 83, 5],
                     [52, 75, 83, 5],
                     [53, 75, 83, 5],
                     [54, 75, 83, 5],
                     [55, 75, 83, 5],
                     [56, 75, 83, 5],
                     [57, 75, 83, 5],
                     [58, 75, 83, 5],
                     [59, 75, 83, 5],
                     [60, 75, 83, 5],
 

                     [10, 76, 83, 0],
                     [11, 76, 83, 0],
                     [12, 76, 83, 0],
                     [13, 76, 83, 0],
                     [14, 76, 83, 0],
                     [15, 76, 83, 0],
                     [16, 76, 83, 0],
                     [17, 76, 83, 0],
                     [18, 76, 83, 0],
                     [19, 76, 83, 0],
                     [20, 76, 83, 0],
                     [21, 76, 83, 0],
                     [22, 76, 83, 0],
                     [23, 76, 83, 0],
                     [24, 76, 83, 0],
                     [25, 76, 83, 0],
                     [26, 76, 83, 0],
                     [27, 76, 83, 0],
                     [28, 76, 83, 0],
                     [29, 76, 83, 0],
                     [30, 76, 83, 0],
                     [31, 76, 83, 0],
                     [32, 76, 83, 0],
                     [33, 76, 83, 0],
                     [34, 76, 83, 0],
                     [35, 76, 83, 0],
                     [36, 76, 83, 0],
                     [37, 76, 83, 0],
                     [38, 76, 83, 0],
                     [39, 76, 83, 0],
                     [40, 76, 83, 0],
                     [41, 76, 83, 0],
                     [42, 76, 83, 0],
                     [43, 76, 83, 0],
                     [44, 76, 83, 0],
                     [45, 77, 83, 0],
                     [46, 77, 83, 0],
                     [47, 77, 83, 0],
                     [48, 77, 83, 0],
                     [49, 77, 83, 0],
                     [50, 77, 83, 0],
                     [51, 77, 83, 0],
                     [52, 77, 83, 0],
                     [53, 77, 83, 0],
                     [54, 77, 83, 0],
                     [55, 77, 83, 0],
                     [56, 77, 83, 0],
                     [57, 77, 83, 0],
                     [58, 77, 83, 0],
                     [59, 77, 83, 0],
                     #[60, 77, 83, 0],

                     [18, 62, 100, 30],
                     [19, 62, 100, 30],
                     [20, 62, 100, 30],
                     [21, 62, 100, 30],
                     [22, 62, 100, 30],
                     [23, 62, 100, 30],
                     [24, 62, 100, 30],
                     [25, 62, 100, 30],
                     [26, 62, 100, 30],
                     [27, 62, 100, 30],
                     [28, 62, 100, 30],
                     [29, 62, 100, 30],
                     [30, 62, 100, 30],
                     [31, 62, 100, 30],
                     [32, 62, 100, 30],
                     [33, 62, 100, 30],
                     [34, 62, 100, 30],
                     [35, 62, 100, 30],
                     [36, 62, 100, 30],
                     [37, 62, 100, 30],
                     [38, 62, 100, 30],
                     [39, 62, 100, 30],
                     [40, 62, 100, 30],
                     [41, 62, 100, 30],
                     [42, 62, 100, 30],
                     [43, 62, 100, 30],
                     [44, 62, 100, 30],
                     [45, 62, 100, 30],
                     [46, 62, 100, 30],
                     [47, 62, 100, 30],
                     [48, 62, 100, 30],
                     [49, 62, 100, 30],
                     [50, 62, 100, 30],
                     [51, 62, 100, 30],

                     [17, 63, 100, 30],
                     [18, 63, 100, 30],
                     [19, 63, 100, 30],
                     [20, 63, 100, 30],
                     [21, 63, 100, 30],
                     [22, 63, 100, 30],
                     [23, 63, 100, 30],
                     [24, 63, 100, 30],
                     [25, 63, 100, 30],
                     [26, 63, 100, 30],
                     [27, 63, 100, 30],
                     [28, 63, 100, 30],
                     [29, 63, 100, 30],
                     [30, 63, 100, 30],
                     [31, 63, 100, 30],
                     [32, 63, 100, 30],
                     [33, 63, 100, 30],
                     [34, 63, 100, 30],
                     [35, 63, 100, 30],
                     [36, 63, 100, 30],
                     [37, 63, 100, 30],
                     [38, 63, 100, 30],
                     [39, 63, 100, 30],
                     [40, 63, 100, 30],
                     [41, 63, 100, 30],
                     [42, 63, 100, 30],
                     [43, 63, 100, 30],
                     [44, 63, 100, 30],
                     [45, 63, 100, 30],
                     [46, 63, 100, 30],
                     [47, 63, 100, 30],
                     [48, 63, 100, 30],
                     [49, 63, 100, 30],
                     [50, 63, 100, 30],

                    ]

        for track_path in track_lst:
            print(track_path)
            self.servoMotors[0].setAngle(track_path[0])
            self.servoMotors[1].setAngle(track_path[1])
            self.servoMotors[2].setAngle(track_path[2])
            self.servoMotors[3].setAngle(track_path[3])
            sleep(0.5)


    def line_of_mountain (self):
        """
            山の境界線 (赤)
        """
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
            self.servoMotors[0].setAngle(track_path[0])
            self.servoMotors[1].setAngle(track_path[1])
            self.servoMotors[2].setAngle(track_path[2])
            self.servoMotors[3].setAngle(track_path[3])
            sleep(0.5)
