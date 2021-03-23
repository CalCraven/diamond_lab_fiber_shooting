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
        self.video_height, self.video_width = None, None
        self.px_size_zoom1_um = 7*125./452  # Camera pixel size in um at zoom=1. Calibrated by observing a fiber.
        self.zoom_factor = 7  # Default zoom factor of the Navitar telescope
        self.px_size_um = self.px_size_zoom1_um/ self.zoom_factor  # Camera pixel size in um for a given zoom
        # By default, the size of the video frame is 640 x 480 pixels, even if a camera allows larger images
        # That gives a cropped view. One can force camera to show larger frame size (see setup_camera()).
        # This does not work with all cameras. Tested successfully with TheImagingSource cameras.
        # We want 1280x1024 window, but with x2 magnification. So we set 640x512 pixels and a software scale factor.
        # Actual size of the grabbed frame from the camera sensor:
        #self.frame_width = 1280
        #self.frame_height = 1024
        self.frame_width = 640
        self.frame_height = 512
        # Software scaling factor of the video frame
        self.sscale = 2
        self.px_size_zoom1_um /= self.sscale  # Adjust the pixel size due to software scaling
        self.px_size_um /= self.sscale  # Adjust the pixel size due to software scaling
        # Scaled size of the video shown on the monitor:
        self.video_width = self.frame_width * self.sscale
        self.video_height = self.frame_height * self.sscale
        # On-screen markers
        self.edges = False
        self.edge_min = 6
        self.edge_max = 26
        self.cross = False
        self.cladding = False
        self.jacket = False
        self.core = False
        self.pixel_size = 0
        # Single-mode fiber dimensions:
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
        # Activate external camera (0 - first camera is laptop's front camera)
        # 1 - DMK 41AU02
        # 2 - DMK 33UX249
        self.cam = cv2.VideoCapture(2 + cv2.CAP_DSHOW)
        if self.cam.isOpened():
            self.ret, self.frame = self.cam.read()
            if self.ret:
                # Tell camera to grab a particular size of the frame rather than the default 640x480 crop:
                self.cam.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
                self.cam.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
                # Setting up the real pixel size (requires prior camera calibration)
                self.jacket_circle_radius = int(self.fiber_jacket_radius / self.px_size_um)
                self.cladding_circle_radius = int(self.fiber_cladding_radius / self.px_size_um)
                self.core_circle_radius = int(self.fiber_core_radius / self.px_size_um)
                # Checking brightness/gain/exposure settings
                print('Brightness:', self.cam.get(cv2.CAP_PROP_BRIGHTNESS))
                print('Gain:', self.cam.get(cv2.CAP_PROP_GAIN))
                print('Exposure:', self.cam.get(cv2.CAP_PROP_EXPOSURE))
                print('Setting exposure to around 250 ms (depends on camera)')
                self.cam.set(cv2.CAP_PROP_EXPOSURE, -2)
                print('Exposure:', self.cam.get(cv2.CAP_PROP_EXPOSURE))
                # Get a new frame after changing all the above settings
                cv2.waitKey(1)
                self.ret, self.frame = self.cam.read()
                print('Frame size:', np.shape(np.asarray(self.frame)))
                return True
            else:
                print('Error reading frame')
                return False
        else:
            print('Cannot start video capturing with this camera')
            self.cam.release()
            self.cam = None
            return False

    def start_video_thread(self):
        """ Start a thread that captures the video. """
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
            ret, frame = self.cam.read()
            # frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)  # Convert to mono for color CCD camera
            # Scale up by a factor sscale
            self.frame = cv2.resize(frame, (0, 0), None, self.sscale, self.sscale)
            if ret:
                # Our operations on the frame come here
                self.get_edges()
                self.get_cross()
                self.get_core()
                self.get_cladding()
                self.get_jacket()
                cv2.imshow('Camera0', self.frame)
                cv2.waitKey(5)
            else:
                print("Can't receive frame from the camera")
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
        filename = 'C:\\Temp\\screenshot.png'
        print('Saving screenshot as', filename);
        cv2.imwrite(filename, self.frame)

    def set_zoom_factor(self, value):
        """ Set the scaling factor of the video. """
        self.zoom_factor = value
        # Calibration values for TheImagingSource camera DMK 33UX249:
        self.px_size_um = self.px_size_zoom1_um / self.zoom_factor  # Camera pixel size in um for a given zoom
        self.jacket_circle_radius = int(self.fiber_jacket_radius / self.px_size_um)
        self.cladding_circle_radius = int(self.fiber_cladding_radius / self.px_size_um)
        self.core_circle_radius = int(self.fiber_core_radius / self.px_size_um)

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

    def exposure_up(self):
        """Increase exposure of the camera
        @return: New exposure value"""
        exposure = self.cam.get(cv2.CAP_PROP_EXPOSURE) + 1
        self.cam.set(cv2.CAP_PROP_EXPOSURE, exposure)
        return exposure

    def exposure_down(self):
        """Decrease exposure of the camera
        @return: New exposure value"""
        exposure = self.cam.get(cv2.CAP_PROP_EXPOSURE) - 1
        self.cam.set(cv2.CAP_PROP_EXPOSURE, exposure)
        return exposure
