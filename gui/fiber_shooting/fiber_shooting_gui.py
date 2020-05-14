# -*- coding: utf-8 -*-

import os
import time
from core.module import Connector
from gui.guibase import GUIBase
from gui.colordefs import QudiPalettePale as Palette
from qtpy import QtWidgets
from qtpy import uic
import pyqtgraph as pg


class MainWindow(QtWidgets.QMainWindow):
    """ Create the Main Window based on the corresponding *.ui file. """

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'fiber_shooting_GUI.ui')
        self._doubleclicked = False

        # Load it
        super(MainWindow, self).__init__()
        uic.loadUi(ui_file, self)
        self.show()
        self.move(280, 0)


class FiberShootingGui(GUIBase):
    """ Main Gui Class for fiber shooting experiment."""
    _modclass = 'fiber_shooting_GUI'
    _modtype = 'gui'

    # declare connectors
    fiber_shooting_logic = Connector(interface='EmptyInterface')

    def show(self):
        """Make main window visible and put it above all other windows. """
        # Show the Main Confocal GUI:
        self._mw.show()
        self._mw.activateWindow()
        self._mw.raise_()

    def on_activate(self):
        """ Initializes all needed UI files and establishes the connectors.

        This method executes the all the inits for the differnt GUIs and passes
        the event argument from fysom to the methods.
        """
        # Getting an access to all connectors:
        self._fiber_shooting_logic = self.fiber_shooting_logic()
        self.init_main_ui()  # initialize the main GUI

    def init_main_ui(self):
        """ Definition, configuration and initialisation of the confocal GUI.
        This init connects all the graphic modules, which were created in the
        *.ui file and configures the event handling between the modules.
        Moreover it sets default values.
        """
        self._mw = MainWindow()

        self.laser_status = False  # Laser OFF

        self.power_data = []
        self.time_data = []
        self._pw = None
        self.curve = []

        self.acquisition_time = 60
        self.beam_splitter_coef = 29.5/93.0 # 0.15/0.85

        self.time_start = 0

        self.laser_status = False
        self.setpoint = 0

        # Adjust GUI Parameters
        self._mw.cross_radioButton.setChecked(self._fiber_shooting_logic.is_cross())
        self._mw.core_radioButton.setChecked(self._fiber_shooting_logic.is_core())
        self._mw.cladding_radioButton.setChecked(self._fiber_shooting_logic.is_cladding())
        self._mw.jacket_radioButton.setChecked(self._fiber_shooting_logic.is_jacket())
        self._mw.edge_detection_radioButton.setChecked(self._fiber_shooting_logic.is_edge_detection())
        self._mw.zoom_comboBox.addItems(['0.58', '1', '2', '3', '4', '5', '6', '7'])
        self._mw.zoom_comboBox.setCurrentIndex(
            self._mw.zoom_comboBox.findText(str(self._fiber_shooting_logic.get_zoom_factor())))
        self._mw.edge_min_spinBox.setValue(self._fiber_shooting_logic.get_edge_min())
        self._mw.edge_max_spinBox.setValue(self._fiber_shooting_logic.get_edge_max())

        self._mw.flipper_open_checkBox.setChecked(False)
        self._mw.shutter_open_checkBox.setChecked(False)
        self._mw.laser_ON_checkBox.setChecked(False)

        self._mw.Kp_doubleSpinBox.setValue(self.get_kp())
        self._mw.Ki_doubleSpinBox.setValue(self.get_ki())
        self._mw.Kd_doubleSpinBox.setValue(self.get_kd())

        self._mw.frequency_spinBox.setValue(self._fiber_shooting_logic.get_frequency())
        self._mw.duty_cycle_doubleSpinBox.setValue(self._fiber_shooting_logic.get_duty_cycle())

        self._mw.acquisition_time_spinBox.setValue(10)

        # graph

        self._pw = self._mw.power_PlotWidget
        self._pw.setLabel('left', 'Power', units='W')
        self._pw.setLabel('bottom', 'Time', units='s')
        self._pw.showGrid(x=True, y=True)

        self.curve.append(pg.PlotDataItem(pen=pg.mkPen(Palette.c1), symbol=None))
        self._pw.addItem(self.curve[-1])
        self.curve.append(pg.InfiniteLine(pos=0, angle=0, pen=pg.mkPen(Palette.c2)))
        self._pw.addItem(self.curve[-1])

        # Camera's connectors
        self._mw.start_video_pushButton.clicked.connect(self.start_video)
        self._mw.stop_video_pushButton.clicked.connect(self.stop_video)
        self._mw.cross_radioButton.clicked.connect(self.camera_cross)
        self._mw.jacket_radioButton.clicked.connect(self.camera_jacket)
        self._mw.edge_detection_radioButton.clicked.connect(self.edge_detection)
        self._mw.cladding_radioButton.clicked.connect(self.camera_cladding)
        self._mw.core_radioButton.clicked.connect(self.camera_core)
        self._mw.zoom_comboBox.currentTextChanged.connect(self.set_zoom_factor)
        self._mw.edge_min_spinBox.valueChanged.connect(self.set_edge_min)
        self._mw.edge_max_spinBox.valueChanged.connect(self.set_edge_max)
        # Flipper's connectors
        self._mw.flipper_open_checkBox.clicked.connect(self.open_flipper)
        # Shutter's connectors
        self._mw.shutter_open_checkBox.clicked.connect(self.open_shutter)
        self._mw.shutter_pulse_pushButton.clicked.connect(self.send_pulse)
        # Laser's connectors
        self._mw.duty_cycle_doubleSpinBox.valueChanged.connect(self.set_duty_cycle)
        self._mw.frequency_spinBox.valueChanged.connect(self.set_frequency)
        self._mw.laser_ON_checkBox.clicked.connect(self.switch_laser)
        self._mw.PID_ON_checkBox.clicked.connect(self.set_pid_status)
        self._mw.setpoint_spinBox.editingFinished.connect(self.set_setpoint)
        self._mw.Kp_doubleSpinBox.editingFinished.connect(self.set_kp)
        self._mw.Ki_doubleSpinBox.editingFinished.connect(self.set_ki)
        self._mw.Kd_doubleSpinBox.editingFinished.connect(self.set_kd)
        # Graph's connectors
        self._mw.acquisition_time_spinBox.editingFinished.connect(self.set_acquisition_time)
        # Handling signals from the logic
        self._fiber_shooting_logic.sigPowerUpdated.connect(self.update_data)

    def on_deactivate(self):
        """ Reverse steps of activation """
        self._mw.close()
        return

    # Camera's methods

    def setup_camera(self):
        """Set the property of the camera so that it is ready to run
        """
        self._fiber_shooting_logic.setup_camera()
        return

    def start_video(self):
        """Start the capture of the camera
        """
        self._fiber_shooting_logic.start_video()
        return

    def stop_video(self):
        """Stop the capture of the camera"""
        self._fiber_shooting_logic.stop_video()
        return

    def camera_cross(self):
        """ Make the target appearing on the camera picture"""
        self._fiber_shooting_logic.set_cross(self._mw.cross_radioButton.isChecked())

    def camera_jacket(self):
        """ Make the fiber jacket diameter appearing on the camera picture"""
        self._fiber_shooting_logic.set_jacket(self._mw.jacket_radioButton.isChecked())

    def camera_cladding(self):
        """ Make the fiber cladding diameter appearing on the camera picture"""
        self._fiber_shooting_logic.set_cladding(self._mw.cladding_radioButton.isChecked())

    def camera_core(self):
        """ Make the fiber core diameter appearing on the camera picture"""
        self._fiber_shooting_logic.set_core(self._mw.core_radioButton.isChecked())

    def set_zoom_factor(self, value):
        """ Modify the diameter of the fiber jacket, cladding and core with respect to the zoom set on the camera
        imaging system. """
        self._fiber_shooting_logic.set_zoom_factor(float(value))
        return

    def set_edge_min(self):
        """ Set the minimum for pixels so that a edge is detected. """
        self._fiber_shooting_logic.set_edge_min((self._mw.edge_min_spinBox.value()))
        return

    def get_edge_min(self):
        """ Get edge_min value. """
        return self._fiber_shooting_logic.get_edge_min()

    def set_edge_max(self):
        """Set the maximum for pixels so that a edge is detected"""
        self._fiber_shooting_logic.set_edge_max(self._mw.edge_max_spinBox.value())
        return

    def get_edges_max(self):
        """ Get edge_max value. """
        return self._fiber_shooting_logic.get_edge_max()

    def edge_detection(self):
        """ Activate the edge detection on the camera capture. """
        if self._mw.edge_detection_radioButton.isChecked():
            self._fiber_shooting_logic.set_edge_detection(1)
        else:
            self._fiber_shooting_logic.set_edge_detection(0)
        return

    #  Flipper's methods

    def open_flipper(self):
        """Open/Close the flip flop mirror"""
        self._fiber_shooting_logic.open_flipper()
        return

    # Shutter's methods

    def open_shutter(self):
        """Open/Close the shutter"""
        self._fiber_shooting_logic.open_shutter()
        return

    def send_pulse(self):
        """Open the shutter for a duration specified on the GUI"""
        self._fiber_shooting_logic.send_pulse(self._mw.shutter_time_spinBox.value())
        return

    # Laser's methods

    def switch_laser(self):
        """ Switch on the laser output and start time of registering data from the power meter"""
        if self._mw.laser_ON_checkBox.isChecked():
            self.time_start = time.time()
            self._fiber_shooting_logic.set_duty_cycle(self._mw.duty_cycle_doubleSpinBox.value())
            self.power_data = []
            self.time_data = []
            self._fiber_shooting_logic.set_power()
            self.laser_status = True
        else:
            self._fiber_shooting_logic.set_duty_cycle(0)
            self.laser_status = False
        return

    def set_duty_cycle(self):
        """ Set the duty_cycle of the laser pulses"""
        if self.laser_status:
            self._fiber_shooting_logic.set_duty_cycle(self._mw.duty_cycle_doubleSpinBox.value())
        else:
            pass
        return

    def set_frequency(self):
        """ Set the frequency of the laser pulses """
        if self.laser_status:
            self._fiber_shooting_logic.set_frequency(self._mw.frequency_spinBox.value())
        else:
            pass
        return

    def set_setpoint(self):
        """Set the laser output power set-point"""
        self.setpoint = self._mw.setpoint_spinBox.value() / self.beam_splitter_coef * 1e-3
        print(self.setpoint)
        self._fiber_shooting_logic.set_setpoint(self.setpoint)
        self.curve[1].setValue(self.setpoint * self.beam_splitter_coef)
        if self._fiber_shooting_logic.is_pid_status():
            self._fiber_shooting_logic.set_ramp_status(True)
            self._fiber_shooting_logic.set_pid_status(False)
        else:
            pass
        return

    def set_pid_status(self):
        """Set the PID power lock ON/OFF"""
        if self._mw.PID_ON_checkBox.isChecked():
            self._fiber_shooting_logic.set_ramp_status(True)
            self._fiber_shooting_logic.set_pid_status(False)
            self._mw.duty_cycle_doubleSpinBox.setReadOnly(True)
        else:
            self._fiber_shooting_logic.set_ramp_status(False)
            self._fiber_shooting_logic.set_pid_status(False)
            self._mw.duty_cycle_doubleSpinBox.setReadOnly(False)
        return

    def set_kp(self):
        """ Set the proportional factor of the PID """
        self._fiber_shooting_logic.set_kp(self._mw.Kp_doubleSpinBox.value())
        return

    def get_kp(self):
        """ Get the proportional factor of the PID """
        return self._fiber_shooting_logic.kp

    def set_ki(self):
        """ Set the integral factor of the PID """
        self._fiber_shooting_logic.set_ki(self._mw.Ki_doubleSpinBox.value())
        return

    def get_ki(self):
        """ Get the integral factor of the PID """
        return self._fiber_shooting_logic.ki

    def set_kd(self):
        """ Set the derivative factor of the PID """
        self._fiber_shooting_logic.set_kd(self._mw.Kd_doubleSpinBox.value())
        return

    def get_kd(self):
        """ Get the derivative factor of the PID """
        return self._fiber_shooting_logic.kd

    # Graph's methods

    def update_data(self):
        """ Get the data from the logic and update the graph on the gui """
        self.time_data.append(self._fiber_shooting_logic.time_loop[-1] - self.time_start)
        self.power_data.append(self._fiber_shooting_logic.power * self.beam_splitter_coef)
        self._mw.duty_cycle_doubleSpinBox.setValue(self._fiber_shooting_logic.get_duty_cycle())
        if self.time_data[-1] > int(self._mw.acquisition_time_spinBox.value()):
            # If the len of the data is over a define value
            del self.time_data[0]
            del self.power_data[0]
        self.curve[0].setData(y=self.power_data, x=self.time_data)
        return

    def set_acquisition_time(self):
        """ Set the acquisition time length of the plot on the GUI. """
        self.acquisition_time = self._mw.acquisition_time_spinBox.value()
        return

    def get_acquisition_time(self):
        """ Get the acquisition time length of the plot on the GUI. """
        return self.acquisition_time
