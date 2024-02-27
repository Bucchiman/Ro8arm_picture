# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

import time

from board import SCL, SDA
import busio
from adafruit_motor import servo
from adafruit_pca9685 import PCA9685

from varspeed import Vspeed


MIN = 0
MAX = 180

vs = Vspeed(init_position=MIN, result="int")
vs.set_bounds(lower_bound=MIN, upper_bound=MAX)

i2c = busio.I2C(SCL, SDA)

pca = PCA9685(i2c)
pca.frequency = 50

servo7 = servo.Servo(pca.channels[0])

servo7.angle = MIN
servo7_sequence = [(MAX/2, 2, 10, "QuadEaseIn"),
                   (MIN, 2.0, 10, "QuadEaseOut"),
                   (MAX, 2.0, 10, "SineEaseInOut")]


## We sleep in the loops to give the servo time to move into position.
#for i in range(180):
#    servo7.angle = i
#    time.sleep(0.03)
#for i in range(180):
#    servo7.angle = 180 - i
#    time.sleep(0.03)


running = True

while running:
    position, running, changed = vs.sequence(sequence=servo7_sequence, loop_max=2)

    #print(position, running, changed)
    if changed:
        print(f'Sequence Num: {vs.seq_pos}, Step: {vs.step}, Position: {position}')
        servo7.angle = position
