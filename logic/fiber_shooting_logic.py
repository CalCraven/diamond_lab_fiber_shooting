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
from core.module import Connector
from core.util.mutex import Mutex


class FiberShootingLogic(Base, EmptyInterface):

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

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)
        self._TiS_camera_hardware = None
        self._arduino_hardware = None
        self._power_meter_hardware = None
        # Flipper variable
        self.flipper_opened = False
        # Laser
        self.duty_cycle = 0
        self.frequency = 5000
        # PID
        self.pid_status = False
        self.ramp_status = False
        self.setpoint = 0.
        self.polarity = 1
        self.kp, self.ki, self.kd = 2, 1, 0.3
        self.min_pid_out, self.max_pid_out = 0., 0.4
        self.ramping_factor = 0.01
        self.offset = 0
        self.error_p_prev = 0.
        self.error_p = 0
        self.error_i = 0
        self.error_d = 0
        self.output = 0
        self.time_loop = []
        self.power = None
        self.error = None

        # Thread
        self.threadlock = Mutex()

    def on_activate(self):
        """ Initialisation performed during activation of the module. """
        self._TiS_camera_hardware = self.TiS_camera_hardware()
        self._arduino_hardware = self.arduino_hardware()
        self._power_meter_hardware = self.power_meter_hardware()

        self.sigPowerDataNext.connect(self.set_power, QtCore.Qt.QueuedConnection)
        return

    def on_deactivate(self):
        """  Performed during deactivation of the module. """
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

    # Camera

    def setup_camera(self):
        """ Setup the camera parameters. """
        self._TiS_camera_hardware.setup_camera()
        return

    def start_video(self):
        """ Start to capture camera frames. """
        self._TiS_camera_hardware.start_video_thread()
        return

    def stop_video(self):
        """ Stop to capture camera frames. """
        self._TiS_camera_hardware.set_video_status(False)
        return

    def is_cross(self):
        """ Return boolean to see if target cross is drawn or not on the camera streaming """
        return self._TiS_camera_hardware.is_cross()

    def is_cladding(self):
        """ Return boolean to see if the cladding of the fiber is drawn or not on the camera streaming """
        return self._TiS_camera_hardware.is_cladding()

    def is_core(self):
        """ Return boolean to see if the core of the fiber is drawn or not on the camera streaming """
        return self._TiS_camera_hardware.is_core()

    def is_jacket(self):
        """ Return boolean to see if the jacket of the fiber is drawn or not on the camera streaming """
        return self._TiS_camera_hardware.is_core()

    def set_cross(self, boolean):
        """ Set the cross drawn /not drawn on the camera video. """
        self._TiS_camera_hardware.set_cross(boolean)
        return

    def set_jacket(self, boolean):
        """ Set the jacket of the fiber drawn /not drawn on the camera video. """
        self._TiS_camera_hardware.set_jacket(boolean)
        return

    def set_cladding(self, boolean):
        """ Set the cladding of the fiber drawn /not drawn on the camera video. """
        self._TiS_camera_hardware.set_cladding(boolean)
        return

    def set_core(self, boolean):
        """ Set the core of the fiber drawn /not drawn on the camera video. """
        self._TiS_camera_hardware.set_core(boolean)
        return

    def set_edge_detection(self, value):
        """ Set the edge detection threshold on the camera video. """
        self._TiS_camera_hardware.set_edge_detection(value)
        return

    def is_edge_detection(self):
        """ Get the edge detection status the camera video. """
        return self._TiS_camera_hardware.is_edge_detection()

    def set_zoom_factor(self, value):
        """ Set the scale factor of the drawings on the video frames. """
        self._TiS_camera_hardware.set_zoom_factor(value)
        return

    def get_zoom_factor(self):
        """ Get the scale factor of the drawings on the video frames. """
        return self._TiS_camera_hardware.get_zoom_factor()

    def set_edge_min(self, value):
        """ Set the edge detection minimum threshold on the camera video. """
        self._TiS_camera_hardware.set_edge_min(value)
        return

    def get_edge_min(self):
        """ Get the edge detection minimum threshold on the camera video. """
        return self._TiS_camera_hardware.get_edge_min()

    def set_edge_max(self, value):
        """ Set the edge detection maximum threshold on the camera video. """
        self._TiS_camera_hardware.set_edge_max(value)
        return

    def get_edge_max(self):
        """ Get the edge detection maximum threshold on the camera video. """
        return self._TiS_camera_hardware.get_edge_max()

    # Flipper

    def open_flipper(self):
        """ Open the flipper. """
        self._arduino_hardware.toggle_shutter(0)
        return

    # Shutter

    def open_shutter(self):
        """ Open the shutter (permanently). """
        self._arduino_hardware.toggle_shutter(1)
        return

    def send_pulse(self, duration):
        """ Open/close the shutter with a certain duration (min : about 6 ms). """
        self._arduino_hardware.open_shutter_micro(1, int(duration*1e3))
        return

    # CO2 Laser

    def set_duty_cycle(self, duty_cycle):
        """ Set the duty cycle of the laser (between 0 and 1). """
        self.duty_cycle = duty_cycle
        self._arduino_hardware.set_duty(self.duty_cycle)

    def get_duty_cycle(self):
        """ Get the duty cycle of the laser. """
        return self.duty_cycle

    def set_frequency(self, frequency):
        """ Set the frequency of the laser (kHz). """
        self.frequency = frequency
        self._arduino_hardware.set_freq(self.frequency)
        return

    def get_frequency(self):
        """ Get the frequency of the laser"""
        return self.frequency

    def set_setpoint(self, setpoint):
        """ Set the power setpoint of the laser. """
        self.setpoint = setpoint
        return

    def get_setpoint(self):
        """ Get the power setpoint of the laser. """
        return self.setpoint

    def set_pid_status(self, boolean):
        """ Set the PID to True or False. """
        self.pid_status = boolean
        return

    def is_pid_status(self):
        """ Get the status of the PID (boolean). """
        return self.pid_status

    def set_kp(self, value):
        """ Set the proportional term of the PID. """
        self.kp = value
        return

    def set_ki(self, value):
        """ Set the integral term of the PID. """
        self.ki = value
        return

    def set_kd(self, value):
        """ Set the derivative term of the PID. """
        self.kd = value
        return

    def clear_integral(self):
        """ Clear the integral term of the PID. """
        self.error_i = 0
        return

    def set_ramp_status(self, boolean):
        """ Set the ramp status (True ot False).
        Used in order to increase the changes of laser power"""
        self.ramp_status = boolean
        return

    def set_power(self):
        """Set the duty cycle with or without PID"""
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
                if self.ramp_status:
                    if abs(self.error) > 1e-3:
                        self.offset = self.output
                        self.output += np.sign(self.error)*1e-4
                        self.set_duty_cycle(self.output)
                    else:
                        self.ramp_status = False
                        self.clear_integral()
                        self.pid_status = True
                elif self.pid_status:
                    delta_t = self.time_loop[-1] - self.time_loop[-2]
                    self.error_p = self.error
                    self.error_i += self.error * delta_t
                    self.error_d = (self.error - self.error_p_prev) / delta_t
                    p = self.kp * self.error_p
                    i = self.ki * self.error_i
                    d = self.kd * self.error_d
                    pid_out = self.polarity * (p + i + d/100)
                    correction = self.offset + pid_out
                    if correction >= self.max_pid_out:
                        self.output = self.max_pid_out
                    elif correction <= self.min_pid_out:
                        self.output = self.min_pid_out
                    else:
                        self.output = correction
                    self.set_duty_cycle(self.output)
                    self.error_p_prev = self.error_p
                else:
                    self.set_duty_cycle(self.duty_cycle)
        self.sigPowerDataNext.emit()
        return

    # Power Meter

    def get_power(self):
        """ Get the optical power measured by the power meter. """
        power_data = self._power_meter_hardware.power_meter.read
        return power_data
