from ctypes import cdll,c_long, c_ulong, c_uint32,byref,create_string_buffer,c_bool,c_char_p,c_int,c_int16,c_double, sizeof, c_voidp
from hardware.Thorlabs_PM101.TLPM import TLPM
from core.module import Base
from interface.empty_interface import EmptyInterface


# Definition of type ViReal64 used in visatype.h
# This is just a synonym for c_double
class ViReal64(c_double):
    pass

class Thorlabs_Powermeter(Base, EmptyInterface):
    """
    This is the Interface class to define the controls for the simple
    microwave hardware.
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

        self.connected = False
        # Account for the beamsplitter ratio:
        self.beam_splitter_coef = 1 # BS * setup transmission

        # List all connected powermeters
        self.power_meter = TLPM()
        deviceCount = c_uint32()
        self.power_meter.findRsrc(byref(deviceCount))
        print(f"Found {deviceCount.value} Thorlabs powermeter(s):")
        resourceName = create_string_buffer(1024)
        for i in range(0, deviceCount.value):
            self.power_meter.getRsrcName(c_int(i), resourceName)
            print(resourceName.value.decode("utf-8"))

        # Openning a particular device
        # PM100A from AttoCube lab:
        #resourceName = create_string_buffer(b'USB0::0x1313::0x8079::P1002063::INSTR')
        # PM100A from Diamond lab:
        #resourceName = create_string_buffer(b'USB0::0x1313::0x8079::P1004028::INSTR')
        # PM101R from CO2 laser:
        resourceName = create_string_buffer(b'USB0::0x1313::0x8076:: M00579483::INSTR')
        print("Openning device", resourceName.value.decode("utf-8"))
        try:
            failed = self.power_meter.open(resourceName, c_bool(True), c_bool(False))
            if failed:
                raise
            self.connected = True
            print("Device opened successfully")
            message = create_string_buffer(1024)
            self.power_meter.getCalibrationMsg(message)
            print("Calibration info:", message.value.decode("utf-8"))
            # Setting up parameters
            result = self.power_meter.setWavelength(ViReal64(10600))  # in nm
            result += self.power_meter.setPowerAutoRange(1)  # 0 = disable, 1 = enable
            #result += self.power_meter.setPowerRange(ViReal64(3.2))  # max power in W
            result += self.power_meter.setPowerUnit(0)  # 0 = W, 1 = dBm
            if result != 0:
                print("Warning! Could not set wavelength and/or power range")
        except:
            print('Failed to connect to powermeter. Make sure it is ON, its usb address is correct, and the assigned driver is TLPM (not PM100D).')
        return


    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        # Release the powermeter
        if self.connected:
            self.power_meter.close()
        return

    def get_power(self):
        if self.connected:
            power = c_double()
            self.power_meter.measPower(byref(power))
            return power.value * self.beam_splitter_coef
        else:
            return 0
