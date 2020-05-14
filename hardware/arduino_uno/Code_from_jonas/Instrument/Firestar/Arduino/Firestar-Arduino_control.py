# -*- coding: utf-8 -*-
"""
Created on Thu Mar 15 15:21:35 2012

@author: jsne
"""

import serial
from datetime import datetime as dt

com_port = 'COM5'
baud_rate = 9600
pwm_period = 150  # in us

class Controller():
    def __init__(self):
        self.start()
    
    def start(self):
        try:
            self.s = serial.Serial(com_port, baud_rate)
            print "Connected on", com_port
        except serial.serialutil.SerialException:
            print "Could not initiate serial connection"
        
    
    def blink(self, us, pulses):
        comm = '%03d%09d' % (us, pulses)
        self.s.write(comm)
        print "-= %s =-" % dt.now().strftime('%H:%M:%S')
        print "Command: %s  (%d pulses of %d us length)" % (comm, pulses, us)
        print "         --> %.3f sec | ~ %.3f W" % \
               (pulses * pwm_period * 1e-6, us2power(us))
    
    def on(self, us, secs):
        pulses = secs * 1e6 / float(pwm_period)
        self.blink(us, pulses)
    
    def end(self):
        self.s.close()
        
        
def us2power(us):
    """
    Conversion of PWM pulse length to rough laser power.
    Assuming a linear correspondence, which is not exactly correct. Based on
    results from 2012-04-03 and 2012-03-29.
    """
    transmission = 0.157  # transmission of partial reflector
    slope = 0.55
    threshold= 4.8
    
    return transmission * slope * (us - threshold)