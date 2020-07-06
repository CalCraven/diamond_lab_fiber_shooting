import visa
from ThorlabsPM100.ThorlabsPM100 import ThorlabsPM100
from core.module import Base
from interface.empty_interface import EmptyInterface

class PowerMeterPM100AHardware(Base, EmptyInterface):
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
        self.rm = visa.ResourceManager()
        # to know the usb address of the power meter, uncomment this line and run the hardware file
        print(self.rm.list_resources())
        try:
            self.inst = self.rm.open_resource('USB0::0x1313::0x8079::P1002063::INSTR')
            # self.inst = self.rm.open_resource('USB0::0x1313::0x8079::P1004028::INSTR')
            self.power_meter = ThorlabsPM100(inst=self.inst)
            print('Power meter connected')
            self.connected = True
        except visa.VisaIOError:
            print('Failed to connect to powermeter. Check if it is ON, or if its usb address is correct.')
            self.connected = False
        return

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        # Switch console from remote to local mode
        self.power_meter._inst.control_ren(6)
        # Release ResourceManager
        self.rm.close()
        return

    def get_power(self):
        return self.power_meter.read
