from core.module import Base
from interface.empty_interface import EmptyInterface
import serial
from threading import Timer


class ArduinoHardware(Base, EmptyInterface):
    """ This is the Interface class to define the controls for the arduino. """

    _modclass = 'EmptyInterface'
    _modtype = 'hardware'

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)
        self.log.info('The following configuration was found.')
        # checking for the right configuration
        for key in config.keys():
            self.log.info('{0}: {1}'.format(key, config[key]))

        self.arduino = None
        self.lasing = False
        self.timer = None
        self.connected = False
        self.duty = 0.

        self.port = 'COM3'
        self.baud_rate = 115200
        self.timeout = 0.2
        self.connect_arduino()
        self.F_CPU = 16e6
        self.TOP = 3199
        self.CM = 0

    def on_activate(self):
        """ Initialisation performed during activation of the module. """
        if self.connected:
            self.set_freq(5000)
            self.set_duty(.01)
        self.timer = Timer(0, None)
        return

    def on_deactivate(self):
        """ De-initialisation performed during deactivation of the module. """
        self.disconnect_arduino()
        return

    def connect_arduino(self):
        """ Connect the arduino. """
        self.arduino = serial.Serial(port=self.port, baudrate=self.baud_rate, timeout=self.timeout)
        self.duty = 0.
        self.connected = True
        return

    def disconnect_arduino(self):
        """ Connect the arduino. """
        if self.arduino:
            self.arduino.close()
        return

    def set_top(self, top):
        """ Set top parameter of the arduino """
        self.TOP = top
        self.arduino.write(('f_%d;' % self.TOP).encode())
        return

    def set_cm(self, cm):
        """ Set cm parameter of the arduino """
        self.CM = cm
        self.arduino.write(('d_%d;' % self.CM).encode())
        return

    def set_freq(self, freq):
        """ Set the laser frequency (kHz) """
        top = int(round(self.F_CPU / float(freq) - 1))
        self.set_top(top)
        # print 'setting TOP = {0:d} (f = {1:.2f} kHz)'.format(top, F_CPU / (TOP + 1) / 1000.)
        return

    def set_duty(self, duty):
        """ Set the laser duty cycle (float between 0 and 1) """
        cm = int(round(duty * (self.TOP + 1) - 1))
        self.set_cm(cm)
        # print 'setting CM = {0:d} (duty = {1:.2f}%)'.format(cm, 100. * (CM + 1) / (TOP + 1))
        return

    def open_shutter(self, shutter, duration):
        """ Send a voltage on the shutter channel that open the shutter. """
        self.arduino.write(('s{0:d}{1:d};'.format(shutter, duration)).encode())
        return

    def open_shutter_micro(self, shutter, duration):
        """ Send a voltage on the shutter channel that open/close the shutter with a certain duration
        (milli seconds). """
        self.arduino.write(('S{0:d},{1:d};'.format(shutter, duration)).encode())
        return

    def toggle_shutter(self, shutter):
        """ Send a voltage that open or close the toggle shutter. """
        self.arduino.write('t{0:d}9;'.format(shutter).encode())  # extra integer needed for
        return

    def change_duty(self, duty):
        """ Change the laser duty cycle (float between 0 and 1)"""
        self.duty = duty
        if self.lasing:
            self.set_duty(duty)
        return
