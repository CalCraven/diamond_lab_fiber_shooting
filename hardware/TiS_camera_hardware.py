import cv2
import threading
import numpy as np
from core.module import Base
from interface.empty_interface import EmptyInterface


class TisCamera(Base, EmptyInterface):
    """
    This is the Interface class to define the controls for the simple
    microwave hardware.
    """
    _modclass = 'EmptyInterface'
    _modtype = 'hardware'

    def on_activate(self):
        """
        Initialisation performed during activation of the module.
        """
        self.cam = None
        self.ret, self.frame = False, None
        self.video_height, self.video_width, self.video_channels = None, None, None
        self.zoom_factor = 2
        self.real_height, self.real_width = np.array([4464, 5952]) / (9.52 * self.zoom_factor)
        self.edges = False
        self.edge_min = 10
        self.edge_max = 200
        self.cross = False
        self.cladding = False
        self.jacket = False
        self.core = False
        self.pixel_size = 0
        self.pixel_height = 0
        self.fiber_jacket_radius = 165 / 2  # um
        self.fiber_cladding_radius = 125 / 2  # um
        self.fiber_core_radius = 5 / 2  # um
        self.jacket_circle_radius = 0
        self.cladding_circle_radius = 0
        self.core_circle_radius = 0
        self.video = False
        self.video_thread = None
        self.frame_r, self.frame_g, self.frame_b = None, None, None
        self.screenshots = None
        self.edges_mask = None

        self.setup_camera()

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        # When everything done, release the capture
        self.cam.release()
        cv2.destroyWindow('Camera')
        return

    def setup_camera(self):
        """ Setup camera parameters. """
        self.cam = cv2.VideoCapture(1)
        self.ret, self.frame = self.cam.read()
        self.video_height, self.video_width, self.video_channels = self.frame.shape
        self.pixel_size = self.real_width / self.video_width
        self.pixel_height = self.real_height / self.video_height
        self.jacket_circle_radius = int(self.fiber_jacket_radius / self.pixel_size)
        self.cladding_circle_radius = int(self.fiber_cladding_radius / self.pixel_size)
        self.core_circle_radius = int(self.fiber_core_radius / self.pixel_size)
        return

    def start_video_thread(self):
        """ Start the thread who capture the video. """
        self.video_thread = threading.Thread(target=self.start_video)
        self.video_thread.start()
        return

    def start_video(self):
        """ Start the capture of the video. """
        self.set_video(True)
        while self.is_video():
            self.get_frame()
        return

    def is_video(self):
        """ Get the video status (boolean) """
        return self.video

    def set_video(self, boolean):
        """ Set the video status to True or False"""
        self.video = boolean
        return

    def get_frame(self):
        """ Get the frame from the camera"""
        self.ret, self.frame = self.cam.read()
        self.frame_r, self.frame_g, self.frame_b = cv2.split(np.asarray(self.frame))
        self.frame = self.frame_r
        if self.ret:
            # Our operations on the frame come here
            self.get_edges()
            self.get_cross()
            self.get_core()
            self.get_cladding()
            self.get_jacket()
        cv2.imshow('Camera', self.frame)
        cv2.waitKey(20)
        return self.frame

    def stop_video(self):
        """ Stop the capture of the video. """
        if self.is_video():
            self.set_video(False)
            self.cam.release()
        else:
            pass
        return

    def get_cross(self):
        """ Get the cross drawn on each frame or not. """
        if self.is_cross():
            cv2.line(self.frame, (int(self.video_width / 2 - 50), int(self.video_height / 2)),
                     (int(self.video_width / 2 + 50), int(self.video_height / 2)), (0, 0, 255), 2)
            cv2.line(self.frame, (int(self.video_width / 2), int(self.video_height / 2 - 50)),
                     (int(self.video_width / 2), int(self.video_height / 2 + 50)), (0, 0, 255), 2)
        else:
            pass

    def get_cladding(self):
        """ Get the cladding drawn on each frame or not. """
        if self.is_cladding():
            cv2.circle(self.frame,
                       (int(self.video_width / 2), int(self.video_height / 2)),
                       self.cladding_circle_radius, (0, 0, 255), 2)
        else:
            pass

    def get_core(self):
        """ Get the core drawn on each frame or not. """
        if self.is_core:
            cv2.circle(self.frame, (int(self.video_width / 2), int(self.video_height / 2)), self.core_circle_radius,
                       (0, 0, 255), 1)
        else:
            pass

    def get_jacket(self):
        """ Get the jacket drawn on each frame or not. """
        if self.is_jacket:
            cv2.circle(self.frame,
                       (int(self.video_width / 2), int(self.video_height / 2)), self.jacket_circle_radius,
                       (0, 0, 255), 2)
        else:
            pass

    def is_cross(self):
        """ Get the cross drawn status. """
        return self.cross

    def is_cladding(self):
        """ Get the cladding drawn status. """
        return self.cladding

    def is_core(self):
        """ Get the core drawn status. """
        return self.core

    def is_jacket(self):
        """ Get the jacket drawn status. """
        return self.jacket

    def set_cross(self, boolean):
        """ Set the cross drawn status. """
        self.cross = boolean
        print('cross', self.cross)

    def set_jacket(self, boolean):
        """ Set the jacket drawn status. """
        self.jacket = boolean

    def set_cladding(self, boolean):
        """ Set the cladding drawn status. """
        self.cladding = boolean

    def set_core(self, boolean):
        """ Set the core drawn status. """
        self.core = boolean
        print('core', self.core)


    def set_edge_detection(self, boolean):
        """ Set the edge detection drawn status. """
        self.edges = boolean

    def is_edge_detection(self):
        """ Get the edge detection drawn status. """
        return self.edges

    def take_screenshot(self):
        """ Take a screenshots. """
        self.screenshots = self.get_frame()
        cv2.imwrite('bla.png', self.screenshots)

    def set_zoom_factor(self, value):
        """ Set the scaling factor of the video. """
        self.zoom_factor = value
        self.real_height, self.real_width = np.array([4464, 5952]) / (9.52 * self.zoom_factor)
        self.pixel_size = self.real_width / self.video_width
        self.jacket_circle_radius = int(self.fiber_jacket_radius / self.pixel_size)
        self.cladding_circle_radius = int(self.fiber_cladding_radius / self.pixel_size)
        self.core_circle_radius = int(self.fiber_core_radius / self.pixel_size)

    def get_zoom_factor(self):
        """ Get the scaling factor of the video. """
        return self.zoom_factor

    def get_edges(self):
        """ Get the edges drawn or not on the video. """
        if self.edges:
            self.edges_mask = cv2.Canny(cv2.GaussianBlur(self.frame, (9, 9), 0), self.edge_min, self.edge_max)
            self.frame = cv2.addWeighted(self.frame, 1, self.edges_mask, 0.5, 0)
        else:
            pass

    def set_edge_min(self, value):
        """ Set the edges minimum threshold. """
        edge_min_value = value * 255 / 100
        self.edge_min = edge_min_value

    def get_edge_min(self):
        """ Get the edges minimum threshold. """
        return int(self.edge_min * 100 / 255)

    def set_edge_max(self, value):
        """ Set the edges maximum threshold. """
        edge_max_value = value * 255 / 100
        self.edge_max = edge_max_value

    def get_edge_max(self):
        """ Get the edges maximum threshold. """
        return int(self.edge_max * 100 / 255)
