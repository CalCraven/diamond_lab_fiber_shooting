import cv2
import threading
import numpy as np
from core.module import Base
from interface.empty_interface import EmptyInterface
import time

class TiS_Camera(Base, EmptyInterface):
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
        self.setup_camera()

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        # When everything done, release the capture
        self.cam.release()
        cv2.destroyWindow('Camera')
        return

    def setup_camera(self):
        self.cam = cv2.VideoCapture(0)
        self.ret, self.frame = self.cam.read()
        self.video_height, self.video_width, self.video_channels = self.frame.shape
        self.zoom_factor = 2
        self.real_height, self.real_width = np.array([4464, 5952]) / (9.52 * self.zoom_factor)
        self.edges = 1
        self.edge_min = 10
        self.edge_max = 200
        self.cross = 1
        self.cladding = 1
        self.jacket = 1
        self.core = 1
        self.pixel_size = self.real_width / self.video_width
        self.pixel_size_2 = self.real_height / self.video_height
        self.fiber_jacket_radius = 165/2  # um
        self.fiber_cladding_radius = 125/2  # um
        self.fiber_core_radius = 5/2  # um
        self.jacket_circle_radius = int(self.fiber_jacket_radius / self.pixel_size)
        self.cladding_circle_radius = int(self.fiber_cladding_radius / self.pixel_size)
        self.core_circle_radius = int(self.fiber_core_radius / self.pixel_size)
        #self.cam.release()

    def start_video_thread(self):
        self.video_thread = threading.Thread(target=self.start_video)
        self.video_thread.start()

    def start_video(self):
        self.video_status = True
        # cv2.startWindowThread()
        # cv2.namedWindow("Camera")
        while self.get_video_status()==True:
            self.get_frame()

    def get_video_status(self):
        return self.video_status

    def set_video_status(self, bool):
        self.video_status = bool
        return

    def get_frame(self):
        # self.cam = cv2.VideoCapture(0)
        # Capture frame-by-frame
        self.ret, self.frame = self.cam.read()
        self.frame_r, self.frame_g, self.frame_b = cv2.split(np.asarray(self.frame))
        self.frame = self.frame_r
        if self.ret == True:
            # Our operations on the frame come here
            self.get_edges()
            self.get_cross()
            self.get_core()
            self.get_cladding()
            self.get_jacket()
        cv2.imshow('Camera', self.frame)
        cv2.waitKey(20)
        # self.cam.release()

    def stop_video(self):
        if self.get_video_status() == True:
            self.set_video_status(False)
            self.cam.release()
        else:
            pass

    def get_cross(self):
        if self.cross == 1:
            cv2.line(self.frame, (int(self.video_width / 2 - 50), int(self.video_height / 2)),
                    (int(self.video_width / 2 + 50), int(self.video_height / 2)), (0, 0, 255), 2)
            cv2.line(self.frame, (int(self.video_width / 2), int(self.video_height / 2 - 50)),
                    (int(self.video_width / 2), int(self.video_height / 2 + 50)), (0, 0, 255), 2)
        else:
            pass

    def get_cladding(self):
        if self.cladding == 1:
            cv2.circle(self.frame,
                       (int(self.video_width / 2),
                        int(self.video_height / 2)),
                        self.cladding_circle_radius,
                        (0, 0, 255), 2)
        else:
            pass

    def get_core(self):
        if self.core == 1:
            cv2.circle(self.frame,
                       (int(self.video_width / 2),
                        int(self.video_height / 2)),
                        self.core_circle_radius,
                        (0, 0, 255), 1)
        else:
            pass

    def get_jacket(self):
        if self.jacket == 1:
            cv2.circle(self.frame,
                       (int(self.video_width / 2),
                        int(self.video_height / 2)),
                        self.jacket_circle_radius,
                        (0, 0, 255), 2)
        else:
            pass

    def get_cross_value(self):
        return self.cross

    def get_cladding_value(self):
        return self.cladding

    def get_core_value(self):
        return self.core

    def get_jacket_value(self):
        return self.jacket

    def set_cross_value(self, value):
        self.cross = value

    def set_jacket_value(self, value):
        self.jacket = value

    def set_cladding_value(self, value):
        self.cladding = value

    def set_core_value(self, value):
        self.core = value

    def set_edge_detection_value(self, value):
        self.edges = value

    def get_edge_detection_value(self):
        return self.edges

    def take_screenshot(self):
        self.screenshot = self.get_frame()
        cv2.imwrite('bla.png', self.screenshot)

    def set_zoom_factor(self, value):
        self.zoom_factor = value
        self.real_height, self.real_width = np.array([4464, 5952]) / (9.52 * self.zoom_factor)
        self.pixel_size = self.real_width / self.video_width
        self.jacket_circle_radius = int(self.fiber_jacket_radius / self.pixel_size)
        self.cladding_circle_radius = int(self.fiber_cladding_radius / self.pixel_size)
        self.core_circle_radius = int(self.fiber_core_radius / self.pixel_size)

    def get_zoom_factor(self):
        return self.zoom_factor

    def get_edges(self):
        if self.edges == 1:
            self.edges_mask = cv2.Canny(cv2.GaussianBlur(self.frame, (9, 9), 0), self.edge_min, self.edge_max)
            self.frame = cv2.addWeighted(self.frame, 1, self.edges_mask, 0.5, 0)
        else:
            pass

    def set_edge_min(self, value):
        ''' The specified value is a percentage
        '''
        edge_min_value = value * 255 / 100
        self.edge_min = edge_min_value

    def get_edge_min(self):
        ''' Return the value as a percentage
        '''
        return int(self.edge_min * 100 / 255)

    def set_edge_max(self, value):
        ''' The specified value is a percentage
        '''
        edge_max_value = value * 255 / 100
        self.edge_max = edge_max_value

    def get_edge_max(self):
        ''' Return the value as a percentage
        '''
        return int(self.edge_max * 100 / 255)
