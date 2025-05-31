#!/usr/bin/env python3
# coding=utf-8

# Rider Robot LCD Screen Display
# Shows battery level, percentage, and current speed setting
# Marc Wester

import time
import sys
import os
import xgoscreen.LCD_2inch as LCD_2inch
from PIL import Image, ImageDraw, ImageFont
from key import Button

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
        
        # Initialize LCD display
        self.__setup_display()
        
        # Initialize button for interaction
        self.__button = Button()
        
        if self.__debug:
            print("RiderScreen initialized")
    
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
        """Draw a visual battery indicator"""
        # Battery outline
        battery_width = 60
        battery_height = 25
        
        # Draw battery outline
        self.__draw_rect(x, y, battery_width, battery_height, self.__color_white, filled=False)
        
        # Draw battery terminal
        self.__draw_rect(x + battery_width, y + 8, 4, 9, self.__color_white, filled=True)
        
        # Draw battery fill based on level
        fill_width = int((battery_width - 4) * (battery_level / 100))
        if fill_width > 0:
            battery_color = self.__get_battery_color(battery_level)
            self.__draw_rect(x + 2, y + 2, fill_width, battery_height - 4, battery_color, filled=True)
    
    def __draw_speed_indicator(self, x, y, speed_scale):
        """Draw a visual speed indicator"""
        # Speed bar background
        bar_width = 150
        bar_height = 20
        
        # Draw speed bar outline
        self.__draw_rect(x, y, bar_width, bar_height, self.__color_white, filled=False)
        
        # Draw speed fill
        fill_width = int((bar_width - 4) * (speed_scale / 2.0))  # Max speed is 2.0
        if fill_width > 0:
            speed_color = self.__color_blue
            self.__draw_rect(x + 2, y + 2, fill_width, bar_height - 4, speed_color, filled=True)
    
    def __update_display(self):
        """Update the display with current information"""
        # Clear screen
        self.__clear_screen()
        
        # Controller status icon (upper left)
        self.__draw_controller_icon(10, 10)
        
        # Title
        self.__draw_text(90, 20, "RIDER ROBOT", self.__color_white, self.__font_large)
        
        # Status line
        status_color = self.__color_green if self.__robot_status == "Connected" else self.__color_red
        self.__draw_text(100, 50, f"Status: {self.__robot_status}", status_color, self.__font_small)
        
        # Battery section
        self.__draw_text(20, 90, "BATTERY", self.__color_white, self.__font_medium)
        
        # Battery indicator
        self.__draw_battery_indicator(20, 120, self.__battery_level)
        
        # Battery percentage
        battery_color = self.__get_battery_color(self.__battery_level)
        self.__draw_text(100, 115, f"{self.__battery_level}%", battery_color, self.__font_large)
        
        # Speed section
        self.__draw_text(20, 170, "SPEED SETTING", self.__color_white, self.__font_medium)
        
        # Speed indicator
        self.__draw_speed_indicator(20, 200, self.__speed_scale)
        
        # Speed value
        self.__draw_text(190, 195, f"{self.__speed_scale:.1f}x", self.__color_white, self.__font_medium)
        
        # Update timestamp
        current_time = time.strftime("%H:%M")
        self.__draw_text(270, 10, current_time, self.__color_white, self.__font_small)
        
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
    
    def update_status(self, status):
        """Update the robot status"""
        self.__robot_status = str(status)
        if self.__debug:
            print(f"Status updated: {self.__robot_status}")
    
    def get_controller_status(self):
        """Get the current controller connection status"""
        return self.__controller_connected
    
    def refresh_from_robot(self):
        """Refresh data from the robot if available"""
        if self.__robot is not None:
            try:
                # Try to read battery level
                battery_level = None
                
                # Try rider-specific method first
                try:
                    battery_level = self.__robot.rider_read_battery()
                except AttributeError:
                    # Fallback to standard method
                    try:
                        battery_level = self.__robot.read_battery()
                    except AttributeError:
                        battery_level = 0
                except Exception:
                    battery_level = 0
                
                if battery_level is not None and battery_level > 0:
                    self.update_battery(battery_level)
                    self.update_status("Connected")
                else:
                    self.update_status("No Battery Data")
                    
            except Exception as e:
                self.update_status("Connection Error")
                if self.__debug:
                    print(f"Error reading from robot: {e}")
    
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