#!/usr/bin/env python3
# coding=utf-8

# Rider Robot LCD Screen Display
# Shows battery level, percentage, and current speed setting
# This is the main screen file for the Rider robot
# Marc Wester

import time
import sys
import os
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
                
                # First try to use controller's battery reading method if we have a reference to it
                # For now, use the existing robot methods but consolidate the logic
                try:
                    battery_level = self.__robot.rider_read_battery()
                except AttributeError:
                    # Fallback to standard method
                    try:
                        battery_level = self.__robot.read_battery()
                    except AttributeError:
                        battery_level = 0
                except Exception:
                    # Final fallback
                    try:
                        battery_level = self.__robot.read_battery()
                    except:
                        battery_level = 0
                
                if battery_level is not None and battery_level > 0:
                    self.update_battery(battery_level)
                else:
                    self.update_battery(0)
                
                # Read odometry data
                self.__read_odometry_data()
                    
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
    
    def __read_odometry_data(self):
        """Read odometry/IMU data from robot"""
        if self.__robot is not None:
            try:
                # Try to read IMU data (roll, pitch, yaw) as odometry substitute
                try:
                    self.__roll = self.__robot.rider_read_roll() if hasattr(self.__robot, 'rider_read_roll') else self.__robot.read_roll()
                except (AttributeError, Exception):
                    self.__roll = 0.0
                
                try:
                    self.__pitch = self.__robot.rider_read_pitch() if hasattr(self.__robot, 'rider_read_pitch') else self.__robot.read_pitch()
                except (AttributeError, Exception):
                    self.__pitch = 0.0
                
                try:
                    self.__yaw = self.__robot.rider_read_yaw() if hasattr(self.__robot, 'rider_read_yaw') else self.__robot.read_yaw()
                except (AttributeError, Exception):
                    self.__yaw = 0.0
                    
                if self.__debug:
                    print(f"Odometry data - Roll: {self.__roll:.1f}°, Pitch: {self.__pitch:.1f}°, Yaw: {self.__yaw:.1f}°")
                    
            except Exception as e:
                if self.__debug:
                    print(f"Error reading odometry data: {e}")
                self.__roll = self.__pitch = self.__yaw = 0.0 