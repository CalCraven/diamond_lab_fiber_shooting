from core.module import Base
from interface.empty_interface import EmptyInterface
import serial
from threading import Timer


class arduino_hardware(Base, EmptyInterface):
    """
    This is the Interface class to define the controls for the arduino
    """
    _modclass = 'EmptyInterface'
    _modtype = 'hardware'

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)
        self.log.info('The following configuration was found.')
        # checking for the right configuration
        for key in config.keys():
            self.log.info('{0}: {1}'.format(key, config[key]))

    def on_activate(self):
        """
        Initialisation performed during activation of the module.
        """
        self.port = 'COM5'
        self.baud_rate=115200
        self.timeout = 0.2
        self.connect_arduino()
        self.F_CPU = 16e6
        self.TOP = 3199
        self.CM = 0
        if self.connected:
            self.setfreq(5000)
            self.setduty(.01)
        self.lasing = False
        self.timer = Timer(0, None)
        return

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        self.disconnect_arduino()
        return

    def connect_arduino(self):
        self.arduino = serial.Serial(port=self.port, baudrate=self.baud_rate, timeout=self.timeout)
        self.duty = 0.
        self.connected = True

    def disconnect_arduino(self):
        if self.arduino:
            self.arduino.close()

    def setTOP(self, top):
        self.TOP = top
        self.arduino.write(('f_%d;' % self.TOP).encode())

    def setCM(self, cm):
        self.CM = cm
        self.arduino.write(('d_%d;' % self.CM).encode())


    def setfreq(self, freq):
        top = int(round(self.F_CPU / float(freq) - 1))
        self.setTOP(top)
        # print 'setting TOP = {0:d} (f = {1:.2f} kHz)'.format(top, F_CPU / (TOP + 1) / 1000.)

    def setduty(self, duty):
        cm = int(round(duty * (self.TOP + 1) - 1))
        self.setCM(cm)
        # print 'setting CM = {0:d} (duty = {1:.2f}%)'.format(cm, 100. * (CM + 1) / (TOP + 1))

    def open_shutter(self, shutter, duration):
        self.arduino.write(('s{0:d}{1:d};'.format(shutter, duration)).encode())

    def open_shutter_micro(self, shutter, duration):
        self.arduino.write(('S{0:d},{1:d};'.format(shutter, duration)).encode())

    def toggle_shutter(self, shutter):
        self.arduino.write('t{0:d}9;'.format(shutter).encode())  # extra integer needed for

    def change_duty(self, duty):
        self.duty = duty
        if self.lasing:
            self.setduty(duty)
