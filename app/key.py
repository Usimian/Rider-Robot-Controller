import lgpio
import time, os

_chip = lgpio.gpiochip_open(0)

class Button:
    def __init__(self):
        self.key1 = 24
        self.key2 = 23
        self.key3 = 17
        self.key4 = 22
        for pin in [self.key1, self.key2, self.key3, self.key4]:
            lgpio.gpio_claim_input(_chip, pin, lgpio.SET_PULL_UP)

    def press_a(self):
        if lgpio.gpio_read(_chip, self.key1):
            return False
        while not lgpio.gpio_read(_chip, self.key1):
            time.sleep(0.02)
        return True

    def press_b(self):
        if lgpio.gpio_read(_chip, self.key2):
            return False
        while not lgpio.gpio_read(_chip, self.key2):
            time.sleep(0.02)
        os.system('pkill mplayer')
        return True

    def press_c(self):
        if lgpio.gpio_read(_chip, self.key3):
            return False
        while not lgpio.gpio_read(_chip, self.key3):
            time.sleep(0.02)
        return True

    def press_d(self):
        if lgpio.gpio_read(_chip, self.key4):
            return False
        while not lgpio.gpio_read(_chip, self.key4):
            time.sleep(0.02)
        return True
