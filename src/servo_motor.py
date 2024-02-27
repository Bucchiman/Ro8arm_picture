import sys
from time import sleep

from adafruit_pca9685 import PCA9685
from adafruit_motor import servo
from board import SCL, SDA
import busio

from varspeed import Vspeed


class ServoMotor:
    """
        Reference: https://rb-station.com/blogs/article/pca9685-raspbery-pi-python
    """
    def __init__(self, Channel):
        self.MIN = 0
        self.MAX = 180
        self.mChannel = Channel
        self.vs = Vspeed(init_position=self.MIN, result="int")
        self.vs.set_bounds(lower_bound=self.MIN, upper_bound=self.MAX)
        i2c = busio.I2C(SCL, SDA)
        pca = PCA9685(i2c)
        pca.freuquency = 60
        self.servo = servo.Servo(pca)
        self.servo_sequence = [(self.MAX/2, 2, 10, "QuadEaseIn"),
                               (self.MIN, 2.0, 10, "QuadEaseOut"),
                               (self.MAX, 2.0, 10, "SineEaseInOut")]

    def setAngle(self, angle):

        position, running, changed = self.vs.sequence(sequence=self.servo_sequence,
                                                      loop_max=2)
        if changed:
            print(f'Sequence Num: {self.vs.seq_pos}, Step: {self.vs.step}, Position: {position}')
            self.servo.angle = position

    def cleanup(self):
        pass
        ## self.setAngle(10)
        #self.mPwm.set_pwm(self.mChannel, 0, 0)
        #sleep(1)
        #self.mPwm.set_pwm(self.mChannel, 0, 0)
        #sleep(1)


    #def check_angle(self):
    #    self.#
