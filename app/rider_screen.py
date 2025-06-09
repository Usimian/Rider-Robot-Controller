#!/usr/bin/env python3
# coding=utf-8

# Rider Robot LCD Screen Display
# Shows battery level, percentage, and current speed setting
# This is the main screen file for the Rider robot
# Marc Wester

import time
import sys
import os
import psutil
import xgoscreen.LCD_2inch as LCD_2inch
from PIL import Image, ImageDraw, ImageFont
from key import Button

# Import video streaming module
try:
    from rider_video import RiderVideo
    VIDEO_AVAILABLE = True
except ImportError:
    VIDEO_AVAILABLE = False
    if __debug__:
        print("⚠️  Video module not available - video display disabled")

class RiderScreen:
    def __init__(self, robot=None, debug=False):
        self.__debug = debug
        self.__robot = robot
        self.__running = False
        
        # Display settings
        self.__update_interval = 1.0  # Update every second
        self.__last_update = 0
        
        # Current values to display
        self.__battery_level = 0
        self.__speed_scale = 1.0
        self.__robot_status = "Disconnected"
        self.__controller_connected = False
        self.__roll_balance_enabled = False
        self.__performance_mode_enabled = False
        self.__camera_enabled = False
        
        # Odometry/IMU data
        self.__roll = 0.0
        self.__pitch = 0.0
        self.__yaw = 0.0
        
        # Sensor reading error tracking
        self.__sensor_read_failures = 0
        self.__max_sensor_failures = 3  # Allow 3 failures before showing 0
        self.__last_good_roll = 0.0
        self.__last_good_pitch = 0.0
        self.__last_good_yaw = 0.0
        self.__last_good_battery = 50
        self.__battery_read_failures = 0
        self.__max_battery_failures = 5  # Allow more failures for battery since it's less critical
        
        # Success tracking for recovery
        self.__consecutive_successful_reads = 0
        self.__reset_failure_count_threshold = 10  # Reset failure counters after 10 successful reads
        
        # CPU load data
        self.__cpu_load_1min = 0.0
        self.__cpu_percent = 0.0
        
        # Video settings
        self.__video = None
        self.__video_enabled = False
        self.__last_video_frame = None
        
        # Initialize LCD display
        self.__setup_display()
        
        # Initialize button for interaction
        self.__button = Button()
        
        # Video will be set up externally by the controller
        # self.__setup_video()
        
        if self.__debug:
            print("RiderScreen initialized")
    
    def __setup_video(self):
        """Initialize video streaming if available"""
        if not VIDEO_AVAILABLE:
            if self.__debug:
                print("Video not available - skipping video setup")
            return
        
        try:
            self.__video = RiderVideo(camera_id=0, debug=self.__debug)
            if self.__video.is_camera_available():
                self.__video.start_streaming()
                self.__video_enabled = True
                if self.__debug:
                    print("✅ Video streaming initialized successfully")
            else:
                if self.__debug:
                    print("⚠️  No camera detected - video display disabled")
                self.__video_enabled = False
        except Exception as e:
            if self.__debug:
                print(f"⚠️  Failed to initialize video: {e}")
            self.__video_enabled = False
    
    def __setup_display(self):
        """Initialize the LCD display"""
        try:
            self.__display = LCD_2inch.LCD_2inch()
            self.__display.Init()
            self.__display.clear()
            
            # Create canvas (320x240 pixels)
            self.__splash = Image.new("RGB", (320, 240), (15, 21, 46))  # Dark blue background
            self.__draw = ImageDraw.Draw(self.__splash)
            
            # Load fonts
            self.__font_small = ImageFont.truetype("/home/pi/model/msyh.ttc", 16)
            self.__font_medium = ImageFont.truetype("/home/pi/model/msyh.ttc", 20)
            self.__font_large = ImageFont.truetype("/home/pi/model/msyh.ttc", 24)
            
            # Colors
            self.__color_white = (255, 255, 255)
            self.__color_green = (0, 255, 0)
            self.__color_yellow = (255, 255, 0)
            self.__color_red = (255, 0, 0)
            self.__color_blue = (24, 47, 223)
            self.__color_bg = (15, 21, 46)
            self.__color_gray = (128, 128, 128)
            
            # Show initial screen
            self.__display.ShowImage(self.__splash)
            
            if self.__debug:
                print("LCD display initialized successfully")
                
        except Exception as e:
            print(f"Failed to initialize LCD display: {e}")
            raise
    
    def __clear_screen(self):
        """Clear the screen with background color"""
        self.__draw.rectangle(((0, 0), (320, 240)), fill=self.__color_bg)
    
    def __draw_text(self, x, y, text, color=None, font=None):
        """Helper function to draw text"""
        if color is None:
            color = self.__color_white
        if font is None:
            font = self.__font_medium
        self.__draw.text((x, y), text, fill=color, font=font)
    
    def __draw_rect(self, x, y, w, h, color, filled=True):
        """Helper function to draw rectangles"""
        if filled:
            self.__draw.rectangle(((x, y), (x+w, y+h)), fill=color)
        else:
            self.__draw.rectangle(((x, y), (x+w, y+h)), outline=color, width=2)
    
    def __draw_circle(self, x, y, radius, color, filled=True):
        """Helper function to draw circles"""
        if filled:
            self.__draw.ellipse(((x-radius, y-radius), (x+radius, y+radius)), fill=color)
        else:
            self.__draw.ellipse(((x-radius, y-radius), (x+radius, y+radius)), outline=color, width=2)
    
    def __draw_controller_icon(self, x, y):
        """Draw a controller status icon"""
        # Determine icon color based on controller status
        if not self.__controller_connected:
            icon_color = self.__color_gray
        else:
            icon_color = self.__color_green
        
        # Controller body (rounded rectangle)
        body_width = 24
        body_height = 16
        self.__draw_rect(x, y + 4, body_width, body_height, icon_color, filled=True)
        
        # Controller grips
        self.__draw_rect(x - 2, y + 8, 4, 8, icon_color, filled=True)
        self.__draw_rect(x + body_width - 2, y + 8, 4, 8, icon_color, filled=True)
        
        # D-pad (left side)
        self.__draw_rect(x + 4, y + 8, 6, 2, self.__color_bg, filled=True)
        self.__draw_rect(x + 6, y + 6, 2, 6, self.__color_bg, filled=True)
        
        # Action buttons (right side)
        self.__draw_circle(x + 16, y + 8, 1, self.__color_bg, filled=True)
        self.__draw_circle(x + 19, y + 11, 1, self.__color_bg, filled=True)
        
    def __get_battery_color(self, battery_level):
        """Get appropriate color based on battery level"""
        if battery_level >= 70:
            return self.__color_green
        elif battery_level >= 40:
            return self.__color_yellow
        else:
            return self.__color_red
    
    def __draw_battery_indicator(self, x, y, battery_level):
        """Draw a small battery indicator similar to controller icon"""
        # Small battery outline (similar size to controller icon)
        battery_width = 20
        battery_height = 12
        
        # Draw battery outline
        self.__draw_rect(x, y, battery_width, battery_height, self.__color_white, filled=False)
        
        # Draw battery terminal (smaller)
        self.__draw_rect(x + battery_width, y + 3, 2, 6, self.__color_white, filled=True)
        
        # Draw battery fill based on level
        fill_width = int((battery_width - 2) * (battery_level / 100))
        if fill_width > 0:
            battery_color = self.__get_battery_color(battery_level)
            self.__draw_rect(x + 1, y + 1, fill_width, battery_height - 2, battery_color, filled=True)
    
    def __draw_video_frame(self, x, y):
        """Draw video frame in the lower right corner"""
        if not self.__camera_enabled or self.__video is None:
            # Draw placeholder rectangle
            video_width, video_height = 160, 120  # Updated to match new frame size
            placeholder_color = self.__color_green if self.__video is not None else self.__color_gray
            self.__draw_rect(x, y, video_width, video_height, placeholder_color, filled=False)
            
            # Show different text based on camera availability and status
            if self.__video is None:
                self.__draw_text(x + 50, y + 50, "NO CAM", self.__color_gray, self.__font_small)
            elif not self.__camera_enabled:
                self.__draw_text(x + 45, y + 50, "CAM OFF", placeholder_color, self.__font_small)
            return
        
        try:
            # Get current video frame
            frame = self.__video.get_current_frame()
            if frame is not None:
                self.__last_video_frame = frame
            
            # Use last known frame if current frame is not available
            if self.__last_video_frame is not None:
                # Paste video frame onto the display
                self.__splash.paste(self.__last_video_frame, (x, y))
                
                # Draw border around video
                video_width, video_height = self.__video.get_frame_size()
                self.__draw_rect(x, y, video_width, video_height, self.__color_white, filled=False)
            else:
                # Draw placeholder if no frame available
                video_width, video_height = 160, 120  # Updated to match new frame size
                self.__draw_rect(x, y, video_width, video_height, self.__color_gray, filled=False)
                self.__draw_text(x + 20, y + 25, "...", self.__color_gray, self.__font_small)
                
        except Exception as e:
            if self.__debug:
                print(f"Error drawing video frame: {e}")
            # Draw error placeholder
            video_width, video_height = 160, 120  # Updated to match new frame size
            self.__draw_rect(x, y, video_width, video_height, self.__color_red, filled=False)
            self.__draw_text(x + 15, y + 25, "ERR", self.__color_red, self.__font_small)
    
    def __draw_odometry_info(self, x, y):
        """Draw odometry information above the video window"""
        # Draw Roll, Pitch, Yaw values in a compact format
        odom_text = f"Roll: {self.__roll:+0.1f}°"
        self.__draw_text(x, y, odom_text, self.__color_yellow, self.__font_medium)
        odom_text = f"Pitch: {self.__pitch:+0.1f}°"
        self.__draw_text(x, y+25, odom_text, self.__color_yellow, self.__font_medium)
        odom_text = f"Yaw: {self.__yaw:+0.1f}°"
        self.__draw_text(x, y+50, odom_text, self.__color_yellow, self.__font_medium)
    
    def __draw_cpu_info(self, x, y):
        """Draw CPU percentage and load as two horizontal bars above the video window"""
        bar_width = 100  # Total bar width (reduced to fit two bars)
        bar_height = 10  # Bar height (reduced slightly)
        
        # CPU Percentage Bar
        cpu_ratio = min(self.__cpu_percent / 100.0, 1.0)  # 0% to 100% maps to 0% to 100%
        cpu_fill_width = int(bar_width * cpu_ratio)
        
        # Determine CPU color based on usage level
        if self.__cpu_percent < 50:
            cpu_color = self.__color_green
        elif self.__cpu_percent < 80:
            cpu_color = self.__color_yellow
        else:
            cpu_color = self.__color_red
        
        # Draw CPU bar outline
        self.__draw_rect(x, y, bar_width, bar_height, self.__color_white, filled=False)
        
        # Draw CPU filled portion
        if cpu_fill_width > 0:
            self.__draw_rect(x + 1, y + 1, cpu_fill_width - 2, bar_height - 2, cpu_color, filled=True)
        
        # Draw CPU value text next to bar
        cpu_text = f"CPU {self.__cpu_percent:.0f}%"
        self.__draw_text(x + bar_width + 5, y - 2, cpu_text, cpu_color, self.__font_small)
        
        # Load Bar (positioned below CPU bar)
        load_y = y + bar_height + 5  # 5 pixels spacing between bars
        
        # Calculate fill percentage (0.0 to 4.0 maps to 0% to 100%)
        load_ratio = min(self.__cpu_load_1min / 4.0, 1.0)  # Cap at 100%
        load_fill_width = int(bar_width * load_ratio)
        
        # Determine load color based on load level
        if self.__cpu_load_1min < 1.0:
            load_color = self.__color_green
        elif self.__cpu_load_1min < 3.0:
            load_color = self.__color_yellow
        else:
            load_color = self.__color_red
        
        # Draw load bar outline
        self.__draw_rect(x, load_y, bar_width, bar_height, self.__color_white, filled=False)
        
        # Draw load filled portion
        if load_fill_width > 0:
            self.__draw_rect(x + 1, load_y + 1, load_fill_width - 2, bar_height - 2, load_color, filled=True)
        
        # Draw load value text next to bar
        load_text = f"Load {self.__cpu_load_1min:.2f}"
        self.__draw_text(x + bar_width + 5, load_y - 2, load_text, load_color, self.__font_small)
    
    def __read_cpu_data(self):
        """Read CPU load and usage data"""
        try:
            # Get CPU usage percentage with short interval for accuracy
            self.__cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # Get load average (1 minute only)
            load_avg = os.getloadavg()
            self.__cpu_load_1min = load_avg[0]
        except Exception as e:
            if self.__debug:
                print(f"Error reading CPU data: {e}")
            self.__cpu_percent = 0.0
            self.__cpu_load_1min = 0.0
    
    def __draw_button_labels(self):
        """Draw labels for the physical buttons around the screen"""
        # A button (lower right) - "Quit"
        self.__draw_text(270, 210, "Quit", self.__color_white, self.__font_small)
        
        # B button (lower left) - "Camera"
        camera_color = self.__color_green if self.__camera_enabled else self.__color_white
        self.__draw_text(10, 210, "Camera", camera_color, self.__font_small)
        
        # C button (upper left) 
        # self.__draw_text(10, 30, "C", self.__color_white, self.__font_small)
        
        # D button (upper right)
        # self.__draw_text(270, 30, "D", self.__color_white, self.__font_small)

    def __update_display(self):
        """Update the display with current information"""
        # Clear screen
        self.__clear_screen()
        
        # Update timestamp - moved to top center
        current_time = time.strftime("%H:%M")
        self.__draw_text(140, 5, current_time, self.__color_white, self.__font_small)
        
        # Controller status icon (upper left)
        self.__draw_controller_icon(10, 10)
        
        # Battery indicator (upper right) - small icon
        self.__draw_battery_indicator(235, 15, self.__battery_level)
        
        # Battery percentage next to battery icon
        battery_color = self.__get_battery_color(self.__battery_level)
        self.__draw_text(265, 12, f"{self.__battery_level}%", battery_color, self.__font_small)
        
        # Speed section
        self.__draw_text(20, 125, "SPD", self.__color_white, self.__font_medium)
        self.__draw_text(65, 125, f"{self.__speed_scale:.1f}x", self.__color_white, self.__font_medium)
        
        # Roll Balance section (left aligned)
        self.__draw_text(20, 150, "BAL", self.__color_white, self.__font_medium)
        
        # Roll balance status with color indicator (left aligned)
        balance_color = self.__color_green if self.__roll_balance_enabled else self.__color_red
        balance_status = "ON" if self.__roll_balance_enabled else "OFF"
        self.__draw_text(65, 150, balance_status, balance_color, self.__font_medium)
        
        # Performance Mode section (left aligned)
        self.__draw_text(20, 175, "FUN", self.__color_white, self.__font_medium)
        
        # Performance mode status with color indicator (left aligned)
        performance_color = self.__color_green if self.__performance_mode_enabled else self.__color_red
        performance_status = "ON" if self.__performance_mode_enabled else "OFF"
        self.__draw_text(65, 175, performance_status, performance_color, self.__font_medium)
        
        # Video frame in lower right corner (above Quit button)
        video_x = 150  # Adjusted position to fit larger 160x120 video (was 230)
        video_y = 80   # Moved up 20 pixels from 110 to 90
        self.__draw_video_frame(video_x, video_y)
        
        # Draw odometry information above the video window
        self.__draw_odometry_info(20, video_y - 40)
        
        # Show sensor status if there are issues (debug info)
        if self.__debug or self.__sensor_read_failures > 0 or self.__battery_read_failures > 0:
            status_text = f"S:{self.__sensor_read_failures} B:{self.__battery_read_failures}"
            if self.__consecutive_successful_reads > 0:
                status_text += f" OK:{self.__consecutive_successful_reads}"
            self.__draw_text(220, video_y - 15, status_text, self.__color_yellow, self.__font_small)
        
        # Draw CPU and load bars above the video window (now takes more space)
        self.__draw_cpu_info(150, video_y - 40)
        
        # Draw button labels
        self.__draw_button_labels()
        
        # Show the updated display
        self.__display.ShowImage(self.__splash)
    
    def update_battery(self, battery_level):
        """Update the battery level"""
        self.__battery_level = max(0, min(100, int(battery_level)))
        if self.__debug:
            print(f"Battery updated: {self.__battery_level}%")
    
    def update_speed(self, speed_scale):
        """Update the speed scale"""
        self.__speed_scale = max(0.1, min(2.0, float(speed_scale)))
        if self.__debug:
            print(f"Speed updated: {self.__speed_scale:.1f}x")
    
    def update_roll_balance(self, enabled):
        """Update the roll balance status"""
        self.__roll_balance_enabled = bool(enabled)
        if self.__debug:
            print(f"Roll balance updated: {'ON' if self.__roll_balance_enabled else 'OFF'}")
    
    def update_performance_mode(self, enabled):
        """Update the performance mode status"""
        self.__performance_mode_enabled = bool(enabled)
        if self.__debug:
            print(f"Performance mode updated: {'ON' if self.__performance_mode_enabled else 'OFF'}")
    
    def update_camera_status(self, enabled):
        """Update the camera status"""
        self.__camera_enabled = bool(enabled)
        if self.__debug:
            print(f"Camera updated: {'ON' if self.__camera_enabled else 'OFF'}")
    
    def update_status(self, status):
        """Update the robot status"""
        self.__robot_status = str(status)
        if self.__debug:
            print(f"Status updated: {self.__robot_status}")
    
    def set_video_instance(self, video_instance):
        """Set the video instance from external controller"""
        self.__video = video_instance
        if self.__debug:
            print(f"Video instance set: {video_instance is not None}")
    
    def get_controller_status(self):
        """Get the current controller connection status"""
        return self.__controller_connected
    
    def refresh_from_robot(self):
        """Refresh data from the robot if available"""
        if self.__robot is not None:
            try:
                # Try to read battery level using consolidated method
                battery_level = None
                
                # Read battery with retry logic
                battery_level = None
                
                # Try rider-specific method first
                if hasattr(self.__robot, 'rider_read_battery'):
                    battery_level = self.__read_sensor_with_retry('battery', self.__robot.rider_read_battery)
                elif hasattr(self.__robot, 'read_battery'):
                    battery_level = self.__read_sensor_with_retry('battery', self.__robot.read_battery)
                
                # Handle battery reading with better error recovery
                if battery_level is not None and battery_level > 0:
                    # Successful battery reading
                    self.__battery_read_failures = 0
                    self.__last_good_battery = int(battery_level)
                    self.update_battery(battery_level)
                    
                    if self.__debug:
                        print(f"✅ Battery reading successful: {battery_level}%")
                else:
                    # Failed battery reading
                    self.__battery_read_failures += 1
                    self.__consecutive_successful_reads = 0
                    
                    if self.__battery_read_failures <= self.__max_battery_failures:
                        # Use last good battery value for a few failures
                        self.update_battery(self.__last_good_battery)
                        
                        if self.__debug:
                            print(f"⚠️  Battery read failed ({self.__battery_read_failures}/{self.__max_battery_failures}), using cached value: {self.__last_good_battery}%")
                    else:
                        # Too many failures - show 0
                        self.update_battery(0)
                        
                        if self.__debug:
                            print(f"❌ Battery consistently failing ({self.__battery_read_failures} failures), showing 0%")
                
                # Read odometry data
                self.__read_odometry_data()
                
                # Read CPU data
                self.__read_cpu_data()
                    
            except Exception as e:
                if self.__debug:
                    print(f"Error reading from robot: {e}")
                self.update_battery(0)
    
    def set_external_controller_status(self, connected):
        """Set controller status from external source (overrides internal detection)"""
        self.__controller_connected = connected
        if self.__debug:
            print(f"External controller status set: {connected}")
    
    def refresh_and_update_display(self, external_controller_status=None):
        """Refresh data from robot and update the display - for integration use"""
        # Use external controller status if provided (from main controller)
        if external_controller_status is not None:
            self.set_external_controller_status(external_controller_status)
        
        # Always read CPU data regardless of robot connection
        self.__read_cpu_data()
        
        self.refresh_from_robot()
        self.__update_display()
    
    def stop(self):
        """Stop the display loop"""
        self.__running = False
    
    def cleanup(self):
        """Clean up resources"""
        try:
            # Clean up video first
            if self.__video:
                self.__video.cleanup()
                self.__video = None
            
            # Turn off the display properly
            print("Turning off LCD display...")
            
            # Send display off command (0x28)
            self.__display.command(0x28)
            time.sleep(0.1)
            
            # Send sleep in command (0x10) 
            self.__display.command(0x10)
            time.sleep(0.1)
            
            # Clear the display buffer
            self.__display.clear()
            
            print("✅ LCD display turned off")
        except Exception as e:
            print(f"⚠️  Error turning off display: {e}")
            # Fallback - just clear
            try:
                self.__display.clear()
            except:
                pass
    
    def __read_sensor_with_retry(self, sensor_name, sensor_func, max_retries=2):
        """Read sensor data with retry logic and error handling"""
        for attempt in range(max_retries + 1):
            try:
                value = sensor_func()
                if value is not None:
                    return float(value)
            except Exception as e:
                if self.__debug and attempt == max_retries:
                    print(f"⚠️  Failed to read {sensor_name} after {max_retries + 1} attempts: {e}")
                if attempt < max_retries:
                    time.sleep(0.05)  # Brief delay before retry
        return None

    def __read_odometry_data(self):
        """Read odometry/IMU data from robot with improved error handling"""
        if self.__robot is not None:
            try:
                # Try to read IMU data with retry logic
                new_roll = None
                new_pitch = None
                new_yaw = None
                
                # Read roll with retry
                if hasattr(self.__robot, 'rider_read_roll'):
                    new_roll = self.__read_sensor_with_retry('roll', self.__robot.rider_read_roll)
                elif hasattr(self.__robot, 'read_roll'):
                    new_roll = self.__read_sensor_with_retry('roll', self.__robot.read_roll)
                
                # Read pitch with retry
                if hasattr(self.__robot, 'rider_read_pitch'):
                    new_pitch = self.__read_sensor_with_retry('pitch', self.__robot.rider_read_pitch)
                elif hasattr(self.__robot, 'read_pitch'):
                    new_pitch = self.__read_sensor_with_retry('pitch', self.__robot.read_pitch)
                
                # Read yaw with retry
                if hasattr(self.__robot, 'rider_read_yaw'):
                    new_yaw = self.__read_sensor_with_retry('yaw', self.__robot.rider_read_yaw)
                elif hasattr(self.__robot, 'read_yaw'):
                    new_yaw = self.__read_sensor_with_retry('yaw', self.__robot.read_yaw)
                
                # Handle successful vs failed readings
                all_readings_successful = all(val is not None for val in [new_roll, new_pitch, new_yaw])
                
                if all_readings_successful:
                    # All readings successful - update values and reset failure counter
                    self.__roll = new_roll
                    self.__pitch = new_pitch
                    self.__yaw = new_yaw
                    self.__last_good_roll = new_roll
                    self.__last_good_pitch = new_pitch
                    self.__last_good_yaw = new_yaw
                    self.__sensor_read_failures = 0
                    
                    # Track consecutive successful reads for recovery
                    self.__consecutive_successful_reads += 1
                    
                    # Reset all failure counters after sustained success
                    if self.__consecutive_successful_reads >= self.__reset_failure_count_threshold:
                        self.__sensor_read_failures = 0
                        self.__battery_read_failures = 0
                        self.__consecutive_successful_reads = 0
                        if self.__debug:
                            print("🔄 Failure counters reset after sustained success")
                    
                    if self.__debug:
                        print(f"✅ IMU data - Roll: {self.__roll:.1f}°, Pitch: {self.__pitch:.1f}°, Yaw: {self.__yaw:.1f}°")
                else:
                    # Some readings failed - increment failure counter and reset success counter
                    self.__sensor_read_failures += 1
                    self.__consecutive_successful_reads = 0
                    
                    if self.__sensor_read_failures <= self.__max_sensor_failures:
                        # Use last good values for a few failures
                        self.__roll = self.__last_good_roll
                        self.__pitch = self.__last_good_pitch
                        self.__yaw = self.__last_good_yaw
                        
                        if self.__debug:
                            print(f"⚠️  IMU read failed ({self.__sensor_read_failures}/{self.__max_sensor_failures}), using cached values")
                    else:
                        # Too many failures - show zeros
                        self.__roll = self.__pitch = self.__yaw = 0.0
                        
                        if self.__debug:
                            print(f"❌ IMU consistently failing ({self.__sensor_read_failures} failures), showing zeros")
                    
            except Exception as e:
                self.__sensor_read_failures += 1
                self.__consecutive_successful_reads = 0
                if self.__debug:
                    print(f"❌ Error reading odometry data: {e}")
                
                # Use cached values if available, otherwise use zeros
                if self.__sensor_read_failures <= self.__max_sensor_failures:
                    self.__roll = self.__last_good_roll
                    self.__pitch = self.__last_good_pitch
                    self.__yaw = self.__last_good_yaw
                else:
                    self.__roll = self.__pitch = self.__yaw = 0.0 