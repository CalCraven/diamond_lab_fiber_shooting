# -*- coding: utf-8 -*-

import numpy as np
import os
import pyqtgraph as pg
import time
import cv2

from core.module import Connector, ConfigOption, StatusVar
from gui.guibase import GUIBase
import threading
from gui.guiutils import ColorBar
from gui.colordefs import ColorScaleInferno
from gui.colordefs import QudiPalettePale as palette
from gui.fitsettings import FitParametersWidget
from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets
from qtpy import uic
import pyqtgraph as pg



class fiber_shooting_GUI_Window(QtWidgets.QMainWindow):

    """ Create the Mainwindow based on the corresponding *.ui file. """

    sigPressKeyBoard = QtCore.Signal(QtCore.QEvent)
    sigDoubleClick = QtCore.Signal()

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'fiber_shooting_GUI.ui')
        self._doubleclicked = False

        # Load it
        super(fiber_shooting_GUI_Window, self).__init__()
        uic.loadUi(ui_file, self)
        self.show()

    def keyPressEvent(self, event):
        """Pass the keyboard press event from the main window further. """
        self.sigPressKeyBoard.emit(event)

    def mouseDoubleClickEvent(self, event):
        self._doubleclicked = True
        self.sigDoubleClick.emit()

class fiber_shooting_GUI(GUIBase):

    """ Main Confocal Class for xy and depth scans.
    """
    _modclass = 'fiber_shooting_GUI'
    _modtype = 'gui'


    # declare connectors
    fiber_shooting_logic = Connector(interface='EmptyInterface')

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

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
        self._fiber_shooting_logic = self.get_connector('fiber_shooting_logic')
        self.initMainUI()      # initialize the main GUI

    def initMainUI(self):
        """ Definition, configuration and initialisation of the confocal GUI.
        This init connects all the graphic modules, which were created in the
        *.ui file and configures the event handling between the modules.
        Moreover it sets default values.
        """
        self._mw = fiber_shooting_GUI_Window()

        # Adjust GUI Parameters
        self._mw.cross_radioButton.setChecked(self._fiber_shooting_logic.get_cross_value())
        self._mw.core_radioButton.setChecked(self._fiber_shooting_logic.get_core_value())
        self._mw.cladding_radioButton.setChecked(self._fiber_shooting_logic.get_cladding_value())
        self._mw.jacket_radioButton.setChecked(self._fiber_shooting_logic.get_jacket_value())
        self._mw.edge_detection_radioButton.setChecked(self._fiber_shooting_logic.get_edge_detection_value())
        self._mw.zoom_comboBox.addItems(['0.58', '1', '2', '3', '4', '5', '6', '7'])
        self._mw.zoom_comboBox.setCurrentIndex(self._mw.zoom_comboBox.findText(str(self._fiber_shooting_logic.get_zoom_factor())))
        self._mw.edge_min_spinBox.setValue(self._fiber_shooting_logic.get_edge_min())
        self._mw.edge_max_spinBox.setValue(self._fiber_shooting_logic.get_edge_max())

        self._mw.flipper_open_checkBox.setChecked(False)
        self._mw.shutter_open_checkBox.setChecked(False)
        self._mw.laser_ON_checkBox.setChecked(False)
        self.laser_status = False # Laser off

        self._mw.Kp_doubleSpinBox.setValue(self.get_Kp())
        self._mw.Ki_doubleSpinBox.setValue(self.get_Ki())
        self._mw.Kd_doubleSpinBox.setValue(self.get_Kd())

        self._mw.frequency_spinBox.setValue(self._fiber_shooting_logic.get_frequency())
        self._mw.duty_cycle_doubleSpinBox.setValue(self._fiber_shooting_logic.get_duty_cycle())

        self._mw.acquisition_time_spinBox.setValue(10)

        # graph
        self.power_data = []
        self.time_data = []
        self._pw = self._mw.power_PlotWidget
        self._pw.setLabel('left', 'Power', units='W')
        self._pw.setLabel('bottom', 'Time', units='s')
        self._pw.showGrid(x=True, y=True)
        self.curve = []
        self.curve.append(pg.PlotDataItem(pen=pg.mkPen(palette.c1), symbol=None))
        self._pw.addItem(self.curve[-1])
        self.curve.append(pg.InfiniteLine(pos=0, angle=0, pen=pg.mkPen(palette.c2)))
        self._pw.addItem(self.curve[-1])
        self.aquisition_time = 60

        self.beam_splitter_reflectivity = 0.839

        # CONNECTORS
        # Camera
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
        # Flipper
        self._mw.flipper_open_checkBox.clicked.connect(self.open_flipper)
        # Shutter
        self._mw.shutter_open_checkBox.clicked.connect(self.open_shutter)
        self._mw.shutter_pulse_pushButton.clicked.connect(self.send_pulse)
        # Laser
        self._mw.duty_cycle_doubleSpinBox.valueChanged.connect(self.set_duty_cycle)
        self._mw.frequency_spinBox.valueChanged.connect(self.set_frequency)
        self._mw.laser_ON_checkBox.clicked.connect(self.switch_laser)
        self._mw.PID_ON_checkBox.clicked.connect(self.set_PID_status)
        self._mw.setpoint_spinBox.editingFinished.connect(self.set_setpoint)
        self._mw.Kp_doubleSpinBox.editingFinished.connect(self.set_Kp)
        self._mw.Ki_doubleSpinBox.editingFinished.connect(self.set_Ki)
        self._mw.Kd_doubleSpinBox.editingFinished.connect(self.set_Kd)
        # Graph
        self._mw.acquisition_time_spinBox.editingFinished.connect(self.set_acquisition_time)
        # Handling signals from the logic
        self._fiber_shooting_logic.sigPowerUpdated.connect(self.update_data)

    def on_deactivate(self):
        """ Reverse steps of activation

        @return int: error code (0:OK, -1:error)
        """
        self._mw.close()
        return 0

#################################################### Camera ############################################################

    def setup_camera(self):
        '''Set the property of the camera so that it is ready to run
        '''
        self._fiber_shooting_logic.setup_camera()

    def start_video(self):
        '''Start the capture of the camera
        '''
        self._fiber_shooting_logic.start_video()

    def stop_video(self):
        '''Stop the capture of the camera'''
        self._fiber_shooting_logic.stop_video()

    def camera_cross(self):
        ''' Make the target appearing on the camera picture'''
        if self._mw.cross_radioButton.isChecked() == True:
            self._fiber_shooting_logic.set_cross_value(1)
        else:
            self._fiber_shooting_logic.set_cross_value(0)

    def camera_jacket(self):
        ''' Make the fiber jacket diameter appearing on the camera picture'''
        if self._mw.jacket_radioButton.isChecked() == True:
            self._fiber_shooting_logic.set_jacket_value(1)
        else:
            self._fiber_shooting_logic.set_jacket_value(0)

    def camera_cladding(self):
        ''' Make the fiber cladding diameter appearing on the camera picture'''
        if self._mw.cladding_radioButton.isChecked() == True:
            self._fiber_shooting_logic.set_cladding_value(1)
        else:
            self._fiber_shooting_logic.set_cladding_value(0)

    def camera_core(self):
        ''' Make the fiber core diameter appearing on the camera picture
        '''
        if self._mw.core_radioButton.isChecked() == True:
            self._fiber_shooting_logic.set_core_value(1)
        else:
            self._fiber_shooting_logic.set_core_value(0)

    def set_zoom_factor(self, value):
        '''Modify the diameter of the fiber jacket, cladding and core with respect to the zoom set on the camera
        imaging system'''
        self._fiber_shooting_logic.set_zoom_factor(float(value))

    def set_edge_min(self, value):
        '''Set the minimum for pixels so that a edge is detected'''
        self._fiber_shooting_logic.set_edge_min((self._mw.edge_min_spinBox.value()))

    def get_edge_min(self):
        '''Get edge_min value'''
        return self._fiber_shooting_logic.get_edge_min()

    def set_edge_max(self):
        '''Set the maximum for pixels so that a edge is detected'''
        self._fiber_shooting_logic.set_edge_max(self._mw.edge_max_spinBox.value())

    def get_edges_max(self):
        '''Get edge_max value'''
        return self._fiber_shooting_logic.get_edge_max()

    def edge_detection(self):
        '''Activate the edge detection on the camera capture'''
        if self._mw.edge_detection_radioButton.isChecked() == True:
            self._fiber_shooting_logic.set_edge_detection_value(1)
        else:
            self._fiber_shooting_logic.set_edge_detection_value(0)

#################################################### Flipper ###########################################################

    def open_flipper(self):
        '''Open/Close the flip flop mirror'''
        self._fiber_shooting_logic.open_flipper()

#################################################### Shutter ###########################################################

    def open_shutter(self):
        '''Open/Close the shutter'''
        self._fiber_shooting_logic.open_shutter()

    def send_pulse(self):
        '''Open the shutter for a duration specified on the GUI'''
        self._fiber_shooting_logic.send_pulse(self._mw.shutter_time_spinBox.value())

##################################################### Laser ############################################################

    def switch_laser(self):
        ''' Switch on the laser output and start time of registering data from the power meter'''
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

    def set_duty_cycle(self):
        ''' Set the duty_cycle of the laser pulses'''
        if self.laser_status == True:
            self._fiber_shooting_logic.set_duty_cycle(self._mw.duty_cycle_doubleSpinBox.value())
        else:
            pass

    def set_frequency(self):
        '''Set the frequency of the laser pulses'''
        if self.laser_status == True:
            self._fiber_shooting_logic.set_frequency(self._mw.frequency_spinBox.value())
        else:
            pass

    def set_setpoint(self):
        '''Set the laser output power set-point'''
        self.setpoint = self._mw.setpoint_spinBox.value()*(1-self.beam_splitter_reflectivity)*1e-3
        self._fiber_shooting_logic.set_setpoint(self.setpoint)
        self.curve[1].setValue(self.setpoint/(1-self.beam_splitter_reflectivity))
        if self._fiber_shooting_logic.get_PID_status() == True:
            self._fiber_shooting_logic.set_ramp_status(True)
            self._fiber_shooting_logic.set_PID_status(False)
        else:
            pass

    def set_PID_status(self):
        '''Set the PID power lock ON/OFF'''
        if self._mw.PID_ON_checkBox.isChecked():
            self._fiber_shooting_logic.set_ramp_status(True)
            self._fiber_shooting_logic.set_PID_status(False)
            self._mw.duty_cycle_doubleSpinBox.setReadOnly(True)
        else:
            self._fiber_shooting_logic.set_ramp_status(False)
            self._fiber_shooting_logic.set_PID_status(False)
            self._mw.duty_cycle_doubleSpinBox.setReadOnly(False)

    def set_Kp(self):
        self._fiber_shooting_logic.set_Kp(self._mw.Kp_doubleSpinBox.value())

    def get_Kp(self):
        return self._fiber_shooting_logic.Kp

    def set_Ki(self):
        self._fiber_shooting_logic.set_Ki(self._mw.Ki_doubleSpinBox.value())

    def get_Ki(self):
        return self._fiber_shooting_logic.Ki

    def set_Kd(self):
        self._fiber_shooting_logic.set_Kd(self._mw.Kd_doubleSpinBox.value())

    def get_Kd(self):
        return self._fiber_shooting_logic.Kd



##################################################### Graph ############################################################

    def update_data(self):
        self.time_data.append(self._fiber_shooting_logic.time_loop[-1]-self.time_start)
        self.power_data.append(self._fiber_shooting_logic.power/(1-self.beam_splitter_reflectivity))
        self._mw.duty_cycle_doubleSpinBox.setValue(self._fiber_shooting_logic.get_duty_cycle())
        if self.time_data[-1] > int(self._mw.acquisition_time_spinBox.value()):
            del self.time_data[0]
            del self.power_data[0]
            # print(np.average(self.power_data))
        self.curve[0].setData(y=self.power_data, x=self.time_data)

    def set_acquisition_time(self):
        self.aquisition_time = self._mw.acquisition_time_spinBox.value()

    def get_acquisition_time(self):
        return self.aquisition_time
