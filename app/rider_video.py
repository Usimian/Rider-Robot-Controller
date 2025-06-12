#!/usr/bin/env python3
# coding=utf-8

# Rider Robot Video Streaming Module
# Handles camera capture and video streaming for the Rider robot
# This is a support file for rider_controller.py
# Marc Wester

import threading
import time
import base64
import io
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
        
        # Image capture settings
        self.__capture_width = 640   # Higher resolution for captured images
        self.__capture_height = 480
        self.__capture_quality = 85  # JPEG quality for captured images (0-100)
        
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
                
                # TEST: Try to capture a frame during initialization to verify camera works
                if self.__debug:
                    print("Testing initial frame capture...")
                
                # Give camera time to initialize
                time.sleep(0.2)
                
                # Try to capture a test frame
                ret, test_frame = self.__camera.read()  # type: ignore
                if ret and test_frame is not None:
                    if self.__debug:
                        print(f"✅ Test frame captured successfully: {test_frame.shape}")
                else:
                    if self.__debug:
                        print("⚠️  Warning: Could not capture test frame during initialization")
                        # Don't fail completely, but this indicates a potential issue
                
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
        consecutive_failures = 0
        last_error_report = 0
        
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
                    consecutive_failures += 1
                    
                    # Only report errors occasionally to avoid spam
                    if self.__debug and (current_time - last_error_report) > 5.0:
                        print(f"Failed to capture frame (consecutive failures: {consecutive_failures})")
                        last_error_report = current_time
                    
                    # If too many consecutive failures, sleep longer
                    if consecutive_failures > 10:
                        time.sleep(0.5)
                    
                    continue
                
                # Reset failure counter on success
                consecutive_failures = 0
                
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
                consecutive_failures += 1
                if self.__debug and (current_time - last_error_report) > 5.0:
                    print(f"Error in capture loop: {e}")
                    last_error_report = current_time
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

    def capture_image(self, resolution: str = "high") -> Optional[str]:
        """
        Capture a single image and return it as base64 encoded JPEG
        
        Args:
            resolution: "high" (640x480), "low" (320x240), or "tiny" (160x120)
            
        Returns:
            Base64 encoded JPEG string, or None if capture failed
        """
        if not self.is_camera_available():
            if self.__debug:
                print("Cannot capture image - camera not available")
            return None
        
        # Check if streaming is active - if so, we need to pause it to avoid conflicts
        streaming_was_active = self.__running
        
        try:
            if streaming_was_active:
                if self.__debug:
                    print("📷 Pausing streaming for high-quality image capture...")
                # Temporarily stop streaming to avoid camera conflicts
                self.stop_streaming()
                # Give it a moment to fully stop
                time.sleep(0.2)
            
            if self.__debug:
                print(f"📷 Capturing image at {resolution} resolution directly from camera")
            
            # Get target resolution
            target_width, target_height = self.__get_target_resolution(resolution)
            
            # Store original camera settings to restore later
            original_width = self.__camera.get(cv2.CAP_PROP_FRAME_WIDTH)  # type: ignore
            original_height = self.__camera.get(cv2.CAP_PROP_FRAME_HEIGHT)  # type: ignore
            
            # Set camera to target resolution for capture
            self.__camera.set(cv2.CAP_PROP_FRAME_WIDTH, target_width)  # type: ignore
            self.__camera.set(cv2.CAP_PROP_FRAME_HEIGHT, target_height)  # type: ignore
            
            # Give camera time to adjust to new resolution
            time.sleep(0.1)
            
            # Clear camera buffer to get fresh frame at new resolution
            for _ in range(3):  # Read a few frames to clear buffer
                self.__camera.read()  # type: ignore
            
            # Capture the actual frame we want
            ret, frame = self.__camera.read()  # type: ignore
            
            # Restore original camera settings for streaming
            self.__camera.set(cv2.CAP_PROP_FRAME_WIDTH, original_width)  # type: ignore
            self.__camera.set(cv2.CAP_PROP_FRAME_HEIGHT, original_height)  # type: ignore
            
            if not ret or frame is None:
                if self.__debug:
                    print("❌ Failed to capture image frame at requested resolution")
                return None
            
            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  # type: ignore
            
            # Convert to PIL Image
            pil_image = Image.fromarray(rgb_frame)
            
            # Verify we got the expected resolution
            actual_width, actual_height = pil_image.size
            if self.__debug:
                print(f"📷 Captured frame: {actual_width}x{actual_height} (requested: {target_width}x{target_height})")
            
            # If camera didn't provide exact resolution, resize as needed
            if pil_image.size != (target_width, target_height):
                if self.__debug:
                    print(f"📏 Resizing from {pil_image.size} to {target_width}x{target_height}")
                pil_image = pil_image.resize((target_width, target_height), Image.Resampling.LANCZOS)
            
            # Convert to JPEG and encode as base64
            buffer = io.BytesIO()
            pil_image.save(buffer, format='JPEG', quality=self.__capture_quality)
            img_bytes = buffer.getvalue()
            
            # Encode to base64
            base64_string = base64.b64encode(img_bytes).decode('utf-8')
            
            if self.__debug:
                img_size_kb = len(img_bytes) / 1024
                print(f"✅ Image captured successfully: {pil_image.size[0]}x{pil_image.size[1]}, {img_size_kb:.1f}KB")
            
            return base64_string
            
        except Exception as e:
            if self.__debug:
                print(f"❌ Error capturing image: {e}")
            
            # Fallback: Try to use current streaming frame if direct capture fails
            try:
                if self.__debug:
                    print("🔄 Falling back to streaming frame...")
                
                current_frame = self.get_current_frame()
                if current_frame is not None:
                    # Get target resolution
                    target_width, target_height = self.__get_target_resolution(resolution)
                    
                    # Resize the current frame
                    current_frame = current_frame.resize((target_width, target_height), Image.Resampling.LANCZOS)
                    
                    # Convert to JPEG and encode as base64
                    buffer = io.BytesIO()
                    current_frame.save(buffer, format='JPEG', quality=self.__capture_quality)
                    img_bytes = buffer.getvalue()
                    
                    # Encode to base64
                    base64_string = base64.b64encode(img_bytes).decode('utf-8')
                    
                    if self.__debug:
                        img_size_kb = len(img_bytes) / 1024
                        print(f"⚠️  Fallback capture: {current_frame.size[0]}x{current_frame.size[1]}, {img_size_kb:.1f}KB (upscaled)")
                    
                    return base64_string
                    
            except Exception as fallback_e:
                if self.__debug:
                    print(f"❌ Fallback capture also failed: {fallback_e}")
            
            return None
            
        finally:
            # Always restart streaming if it was active before
            if streaming_was_active:
                if self.__debug:
                    print("🔄 Restarting streaming...")
                self.start_streaming()
                # Give it a moment to restart
                time.sleep(0.1)
    
    def __get_target_resolution(self, resolution: str) -> tuple:
        """Get target resolution dimensions"""
        if resolution == "high":
            return (self.__capture_width, self.__capture_height)
        elif resolution == "low":
            return (320, 240)
        elif resolution == "tiny":
            return (160, 120)
        else:
            # Default to high if unknown
            return (self.__capture_width, self.__capture_height)
    
    def capture_image_file(self, filepath: str, resolution: str = "high") -> bool:
        """
        Capture a single image and save it to a file
        
        Args:
            filepath: Path where to save the image
            resolution: "high" (640x480) or "low" (320x240)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_camera_available():
            if self.__debug:
                print("Cannot capture image - camera not available")
            return False
        
        try:
            # Get base64 encoded image
            base64_image = self.capture_image(resolution)
            if base64_image is None:
                return False
            
            # Decode base64 and save to file
            img_bytes = base64.b64decode(base64_image)
            
            with open(filepath, 'wb') as f:
                f.write(img_bytes)
            
            if self.__debug:
                print(f"📷 Image saved to: {filepath}")
            
            return True
            
        except Exception as e:
            if self.__debug:
                print(f"Error saving image to file: {e}")
            return False
