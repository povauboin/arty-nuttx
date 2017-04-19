#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# LambdaConcept - 2017
# Pierre-Olivier Vauboin - po@lambdaconcept.com

from litex.gen import *
from litex.soc.interconnect.csr import *

class PWM(Module):
    def __init__(self, out, level):

        counter = Signal(12) # Just to reduce brightness

        self.comb += [
            If(counter < level,
                out.eq(1),
            ).Else(
                out.eq(0),
            ),
        ]

        self.sync += [
            counter.eq(counter + 1),
        ]

class RGBLeds(Module, AutoCSR):
    def __init__(self, pads):

        self.leds = pads

        self.csr_led0 = CSRStorage(24)
        self.csr_led1 = CSRStorage(24)
        self.csr_led2 = CSRStorage(24)
        self.csr_led3 = CSRStorage(24)

        for i in range(4):
            csr_led = getattr(self, 'csr_led{}'.format(i))

            self.submodules += PWM(self.leds.r[i], csr_led.storage[16:24])
            self.submodules += PWM(self.leds.g[i], csr_led.storage[8:16])
            self.submodules += PWM(self.leds.b[i], csr_led.storage[0:8])
