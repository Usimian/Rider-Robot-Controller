#!/usr/bin/env python3
# coding=utf-8

# Rider Robot Video Streaming Module
# Handles camera capture and video streaming for the Rider robot
# This is a support file for rider_controller.py
# Marc Wester

import threading
import time
import numpy as np
from PIL import Image
from typing import Optional, Tuple

# Import OpenCV with proper error handling
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
        self.__camera: Optional[object] = None  # cv2.VideoCapture object
        self.__running = False
        self.__capture_thread: Optional[threading.Thread] = None
        self.__current_frame: Optional[Image.Image] = None
        self.__frame_lock = threading.Lock()
        
        # Video settings
        self.__frame_width = 160   # Doubled size for LCD corner display (was 80)
        self.__frame_height = 120  # Doubled size for LCD corner display (was 60)
        self.__fps = 15          # Moderate FPS to reduce CPU load
        
        # Check if OpenCV is available
        if not CV2_AVAILABLE:
            if self.__debug:
                print("⚠️  OpenCV (cv2) not available - video functionality disabled")
            return
        
        # Initialize camera
        self.__init_camera()
        
        if self.__debug:
            print("RiderVideo initialized")
    
    def __init_camera(self) -> bool:
        """Initialize the camera"""
        if not CV2_AVAILABLE or cv2 is None:
            if self.__debug:
                print("Cannot initialize camera - OpenCV not available")
            return False
            
        try:
            if self.__debug:
                print(f"Initializing camera {self.__camera_id}...")
            
            # Try to open camera
            self.__camera = cv2.VideoCapture(self.__camera_id)  # type: ignore
            
            if self.__camera is None or not self.__camera.isOpened():  # type: ignore
                if self.__debug:
                    print(f"Failed to open camera {self.__camera_id}, trying USB camera...")
                # Try USB camera
                self.__camera = cv2.VideoCapture(0)  # type: ignore
                
                if self.__camera is None or not self.__camera.isOpened():  # type: ignore
                    if self.__debug:
                        print("No camera found!")
                    self.__camera = None
                    return False
            
            # Set camera properties for better performance
            if self.__camera is not None:
                self.__camera.set(cv2.CAP_PROP_FRAME_WIDTH, 320)  # type: ignore
                self.__camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)  # type: ignore
                self.__camera.set(cv2.CAP_PROP_FPS, self.__fps)  # type: ignore
                
                # Set buffer size to reduce latency
                self.__camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # type: ignore
                
                if self.__debug:
                    actual_width = self.__camera.get(cv2.CAP_PROP_FRAME_WIDTH)  # type: ignore
                    actual_height = self.__camera.get(cv2.CAP_PROP_FRAME_HEIGHT)  # type: ignore
                    actual_fps = self.__camera.get(cv2.CAP_PROP_FPS)  # type: ignore
                    print(f"Camera initialized: {actual_width}x{actual_height} @ {actual_fps}fps")
            
            return True
            
        except Exception as e:
            if self.__debug:
                print(f"Error initializing camera: {e}")
            self.__camera = None
            return False
    
    def is_camera_available(self) -> bool:
        """Check if camera is available"""
        if not CV2_AVAILABLE or cv2 is None:
            return False
        return self.__camera is not None and hasattr(self.__camera, 'isOpened') and self.__camera.isOpened()  # type: ignore
    
    def start_streaming(self) -> bool:
        """Start video streaming in a separate thread"""
        if not self.is_camera_available():
            if self.__debug:
                print("Cannot start streaming - camera not available")
            return False
        
        if self.__running:
            if self.__debug:
                print("Streaming already running")
            return True
        
        self.__running = True
        self.__capture_thread = threading.Thread(target=self.__capture_loop, daemon=True)
        self.__capture_thread.start()
        
        if self.__debug:
            print("Video streaming started")
        return True
    
    def stop_streaming(self) -> None:
        """Stop video streaming"""
        self.__running = False
        if self.__capture_thread and self.__capture_thread.is_alive():
            self.__capture_thread.join(timeout=1.0)
        
        if self.__debug:
            print("Video streaming stopped")
    
    def __capture_loop(self) -> None:
        """Main capture loop running in separate thread"""
        if not CV2_AVAILABLE or cv2 is None:
            return
            
        frame_interval = 1.0 / self.__fps
        last_frame_time = 0
        
        while self.__running and self.is_camera_available():
            current_time = time.time()
            
            # Control frame rate
            if current_time - last_frame_time < frame_interval:
                time.sleep(0.01)  # Small sleep to prevent busy waiting
                continue
            
            try:
                # Ensure camera is still valid
                if self.__camera is None:
                    break
                    
                # Capture frame
                ret, frame = self.__camera.read()  # type: ignore
                if not ret or frame is None:
                    if self.__debug:
                        print("Failed to capture frame")
                    continue
                
                # Resize frame for display
                resized_frame = cv2.resize(frame, (self.__frame_width, self.__frame_height))  # type: ignore
                
                # Convert BGR to RGB
                rgb_frame = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)  # type: ignore
                
                # Convert to PIL Image
                pil_frame = Image.fromarray(rgb_frame)
                
                # Store frame thread-safely
                with self.__frame_lock:
                    self.__current_frame = pil_frame
                
                last_frame_time = current_time
                
            except Exception as e:
                if self.__debug:
                    print(f"Error in capture loop: {e}")
                time.sleep(0.1)
    
    def get_current_frame(self) -> Optional[Image.Image]:
        """Get the current video frame as PIL Image"""
        with self.__frame_lock:
            if self.__current_frame is not None:
                return self.__current_frame.copy()
            return None
    
    def get_frame_size(self) -> Tuple[int, int]:
        """Get video frame dimensions"""
        return (self.__frame_width, self.__frame_height)
    
    def cleanup(self) -> None:
        """Clean up resources"""
        self.stop_streaming()
        
        if self.__camera is not None:
            try:
                self.__camera.release()  # type: ignore
            except Exception as e:
                if self.__debug:
                    print(f"Error releasing camera: {e}")
            self.__camera = None
        
        if self.__debug:
            print("RiderVideo cleanup complete")
