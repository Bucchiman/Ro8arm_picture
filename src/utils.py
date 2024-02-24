from servo_motor import ServoMotor
from time import sleep



def motor0():
    motor = ServoMotor(Channel=0, ZeroOffset=0)
    motor.setAngle(0)
    sleep(5)
    motor.cleanup()

def motor1():
    motor = ServoMotor(Channel=1, ZeroOffset=0)
    motor.setAngle(0)
    sleep(5)
    motor.cleanup()

def motor2():
    motor = ServoMotor(Channel=2, ZeroOffset=0)
    motor.setAngle(0)
    sleep(5)
    motor.cleanup()

def motor3():
    motor = ServoMotor(Channel=3, ZeroOffset=0)
    motor.setAngle(0)
    sleep(5)
    motor.cleanup()


def motor4():
    """
    test motor
    """
    motor = ServoMotor(Channel=4, ZeroOffset=0)
    motor.setAngle(0)
    sleep(5)
    motor.cleanup()


#pos00 pos01 pos02 pos03 pos04 pos05 pos06 pos07 pos08 pos09 pos0a pos0b pos0c pos0d pos0e pos0f
#pos10 pos11 pos12 pos13 pos14 pos15 pos16 pos17 pos18 pos19 pos1a pos1b pos1c pos1d pos1e pos1f
#pos20 pos21 pos22 pos23 pos24 pos25 pos26 pos27 pos28 pos29 pos2a pos2b pos2c pos2d pos2e pos2f
#pos30 pos31 pos32 pos33 pos34 pos35 pos36 pos37 pos38 pos39 pos3a pos3b pos3c pos3d pos3e pos3f
#pos40 pos41 pos42 pos43 pos44 pos45 pos46 pos47 pos48 pos49 pos4a pos4b pos4c pos4d pos4e pos4f
#pos50 pos51 pos52 pos53 pos54 pos55 pos56 pos57 pos58 pos59 pos5a pos5b pos5c pos5d pos5e pos5f
#pos60 pos61 pos62 pos63 pos64 pos65 pos66 pos67 pos68 pos69 pos6a pos6b pos6c pos6d pos6e pos6f
#pos70 pos71 pos72 pos73 pos74 pos75 pos76 pos77 pos78 pos79 pos7a pos7b pos7c pos7d pos7e pos7f
#pos80 pos81 pos82 pos83 pos84 pos85 pos86 pos87 pos88 pos89 pos8a pos8b pos8c pos8d pos8e pos8f
#pos90 pos91 pos92 pos93 pos94 pos95 pos96 pos97 pos98 pos99 pos9a pos9b pos9c pos9d pos9e pos9f
#posa0 posa1 posa2 posa3 posa4 posa5 posa6 posa7 posa8 posa9 posaa posab posac posad posae posaf
#posb0 posb1 posb2 posb3 posb4 posb5 posb6 posb7 posb8 posb9 posba posbb posbc posbd posbe posbf
#posc0 posc1 posc2 posc3 posc4 posc5 posc6 posc7 posc8 posc9 posca poscb poscc poscd posce poscf
#posd0 posd1 posd2 posd3 posd4 posd5 posd6 posd7 posd8 posd9 posda posdb posdc posdd posde posdf
#pose0 pose1 pose2 pose3 pose4 pose5 pose6 pose7 pose8 pose9 posea poseb posec posed posee posef
#posf0 posf1 posf2 posf3 posf4 posf5 posf6 posf7 posf8 posf9 posfa posfb posfc posfd posfe posff





def main():
    #motor0()
    motor1()
    #motor2()
    #motor3()
    pass


if __name__ == "__main__":
    main()

