"""

Qudi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Qudi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Qudi. If not, see <http://www.gnu.org/licenses/>.

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

import time
import numpy as np
from qtpy import QtCore

from core.module import Base
from interface.empty_interface import EmptyInterface
from core.module import Connector, ConfigOption, StatusVar
from core.util.mutex import Mutex
import threading

class fiber_shooting_logic(Base, EmptyInterface):

    """This is the Interface class to define the controls for the simple
    microwave hardware.
    """
    _modclass = 'fiber_shooting_logic'
    _modtype = 'logic'

    # connectors
    TiS_camera_hardware = Connector(interface='EmptyInterface')
    arduino_hardware = Connector(interface='EmptyInterface')
    power_meter_hardware = Connector(interface='EmptyInterface')

    sigPowerUpdated = QtCore.Signal()
    sigPowerDataNext = QtCore.Signal()

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._TiS_camera_hardware = self.get_connector('TiS_camera_hardware')
        self._arduino_hardware = self.get_connector('arduino_hardware')
        self._power_meter_hardware = self.get_connector('power_meter_hardware')

        # Flipper variable
        self.flipper_opened = False

        # Thread
        self.threadlock = Mutex()
        self.sigPowerDataNext.connect(self.set_power, QtCore.Qt.QueuedConnection)

        # Laser
        self.duty_cycle = 0
        self.frequency = 5000

        # PID
        self.PID_status = False
        self.ramp_status = False
        self.setpoint = 0.
        self.polarity = 1
        self.Kp, self.Ki, self.Kd = 2, 1, 0.3
        self.min_PID_out, self.max_PID_out = 0., 0.4
        self.ramping_factor = 0.01
        self.offset = 0
        self.error_P_prev = 0.
        self.error_P = 0
        self.error_I = 0
        self.error_D = 0
        self.output = 0
        self.time_loop = []
        return



    def on_deactivate(self):
        self._TiS_camera_hardware.on_deactivate()
        self._arduino_hardware.on_desactivate()
        self._power_meter_hardware.on_desactivate()
        self.set_duty_cycle(0)
        self.sigPowerDataNext.disconnect()
        return

    def reset_hardware(self):
        """ Resets the hardware, so the connection is lost and other programs can access it.
        """
        self.on_desactivate()
        pass

#################################################### Camera ############################################################

    def setup_camera(self):
        self._TiS_camera_hardware.setup_camera()

    def start_video(self):
        self._TiS_camera_hardware.start_video_thread()

    def stop_video(self):
        self._TiS_camera_hardware.set_video_status(False)

    def get_cross_value(self):
        return self._TiS_camera_hardware.get_cross_value()

    def get_cladding_value(self):
        return self._TiS_camera_hardware.get_cladding_value()

    def get_core_value(self):
        return self._TiS_camera_hardware.get_core_value()

    def get_jacket_value(self):
        return self._TiS_camera_hardware.get_core_value()

    def set_cross_value(self, value):
        self._TiS_camera_hardware.set_cross_value(value)

    def set_jacket_value(self, value):
        self._TiS_camera_hardware.set_jacket_value(value)

    def set_cladding_value(self, value):
        self._TiS_camera_hardware.set_cladding_value(value)

    def set_core_value(self, value):
        self._TiS_camera_hardware.set_core_value(value)

    def set_edge_detection_value(self, value):
        self._TiS_camera_hardware.set_edge_detection_value(value)

    def set_zoom_factor(self, value):
        self._TiS_camera_hardware.set_zoom_factor(value)

    def get_zoom_factor(self):
        return self._TiS_camera_hardware.get_zoom_factor()

    def set_edge_min(self, value):
        self._TiS_camera_hardware.set_edge_min(value)

    def get_edge_min(self):
        return self._TiS_camera_hardware.get_edge_min()

    def set_edge_max(self, value):
        self._TiS_camera_hardware.set_edge_max(value)

    def get_edge_max(self):
        return self._TiS_camera_hardware.get_edge_max()

    def get_edge_detection_value(self):
        return self._TiS_camera_hardware.get_edge_detection_value()

#################################################### Flipper ###########################################################

    def open_flipper(self):
        self._arduino_hardware.toggle_shutter(0)

#################################################### Shutter ###########################################################

    def open_shutter(self):
        self._arduino_hardware.toggle_shutter(1)

    def send_pulse(self, duration):
        self._arduino_hardware.open_shutter_micro(1, int(duration*1e3))

################################################## CO2 Laser ###########################################################

    def set_duty_cycle(self, duty_cycle):
        self.duty_cycle = duty_cycle
        self._arduino_hardware.setduty(self.duty_cycle)

    def get_duty_cycle(self):
        return self.duty_cycle

    def set_frequency(self, frequency):
        self.frequency = frequency
        self._arduino_hardware.setfreq(self.frequency)

    def get_frequency(self):
        return self.frequency

    def set_setpoint(self, setpoint):
        self.setpoint = setpoint

    def get_setpoint(self):
        return self.setpoint

    def set_PID_status(self, bool):
        if bool == True:
            self.PID_status = True
        else:
            self.PID_status = False

    def get_PID_status(self):
        return self.PID_status

    def set_Kp(self, value):
        self.Kp = value

    def set_Ki(self, value):
        self.Ki = value

    def set_Kd(self, value):
        self.Kd = value

    def clear_I(self):
        self.error_I = 0

    def set_ramp_status(self,bool):
        if bool == True:
            self.ramp_status = True
        else:
            self.ramp_status = False

    def set_power(self):
        '''Set the duty cycle with or without PID'''
        # with self.threadlock:
        # measure power an the time
        self.power = self.get_power()
        self.time_loop.append(time.time())
        # We delete the useless data in order to not saturate the memory
        if len(self.time_loop) > 2:
            del self.time_loop[0]
            if self.time_loop[-1] == self.time_loop[-2]:
                # If the time is the same for two loops then we call the function again
                pass
            else:
                # We update the power on the GUI
                self.sigPowerUpdated.emit()
                self.error = self.get_setpoint() - self.power
                if self.ramp_status == True:
                    if abs(self.error) > 1e-3:
                        self.offset = self.output
                        self.output += np.sign(self.error)*1e-4
                        self.set_duty_cycle(self.output)
                    else:
                        self.ramp_status = False
                        self.clear_I
                        self.PID_status = True
                elif self.PID_status == True:
                    delta_t = self.time_loop[-1] - self.time_loop[-2]
                    self.error_P = self.error
                    self.error_I += self.error * delta_t
                    self.error_D = (self.error - self.error_P_prev) / delta_t
                    P = self.Kp * self.error_P
                    I = self.Ki * self.error_I
                    D = self.Kd * self.error_D
                    PID_out = self.polarity * (P + I + D/100)
                    correction = self.offset + PID_out
                    if correction >= self.max_PID_out:
                        self.output = self.max_PID_out
                    elif correction <= self.min_PID_out:
                        self.output = self.min_PID_out
                    else:
                        self.output = correction
                    self.set_duty_cycle(self.output)
                else:
                    self.set_duty_cycle(self.duty_cycle)
        self.sigPowerDataNext.emit()

################################################## Power Meter #########################################################

    def get_power(self):
        power_data = self._power_meter_hardware.power_meter.read
        return power_data




