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
        self.zoom_factor = 3
        self.real_height, self.real_width = np.array([4464, 5952]) / (9.52 * self.zoom_factor)
        self.edges = False
        self.edge_min = 6
        self.edge_max = 26
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
        self.screenshots = None
        self.edges_mask = None


    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        # When everything done, release the capture
        if self.cam != None:
            self.cam.release()
        cv2.destroyAllWindows()
        return

    def setup_camera(self):
        """ Setup camera parameters. """
        self.cam = cv2.VideoCapture(1 + cv2.CAP_DSHOW)
        if self.cam.isOpened():
            self.ret, self.frame = self.cam.read()
            if self.ret:
                self.video_height, self.video_width, self.video_channels = self.frame.shape
                self.pixel_size = self.real_width / self.video_width
                self.pixel_height = self.real_height / self.video_height
                self.jacket_circle_radius = int(self.fiber_jacket_radius / self.pixel_size)
                self.cladding_circle_radius = int(self.fiber_cladding_radius / self.pixel_size)
                self.core_circle_radius = int(self.fiber_core_radius / self.pixel_size)

                print('Brightness: ', self.cam.get(cv2.CAP_PROP_BRIGHTNESS))
                print('Gain: ', self.cam.get(cv2.CAP_PROP_GAIN))
                print('Exposure: ', self.cam.get(cv2.CAP_PROP_EXPOSURE))
                print('Auto Exposure: ', self.cam.get(cv2.CAP_PROP_AUTO_EXPOSURE))
                #print('Setting exposure to 40 ms')
                #print('Setting brightness to 60')
                #self.cam.set(cv2.CAP_PROP_EXPOSURE, -5)
                #self.cam.set(cv2.CAP_PROP_BRIGHTNESS, 60)
                #print('Exposure: ', self.cam.get(cv2.CAP_PROP_EXPOSURE))
                #print('Brightness: ', self.cam.get(cv2.CAP_PROP_BRIGHTNESS))
                print('Frame size: ', np.shape(np.asarray(self.frame)))
                return True
            else:
                print('Error reading frame')
                return False
        else:
            print('Cannot start video capturing with this camera')
            return False

    def start_video_thread(self):
        """ Start the thread who capture the video. """
        if self.cam != None:
            print('Camera output is already in progress')
            return
        if self.setup_camera():
            print('Camera set up successfully')
            cv2.namedWindow('Camera0')
            cv2.moveWindow('Camera0', 638, 0)
            if self.video_thread != None:
                print('Video thread already exists')
                return
            self.video = True
            self.video_thread = threading.Thread(target=self.stream_video)
            self.video_thread.start()
        else:
            print('Cannot set up a camera')
        return

    def stream_video(self):
        """ Threaded function to stream video capture. """
        while self.video:
            self.get_frame()
        return

    def stop_video(self):
        self.video = False
        if self.video_thread != None:
            self.video_thread.join()
        self.video_thread = None
        if self.cam != None:
            self.cam.release()
            self.cam = None
        cv2.destroyAllWindows()


    def get_frame(self):
        """ Get the frame from the camera"""
        self.ret, self.frame = self.cam.read()
        self.frame = cv2.cvtColor(self.frame, cv2.COLOR_BGR2GRAY)
        if self.ret:
            # Our operations on the frame come here
            self.get_edges()
            self.get_cross()
            self.get_core()
            self.get_cladding()
            self.get_jacket()
            cv2.imshow('Camera0', self.frame)
            #cv2.waitKey(1)
        else:
            print("Can't receive frame from the camera")


    def get_cross(self):
        """ Get the cross drawn on each frame or not. """
        if self.cross:
            cv2.line(self.frame, (int(self.video_width / 2 - 50), int(self.video_height / 2)),
                     (int(self.video_width / 2 + 50), int(self.video_height / 2)), (0, 0, 255), 2)
            cv2.line(self.frame, (int(self.video_width / 2), int(self.video_height / 2 - 50)),
                     (int(self.video_width / 2), int(self.video_height / 2 + 50)), (0, 0, 255), 2)


    def get_cladding(self):
        """ Get the cladding drawn on each frame or not. """
        if self.cladding:
            cv2.circle(self.frame, (int(self.video_width / 2), int(self.video_height / 2)),
                       self.cladding_circle_radius, (0, 0, 255), 2)


    def get_core(self):
        """ Get the core drawn on each frame or not. """
        if self.core:
            cv2.circle(self.frame, (int(self.video_width / 2), int(self.video_height / 2)),
                       self.core_circle_radius, (0, 0, 255), 1)


    def get_jacket(self):
        """ Get the jacket drawn on each frame or not. """
        if self.jacket:
            cv2.circle(self.frame, (int(self.video_width / 2), int(self.video_height / 2)),
                       self.jacket_circle_radius, (0, 0, 255), 2)


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
            #self.frame = cv2.Canny(self.frame, self.edge_min, self.edge_max)


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
