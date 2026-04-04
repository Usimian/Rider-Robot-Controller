#!/usr/bin/env python3
# coding=utf-8

# Rider Robot Video Streaming Module
# Handles camera capture and video streaming for the Rider robot
# Uses picamera2 for CSI cameras (CM5), falls back to OpenCV for USB cameras

import threading
import time
import base64
import io
from PIL import Image
from typing import Optional, Tuple

try:
    from picamera2 import Picamera2
    PICAMERA2_AVAILABLE = True
except ImportError:
    PICAMERA2_AVAILABLE = False

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    cv2 = None


class RiderVideo:
    def __init__(self, camera_id: int = 0, debug: bool = False):
        self.__debug = debug
        self.__camera_id = camera_id
        self.__picam = None        # picamera2 instance
        self.__camera = None       # cv2.VideoCapture fallback
        self.__use_picamera2 = False
        self.__running = False
        self.__capture_thread: Optional[threading.Thread] = None
        self.__current_frame: Optional[Image.Image] = None
        self.__frame_lock = threading.Lock()

        self.__frame_width = 160
        self.__frame_height = 120
        self.__fps = 15
        self.__capture_width = 640
        self.__capture_height = 480
        self.__capture_quality = 85

        self.__init_camera()

        if self.__debug:
            print("RiderVideo initialized")

    def __init_camera(self) -> bool:
        # Try picamera2 first (CSI camera on CM5)
        if PICAMERA2_AVAILABLE:
            try:
                self.__picam = Picamera2()
                config = self.__picam.create_preview_configuration(
                    main={'size': (self.__capture_width, self.__capture_height), 'format': 'RGB888'},
                    controls={'FrameRate': float(self.__fps)}
                )
                self.__picam.configure(config)
                self.__picam.start()
                time.sleep(0.5)
                frame = self.__picam.capture_array()
                if frame is not None:
                    self.__use_picamera2 = True
                    if self.__debug:
                        print(f"picamera2 camera initialized: {frame.shape}")
                    return True
                self.__picam.stop()
                self.__picam.close()
                self.__picam = None
            except Exception as e:
                if self.__debug:
                    print(f"picamera2 init failed: {e}")
                if self.__picam:
                    try:
                        self.__picam.close()
                    except Exception:
                        pass
                    self.__picam = None

        # Fall back to OpenCV (USB camera)
        if CV2_AVAILABLE and cv2 is not None:
            try:
                self.__camera = cv2.VideoCapture(self.__camera_id)
                if self.__camera and self.__camera.isOpened():
                    self.__camera.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
                    self.__camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
                    self.__camera.set(cv2.CAP_PROP_FPS, self.__fps)
                    self.__camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    time.sleep(0.2)
                    ret, test_frame = self.__camera.read()
                    if ret and test_frame is not None:
                        if self.__debug:
                            print(f"OpenCV camera initialized: {test_frame.shape}")
                        return True
                self.__camera.release()
                self.__camera = None
            except Exception as e:
                if self.__debug:
                    print(f"OpenCV init failed: {e}")
                self.__camera = None

        if self.__debug:
            print("No camera found")
        return False

    def is_camera_available(self) -> bool:
        if self.__use_picamera2 and self.__picam is not None:
            return True
        if CV2_AVAILABLE and cv2 is not None and self.__camera is not None:
            return hasattr(self.__camera, 'isOpened') and self.__camera.isOpened()
        return False

    def start_streaming(self) -> bool:
        if not self.is_camera_available():
            return False
        if self.__running:
            return True
        self.__running = True
        self.__capture_thread = threading.Thread(target=self.__capture_loop, daemon=True)
        self.__capture_thread.start()
        if self.__debug:
            print("Video streaming started")
        return True

    def stop_streaming(self) -> None:
        self.__running = False
        if self.__capture_thread and self.__capture_thread.is_alive():
            self.__capture_thread.join(timeout=2.0)

    def __capture_loop(self) -> None:
        frame_interval = 1.0 / self.__fps
        last_frame_time = 0
        consecutive_failures = 0
        last_error_report = 0

        while self.__running and self.is_camera_available():
            current_time = time.time()
            if current_time - last_frame_time < frame_interval:
                time.sleep(0.01)
                continue

            try:
                if self.__use_picamera2 and self.__picam:
                    arr = self.__picam.capture_array()
                    if arr is None:
                        consecutive_failures += 1
                        continue
                    pil_frame = Image.fromarray(arr[:, :, ::-1]).resize(
                        (self.__frame_width, self.__frame_height), Image.Resampling.BILINEAR)
                elif CV2_AVAILABLE and cv2 is not None and self.__camera:
                    ret, frame = self.__camera.read()
                    if not ret or frame is None:
                        consecutive_failures += 1
                        if consecutive_failures > 10:
                            time.sleep(0.5)
                        continue
                    rgb = cv2.cvtColor(
                        cv2.resize(frame, (self.__frame_width, self.__frame_height)),
                        cv2.COLOR_BGR2RGB)
                    pil_frame = Image.fromarray(rgb)
                else:
                    break

                consecutive_failures = 0
                with self.__frame_lock:
                    self.__current_frame = pil_frame
                last_frame_time = current_time

            except Exception as e:
                consecutive_failures += 1
                if self.__debug and (current_time - last_error_report) > 5.0:
                    print(f"Capture loop error: {e}")
                    last_error_report = current_time
                time.sleep(0.1)

    def get_current_frame(self) -> Optional[Image.Image]:
        with self.__frame_lock:
            return self.__current_frame.copy() if self.__current_frame is not None else None

    def get_frame_size(self) -> Tuple[int, int]:
        return (self.__frame_width, self.__frame_height)

    def capture_image(self, resolution: str = "high") -> Optional[str]:
        if not self.is_camera_available():
            return None

        # Fast path: use latest streaming frame
        if self.__running:
            frame = self.get_current_frame()
            if frame is not None:
                tw, th = self.__get_target_resolution(resolution)
                if frame.size != (tw, th):
                    frame = frame.resize((tw, th), Image.Resampling.LANCZOS)
                buf = io.BytesIO()
                frame.save(buf, format='JPEG', quality=self.__capture_quality)
                return base64.b64encode(buf.getvalue()).decode('utf-8')

        # Slow path: capture directly
        try:
            tw, th = self.__get_target_resolution(resolution)
            if self.__use_picamera2 and self.__picam:
                arr = self.__picam.capture_array()
                pil_image = Image.fromarray(arr[:, :, ::-1]).resize((tw, th), Image.Resampling.LANCZOS)
            elif CV2_AVAILABLE and cv2 is not None and self.__camera:
                ret, frame = self.__camera.read()
                if not ret or frame is None:
                    return None
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(rgb).resize((tw, th), Image.Resampling.LANCZOS)
            else:
                return None

            buf = io.BytesIO()
            pil_image.save(buf, format='JPEG', quality=self.__capture_quality)
            return base64.b64encode(buf.getvalue()).decode('utf-8')
        except Exception as e:
            if self.__debug:
                print(f"capture_image error: {e}")
            return None

    def __get_target_resolution(self, resolution: str) -> tuple:
        if resolution == "high":
            return (self.__capture_width, self.__capture_height)
        elif resolution == "low":
            return (320, 240)
        elif resolution == "tiny":
            return (160, 120)
        return (self.__capture_width, self.__capture_height)

    def capture_image_file(self, filepath: str, resolution: str = "high") -> bool:
        data = self.capture_image(resolution)
        if data is None:
            return False
        try:
            with open(filepath, 'wb') as f:
                f.write(base64.b64decode(data))
            return True
        except Exception:
            return False

    def cleanup(self) -> None:
        self.stop_streaming()
        if self.__picam:
            try:
                self.__picam.stop()
                self.__picam.close()
            except Exception:
                pass
            self.__picam = None
        if self.__camera is not None:
            try:
                self.__camera.release()
            except Exception:
                pass
            self.__camera = None
        if self.__debug:
            print("RiderVideo cleanup complete")
