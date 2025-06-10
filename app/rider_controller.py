#!/usr/bin/env python3
# coding=utf-8

# This is a bluetooth controller for the Rider two wheel balancing robot
# This is the main controller file for the Rider robot
# Includes video streaming support via rider_video.py
# Marc Wester

import os
import sys
import time
import pygame
from xgo_toolkit import XGO
from rider_screen import RiderScreen
from rider_video import RiderVideo
from rider_mqtt import RiderMQTT
from key import Button

class BluetoothController_Rider(object):
    
    # Centralized button mapping for PlayStation controller
    # Easy to modify for different controllers
    BUTTON_MAPPING = {
        'MIN_HEIGHT': 0,           # A/X button - Lower to minimum height
        'PERFORMANCE_MODE': 1,      # B/Circle button - Toggle performance mode
        'MAX_HEIGHT': 2,          # Triangle button - Raise to maximum height
        'ROLL_BALANCE': 3,          # Square button - Toggle roll balance
        'SPEED_DOWN': 4,            # L1 - Decrease speed
        'SPEED_UP': 5,              # R1 - Increase speed
        'RESET': 9,                 # Back/Select - Reset robot
        'EMERGENCY_STOP': 10,        # Home button - Emergency stop
        'HEIGHT_DOWN': 11,          # Left stick click - Decrease height
        'HEIGHT_UP': 12,            # PS button - Increase height
    }
    
    # Axis mapping for PlayStation controller
    AXIS_MAPPING = {
        'LEFT_STICK_X': 0,
        'LEFT_STICK_Y': 1, 
        'RIGHT_STICK_X': 3,         # Inverted with minus sign in code
        'RIGHT_STICK_Y': 4,
    }
    
    def __init__(self, robot, controller_id=0, debug=False):
        self.__debug = debug
        self.__controller_id = int(controller_id)
        self.__controller_connected = False
        self.__robot = robot
        self.__running = False
        
        # Movement parameters
        self.__speed_scale = 1.0
        self.__turn_scale = 100
        self.__height = 85
        self.__height_min = 75
        self.__height_max = 115
        
        # Roll balance state
        self.__roll_balance_enabled = False
        
        # Performance mode state
        self.__performance_mode_enabled = False
        
        # Camera state (will be set to True if camera is available during setup)
        self.__camera_enabled = False
        self.__video = None
        
        # Button states
        self.__button_states = {}
        
        # Action state tracking
        self.__action_in_progress = False
        self.__action_end_time = 0
        
        # Controller activity tracking for robust connection monitoring
        self.__controller_timeout = 10.0  # 10 seconds timeout
        self.__last_controller_activity = 0
        self.__controllers_initialized = []
        
        # PYGAME 2.6.1 COMPATIBILITY FIXES
        os.environ['SDL_VIDEODRIVER'] = 'dummy'  # Use dummy video driver for headless operation
        os.environ['SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS'] = '1'  # CRITICAL FIX for pygame 2.6.1
        
        # Initialize pygame with improved controller detection
        self.__setup_pygame()
        
        self.STATE_OK = 0
        self.STATE_NO_CONTROLLER = 1
        self.STATE_DISCONNECT = 2
        self.STATE_STOP = 3
        
        # Initialize LCD screen display if available
        self.__screen = None
        self.__screen_last_update = 0
        self.__screen_update_interval = 2.0  # Update screen every 2 seconds
        
        # Initialize MQTT communication
        self.__mqtt_client = None
        self.__mqtt_last_update = 0
        self.__mqtt_update_interval = 1.0  # Update MQTT state every second
        
        # Add button reader
        self.__robot_button = Button()  # Screen button reader for the robot

        # Always try to initialize the screen, regardless of controller status
        try:
            print("📺 Initializing LCD screen display...")
            self.__screen = RiderScreen(robot=self.__robot, debug=self.__debug)
            
            # Set initial screen status based on controller connection
            self.__screen.update_speed(self.__speed_scale)
            self.__screen.update_roll_balance(self.__roll_balance_enabled)
            self.__screen.update_performance_mode(self.__performance_mode_enabled)
            
            if self.__controller_connected:
                # Force initial display update with main controller status
                self.__screen.refresh_and_update_display(self.__controller_connected)
            else:
                # Force initial display update showing no controller
                self.__screen.set_external_controller_status(False)
                self.__screen.refresh_and_update_display(False)
            
            print("✅ LCD screen initialized successfully")
        except Exception as e:
            print(f"⚠️  Failed to initialize LCD screen: {e}")
            self.__screen = None
        
        # Initialize camera after screen is set up
        self.__setup_camera()
        
        # Connect video instance to screen
        if self.__screen and self.__video:
            self.__screen.set_video_instance(self.__video)
        
        # Initialize MQTT communication system
        self.__setup_mqtt()
        
        # Initialize battery display on screen after MQTT is ready
        if self.__screen and self.__mqtt_client:
            try:
                # Give MQTT a moment to get initial battery reading
                time.sleep(0.5)
                robot_state = self.__mqtt_client.get_robot_state()
                initial_battery = robot_state.get('battery_level', 0) or 0
                if initial_battery > 0:
                    self.__screen.update_battery(initial_battery)
                    if self.__debug:
                        print(f"✅ Initial battery level set on screen: {initial_battery}%")
            except Exception as e:
                if self.__debug:
                    print(f"⚠️  Could not set initial battery on screen: {e}")
        
        # Battery reading is now handled by MQTT status updates only
        print("✅ Battery monitoring will be handled via MQTT status updates")
    
    def __setup_pygame(self):
        """Initialize pygame with robust controller detection (integrated from rider_screen.py)"""
        try:
            pygame.init()
            pygame.joystick.init()
            
            # PYGAME 2.6.1 FIX - Force refresh joystick detection
            pygame.joystick.quit()
            pygame.joystick.init()
            time.sleep(0.2)  # Brief pause for detection
            
            # Initialize a minimal display to prevent pygame errors
            try:
                pygame.display.set_mode((1, 1))
            except:
                # Fallback: create pygame surface without display
                try:
                    pygame.display.init()
                except:
                    pass
            
            # Initialize any detected controllers
            controller_count = pygame.joystick.get_count()
            self.__controllers_initialized = []
            
            print('Bluetooth Controllers Available:')
            if controller_count == 0:
                print('    No controllers found!')
                self.__controller_connected = False
                return
                
            for i in range(controller_count):
                controller = pygame.joystick.Joystick(i)
                print(f'    Controller {i}: {controller.get_name()}')
            
            # Initialize the specified controller and any others for monitoring
            for i in range(controller_count):
                try:
                    joystick = pygame.joystick.Joystick(i)
                    joystick.init()
                    
                    # PYGAME 2.6.1 FIX - Verify controller initialized properly
                    if not joystick.get_init():
                        raise Exception("Controller failed to initialize")
                    
                    self.__controllers_initialized.append(joystick)
                    
                    # Set the main controller
                    if i == self.__controller_id:
                        self.__controller = joystick
                        self.__controller_connected = True
                    
                    if self.__debug:
                        print(f"Initialized controller {i}: {joystick.get_name()}")
                        
                except Exception as e:
                    if self.__debug:
                        print(f"Failed to initialize controller {i}: {e}")
            
            # Set initial activity time if controllers are present
            if controller_count > 0 and self.__controller_connected:
                self.__last_controller_activity = time.time()
                if self.__debug:
                    print(f"Controllers detected: {controller_count}")
            else:
                if self.__controller_id >= controller_count:
                    print(f'---Controller {self.__controller_id} not found---')
                self.__controller_connected = False
                
        except Exception as e:
            print(f'---Failed to initialize pygame: {e}---')
            self.__controller_connected = False
    
    def __setup_camera(self):
        """Initialize camera system"""
        try:
            print("📷 Initializing camera system...")
            self.__video = RiderVideo(camera_id=0, debug=self.__debug)
            
            if self.__video.is_camera_available():
                print("✅ Camera detected - starting streaming...")
                # Start streaming immediately on startup
                if self.__video.start_streaming():
                    self.__camera_enabled = True
                    print("✅ Camera enabled on startup")
                    if self.__screen:
                        self.__screen.update_camera_status(True)
                        self.__screen.update_status("Camera: ON")
                else:
                    print("❌ Failed to start camera on startup")
                    self.__camera_enabled = False
                    if self.__screen:
                        self.__screen.update_camera_status(False)
                        self.__screen.update_status("Camera Failed")
            else:
                print("⚠️  No camera detected")
                self.__video = None
                self.__camera_enabled = False
                if self.__screen:
                    self.__screen.update_camera_status(False)
                    self.__screen.update_status("No Camera")
                    
        except Exception as e:
            print(f"⚠️  Failed to initialize camera: {e}")
            self.__video = None
            self.__camera_enabled = False
            if self.__screen:
                self.__screen.update_camera_status(False)
                self.__screen.update_status("Camera Error")
    
    def __setup_mqtt(self):
        """Initialize MQTT communication system"""
        try:
            print("📡 Initializing MQTT communication...")
            self.__mqtt_client = RiderMQTT(robot=self.__robot, debug=self.__debug)
            
            # Set up command callbacks for remote control
            self.__mqtt_client.set_command_callback('movement', self.__handle_mqtt_movement)
            self.__mqtt_client.set_command_callback('settings', self.__handle_mqtt_settings)
            self.__mqtt_client.set_command_callback('camera', self.__handle_mqtt_camera)
            self.__mqtt_client.set_command_callback('system', self.__handle_mqtt_system)
            
            # Connect to MQTT broker
            if self.__mqtt_client.connect():
                print("✅ MQTT communication enabled")
                if self.__screen:
                    self.__screen.update_status("MQTT: Connected")
            else:
                print("⚠️  MQTT broker connection failed")
                if self.__screen:
                    self.__screen.update_status("MQTT: Failed")
                    
        except Exception as e:
            print(f"⚠️  Failed to initialize MQTT: {e}")
            self.__mqtt_client = None
            if self.__screen:
                self.__screen.update_status("MQTT: Error")
    
    def __handle_mqtt_movement(self, payload):
        """Handle movement commands from MQTT"""
        if self.__debug:
            print(f"🎮 MQTT Movement command: {payload}")
        
        # The actual movement is already handled in rider_mqtt.py
        # This callback is for additional controller-specific logic
        x = payload.get('x', 0)
        y = payload.get('y', 0)
        
        # Update screen with remote control status
        if self.__screen:
            if x != 0 or y != 0:
                self.__screen.update_status("Remote Control")
            else:
                self.__screen.update_status("MQTT: Connected")
        
    def __handle_mqtt_settings(self, payload):
        """Handle settings commands from MQTT"""
        if self.__debug:
            print(f"⚙️  MQTT Settings command: {payload}")
        
        # The actual settings changes are handled in rider_mqtt.py
        # Update the controller's local state to match
        action = payload.get('action')
        
        if action == 'toggle_roll_balance':
            # Sync local state with MQTT state
            if self.__mqtt_client:
                robot_state = self.__mqtt_client.get_robot_state()
                self.__roll_balance_enabled = robot_state['roll_balance_enabled']
                if self.__screen:
                    self.__screen.update_roll_balance(self.__roll_balance_enabled)
        
        elif action == 'toggle_performance':
            # Sync local state with MQTT state
            if self.__mqtt_client:
                robot_state = self.__mqtt_client.get_robot_state()
                self.__performance_mode_enabled = robot_state['performance_mode_enabled']
                if self.__screen:
                    self.__screen.update_performance_mode(self.__performance_mode_enabled)
        
        elif action == 'change_speed':
            # Sync local state with MQTT state
            if self.__mqtt_client:
                robot_state = self.__mqtt_client.get_robot_state()
                self.__speed_scale = robot_state['speed_scale']
                if self.__screen:
                    self.__screen.update_speed(self.__speed_scale)
        
    def __handle_mqtt_camera(self, payload):
        """Handle camera commands from MQTT"""
        if self.__debug:
            print(f"📷 MQTT Camera command: {payload}")
        
        # The actual camera toggle is handled in rider_mqtt.py
        # Update the controller's local state to match
        action = payload.get('action', 'toggle_camera')
        
        if action == 'toggle_camera':
            # Sync local state with MQTT state
            if self.__mqtt_client:
                robot_state = self.__mqtt_client.get_robot_state()
                self.__camera_enabled = robot_state['camera_enabled']
                
                # Actually toggle the camera hardware
                if self.__video and self.__video.is_camera_available():
                    if self.__camera_enabled:
                        if self.__video.start_streaming():
                            if self.__screen:
                                self.__screen.update_camera_status(True)
                                self.__screen.update_status("Camera: ON")
                        else:
                            self.__camera_enabled = False
                            if self.__screen:
                                self.__screen.update_camera_status(False)
                                self.__screen.update_status("Camera Failed")
                    else:
                        self.__video.stop_streaming()
                        if self.__screen:
                            self.__screen.update_camera_status(False)
                            self.__screen.update_status("Camera: OFF")
        
    def __handle_mqtt_system(self, payload):
        """Handle system commands from MQTT"""
        if self.__debug:
            print(f"🔧 MQTT System command: {payload}")
        
        # The actual system commands are handled in rider_mqtt.py
        # Update screen status for system commands
        action = payload.get('action')
        
        if action == 'emergency_stop':
            if self.__screen:
                self.__screen.update_status("EMERGENCY STOP!")
            
            # Clear any ongoing action in the controller
            self.__action_in_progress = False
    
    def __toggle_camera(self):
        """Toggle camera on/off"""
        if self.__video is None or not self.__video.is_camera_available():
            print("❌ Camera not available")
            if self.__screen:
                self.__screen.update_status("No Camera Available")
            return
        
        self.__camera_enabled = not self.__camera_enabled
        
        if self.__camera_enabled:
            print("📷 Enabling camera...")
            if self.__video.start_streaming():
                print("✅ Camera enabled")
                if self.__screen:
                    self.__screen.update_camera_status(True)
                    self.__screen.update_status("Camera: ON")
            else:
                print("❌ Failed to start camera")
                self.__camera_enabled = False
                if self.__screen:
                    self.__screen.update_camera_status(False)
                    self.__screen.update_status("Camera Failed")
        else:
            print("📷 Disabling camera...")
            self.__video.stop_streaming()
            print("✅ Camera disabled")
            if self.__screen:
                self.__screen.update_camera_status(False)
                self.__screen.update_status("Camera: OFF")

    def __check_controller_activity(self):
        """Check for controller activity and update connection status (integrated from rider_screen.py)"""
        try:
            current_time = time.time()
            activity_detected = False
            
            # Process pygame events to detect controller activity
            for event in pygame.event.get():
                if event.type in [pygame.JOYAXISMOTION, pygame.JOYBUTTONDOWN, 
                                pygame.JOYBUTTONUP, pygame.JOYHATMOTION]:
                    # Controller activity detected!
                    self.__last_controller_activity = current_time
                    activity_detected = True
                    if self.__debug and not self.__controller_connected:
                        print("🎮 Controller activity detected - marking as connected")
                
                elif event.type == pygame.JOYDEVICEADDED:
                    # New controller connected
                    try:
                        controller_count = pygame.joystick.get_count()
                        # Re-initialize controllers
                        self.__controllers_initialized = []
                        for i in range(controller_count):
                            joystick = pygame.joystick.Joystick(i)
                            joystick.init()
                            self.__controllers_initialized.append(joystick)
                            
                            # Update main controller if needed
                            if i == self.__controller_id:
                                self.__controller = joystick
                        
                        self.__last_controller_activity = current_time
                        activity_detected = True
                        self.__controller_connected = True
                        if self.__debug:
                            print(f"🟢 Controller connected: {controller_count} total")
                    except Exception as e:
                        if self.__debug:
                            print(f"Error handling controller connection: {e}")
                
                elif event.type == pygame.JOYDEVICEREMOVED:
                    if self.__debug:
                        print("🔴 Controller disconnect event received")
                    # Don't immediately mark as disconnected - let timeout handle it
            
            # Check if we have any controllers at all
            controller_count = pygame.joystick.get_count()
            
            if controller_count == 0:
                # No controllers detected by system
                if self.__controller_connected and self.__debug:
                    print("📊 No controllers detected by system - marking as disconnected")
                self.__controller_connected = False
            else:
                # We have controllers - check timeout
                time_since_activity = current_time - self.__last_controller_activity
                
                if time_since_activity <= self.__controller_timeout:
                    # Recent activity - controller is connected
                    if not self.__controller_connected and self.__debug:
                        print(f"✅ Controller marked as connected (activity {time_since_activity:.1f}s ago)")
                    self.__controller_connected = True
                else:
                    # No recent activity - consider disconnected
                    if self.__controller_connected and self.__debug:
                        print(f"⏰ Controller timeout ({time_since_activity:.1f}s) - marking as disconnected")
                    self.__controller_connected = False
                    
                    # Update screen with disconnection status
                    if self.__screen:
                        # Pass controller status to screen to override its internal detection
                        self.__screen.set_external_controller_status(False)
                
        except Exception as e:
            if self.__debug:
                print(f"❌ Error checking controller activity: {e}")
            # Fallback to simple count check
            try:
                self.__controller_connected = pygame.joystick.get_count() > 0
            except:
                self.__controller_connected = False
    
    def is_connected(self):
        return self.__controller_connected
    
    def __robot_reset(self):
        """Reset robot to default state"""
        self.__robot.rider_reset()
        self.__height = 85
        self.__speed_scale = 1.0
        self.__turn_scale = 50  # Use consistent value
        
        # Reset roll balance to disabled state
        self.__roll_balance_enabled = False
        self.__robot.rider_balance_roll(0)
        
        # Reset performance mode to disabled state
        self.__performance_mode_enabled = False
        self.__robot.rider_perform(0)
        
        # Update screen with reset values
        if self.__screen:
            self.__screen.update_speed(self.__speed_scale)
            self.__screen.update_roll_balance(self.__roll_balance_enabled)
            self.__screen.update_performance_mode(self.__performance_mode_enabled)
        
        if self.__debug:
            print("Robot reset to default state - Roll balance and performance mode disabled")
    
    # Battery reading is now consolidated in MQTT status updates only
    
    # Battery display is now handled by MQTT status updates only
    
    def __update_mqtt_state(self):
        """Update MQTT with current robot state"""
        if not self.__mqtt_client or not self.__mqtt_client.is_connected():
            return
            
        try:
            # Battery level is now handled in MQTT status updates
            # Get from MQTT state if available, otherwise use placeholder
            current_battery = 0  # Battery percentage (0-100%)
            if self.__mqtt_client:
                robot_state = self.__mqtt_client.get_robot_state()
                current_battery = robot_state.get('battery_level', 0) or 0  # Battery percentage (0-100%)
            
            # Update MQTT with current robot state
            self.__mqtt_client.update_robot_state(
                battery_level=current_battery,
                speed_scale=self.__speed_scale,
                roll_balance_enabled=self.__roll_balance_enabled,
                performance_mode_enabled=self.__performance_mode_enabled,
                camera_enabled=self.__camera_enabled,
                controller_connected=self.__controller_connected,
                height=self.__height,
                connection_status='connected' if self.__controller_connected else 'disconnected'
            )
            
            if self.__debug:
                print(f"📡 MQTT state updated - Battery: {current_battery}%, Speed: {self.__speed_scale:.1f}x")
                
        except Exception as e:
            if self.__debug:
                print(f"⚠️  Error updating MQTT state: {e}")
    
    def __process_movement(self, left_stick_x, left_stick_y, right_stick_x, right_stick_y):
        """Process analog stick movements for robot control"""
        
        # Don't process movement if action is in progress
        if self.__action_in_progress and time.time() < self.__action_end_time:
            return
        elif self.__action_in_progress and time.time() >= self.__action_end_time:
            self.__action_in_progress = False
            if self.__debug:
                print("Action completed, resuming movement control")
        
        # Dead zone to prevent drift
        dead_zone = 0.1
        
        # Apply dead zone
        if abs(left_stick_x) < dead_zone:
            left_stick_x = 0
        if abs(left_stick_y) < dead_zone:
            left_stick_y = 0
        if abs(right_stick_x) < dead_zone:
            right_stick_x = 0
        if abs(right_stick_y) < dead_zone:
            right_stick_y = 0
        
        # Left stick controls forward/backward movement
        if abs(left_stick_y) > 0:
            speed = -left_stick_y * self.__speed_scale  # Invert Y axis
            
            # Apply asymmetric scaling to compensate for hardware differences
            if speed < 0:  # Backward movement (negative speed)
                speed *= 1.5  # Increase backward speed by 50% to match forward
            
            # Limit speed to safe values
            speed = max(-0.75, min(0.5, speed))  # Allow slightly more backward speed
            self.__robot.rider_move_x(speed)
            if self.__debug:
                if not hasattr(self, '_last_move_debug') or abs(speed - self._last_move_debug) > 0.1:
                    direction = "FORWARD" if speed > 0 else "BACKWARD"
                    print(f"Move: {speed:.2f} ({direction})")
                    self._last_move_debug = speed
        else:
            self.__robot.rider_move_x(0)
            # Reset debug tracking (only in debug mode)
            if self.__debug and hasattr(self, '_last_move_debug'):
                delattr(self, '_last_move_debug')
        
        # Right stick controls turning - SIMPLIFIED LOGIC
        if abs(right_stick_x) > 0:
            # Use a different approach for turning
            turn_speed = right_stick_x * self.__turn_scale
            
            # Ensure minimum effective turn value
            if abs(turn_speed) > 0 and abs(turn_speed) < 20:
                turn_speed = 20 if turn_speed > 0 else -20
            
            # Simplified debug output (only show when turn value changes significantly)
            if self.__debug:
                if not hasattr(self, '_last_turn_debug') or abs(turn_speed - self._last_turn_debug) > 10:
                    print(f"🎮 TURN: {turn_speed:.0f} (stick: {right_stick_x:.2f})")
                    self._last_turn_debug = turn_speed
            
            # Try primary turn method only to avoid conflicts
            try:
                self.__robot.rider_turn(int(turn_speed))
            except Exception as e:
                if self.__debug:
                    print(f"❌ Turn failed: {e}")
                    
        else:
            # Stop turning - ensure all turn methods are stopped
            try:
                self.__robot.rider_turn(0)
            except:
                pass
            try:
                self.__robot.rider_move_y(0)
            except:
                pass
            # Reset debug tracking (only in debug mode)
            if self.__debug and hasattr(self, '_last_turn_debug'):
                delattr(self, '_last_turn_debug')
    
    def __process_buttons(self, button_id, pressed):
        """Process button presses"""
        
        if button_id not in self.__button_states:
            self.__button_states[button_id] = False
        
        # Only process on button press (not release)
        if pressed and not self.__button_states[button_id]:
            self.__button_states[button_id] = True
            
            if self.__debug:
                print(f"Button {button_id} pressed")
            
            # Button mappings using centralized mapping
            if button_id == self.BUTTON_MAPPING['MIN_HEIGHT']:  # A/X button
                # Lower robot to minimum height
                self.__height = self.__height_min
                self.__robot.rider_height(self.__height)
                if self.__debug:
                    print(f"Robot lowered to minimum height: {self.__height}")
                    
            elif button_id == self.BUTTON_MAPPING['PERFORMANCE_MODE']:  # B/Circle button
                # Toggle performance mode
                self.__performance_mode_enabled = not self.__performance_mode_enabled
                self.__robot.rider_perform(1 if self.__performance_mode_enabled else 0)

                # Update screen with new status
                if self.__screen:
                    self.__screen.update_performance_mode(self.__performance_mode_enabled)
                
                if self.__debug:
                    print(f"Performance mode {'enabled' if self.__performance_mode_enabled else 'disabled'}")
                    
            elif button_id == self.BUTTON_MAPPING['MAX_HEIGHT']:  # Triangle button
                # Raise robot to maximum height
                self.__height = self.__height_max
                self.__robot.rider_height(self.__height)
                if self.__debug:
                    print(f"Robot raised to maximum height: {self.__height}")
                    
            elif button_id == self.BUTTON_MAPPING['ROLL_BALANCE']:  # Square button
                # Toggle roll balance
                self.__roll_balance_enabled = not self.__roll_balance_enabled
                self.__robot.rider_balance_roll(1 if self.__roll_balance_enabled else 0)
                
                # Update screen with new status
                if self.__screen:
                    self.__screen.update_roll_balance(self.__roll_balance_enabled)
                
                if self.__debug:
                    print(f"Roll balance {'enabled' if self.__roll_balance_enabled else 'disabled'}")
                    
            elif button_id == self.BUTTON_MAPPING['SPEED_DOWN']:  # L1 button
                # Decrease speed
                self.__speed_scale = max(0.1, self.__speed_scale - 0.1)
                print(f"Speed decreased to: {self.__speed_scale:.1f}")
                # Update screen with new speed
                if self.__screen:
                    self.__screen.update_speed(self.__speed_scale)
                    
            elif button_id == self.BUTTON_MAPPING['SPEED_UP']:  # R1 button
                # Increase speed
                self.__speed_scale = min(2.0, self.__speed_scale + 0.1)
                print(f"Speed increased to: {self.__speed_scale:.1f}")
                # Update screen with new speed
                if self.__screen:
                    self.__screen.update_speed(self.__speed_scale)
                    
            elif button_id == self.BUTTON_MAPPING['RESET']:  # Back/Select button
                # Reset robot
                self.__robot_reset()
                if self.__debug:
                    print("Robot reset")
                    
            elif button_id == self.BUTTON_MAPPING['EMERGENCY_STOP']:  # Start button
                # Emergency stop
                self.__robot.rider_reset_odom()
                self.__robot.rider_move_x(0)
                self.__robot.rider_turn(0)
                try:
                    self.__robot.rider_move_y(0)
                except:
                    pass
                self.__action_in_progress = False  # Clear any ongoing action
                if self.__debug:
                    print("Emergency stop")
                    
            elif button_id == self.BUTTON_MAPPING['HEIGHT_DOWN']:  # Left stick click
                # Decrease height
                self.__height = max(self.__height_min, self.__height - 5)
                self.__robot.rider_height(self.__height)
                if self.__debug:
                    print(f"Height decreased to: {self.__height}")
                    
        elif not pressed:
            self.__button_states[button_id] = False
    
    def __process_dpad(self, hat_x, hat_y):
        """Process D-pad input"""
        if hat_x != 0 or hat_y != 0:
            if self.__debug:
                print(f"D-pad: x={hat_x}, y={hat_y}")
            
            # Stop current movement and actions
            self.__robot.rider_move_x(0)
            self.__robot.rider_turn(0)
            try:
                self.__robot.rider_move_y(0)
            except:
                pass
            
            # D-pad for quick movements - IMPROVED VALUES
            if hat_y == 1:  # Up
                self.__action_in_progress = True
                self.__action_end_time = time.time() + 0.5  # Short action
                self.__robot.rider_move_x(0.3)
                time.sleep(0.3)
                self.__robot.rider_move_x(0)
            elif hat_y == -1:  # Down
                self.__action_in_progress = True
                self.__action_end_time = time.time() + 0.5  # Short action
                self.__robot.rider_move_x(-0.3)
                time.sleep(0.3)
                self.__robot.rider_move_x(0)
            elif hat_x == -1:  # Left - USING IMPROVED TURN LOGIC
                self.__action_in_progress = True
                self.__action_end_time = time.time() + 0.5  # Short action
                try:
                    self.__robot.rider_turn(30)  # Use working minimum value
                    time.sleep(0.3)
                    self.__robot.rider_turn(0)
                except:
                    # Fallback to movement-based turning
                    try:
                        self.__robot.rider_move_y(0.3)
                        time.sleep(0.3)
                        self.__robot.rider_move_y(0)
                    except:
                        if self.__debug:
                            print("D-pad left turn failed")
            elif hat_x == 1:  # Right - USING IMPROVED TURN LOGIC
                self.__action_in_progress = True
                self.__action_end_time = time.time() + 0.5  # Short action
                try:
                    self.__robot.rider_turn(-30)  # Use working minimum value
                    time.sleep(0.3)
                    self.__robot.rider_turn(0)
                except:
                    # Fallback to movement-based turning
                    try:
                        self.__robot.rider_move_y(-0.3)
                        time.sleep(0.3)
                        self.__robot.rider_move_y(0)
                    except:
                        if self.__debug:
                            print("D-pad right turn failed")

    def __check_robot_buttons(self):
        """Check robot's physical buttons around edge of the screen"""
        if self.__robot_button.press_a():   # A button is on the lower right side of the screen
            print("Robot Button A pressed!")
            print("🛑 Quit button pressed - stopping program...")

            if self.__screen:
                # Force initial display update with main controller status
                self.__screen.refresh_and_update_display(self.__controller_connected)
            # Stop the control loop
            self.__running = False
            
        elif self.__robot_button.press_b():   # B button is on the lower left side of the screen
            print("Robot Button B pressed!")
            print("🎥 Camera button pressed - toggling camera...")
            self.__toggle_camera()
            
        elif self.__robot_button.press_c():  # C button is on the upper left side of the screen
            print("Robot Button C pressed!")
            print("🔌 Shutdown button pressed - initiating graceful system shutdown...")
            
            # Update screen with shutdown message if available
            if self.__screen:
                self.__screen.update_status("SHUTTING DOWN...")
                self.__screen.refresh_and_update_display(self.__controller_connected)
            
            # Stop the control loop first
            self.__running = False
            
            # Perform cleanup operations
            try:
                self.cleanup()
                print("✅ Cleanup completed - shutting down system...")
            except Exception as e:
                print(f"⚠️  Warning during cleanup: {e}")
            
            # Initiate system shutdown
            try:
                import subprocess
                print("🔌 Executing system shutdown...")
                subprocess.run(['sudo', 'shutdown', '-h', 'now'], check=True)
            except subprocess.CalledProcessError as e:
                print(f"❌ Failed to execute shutdown command: {e}")
                print("   Try running: sudo shutdown -h now")
            except Exception as e:
                print(f"❌ Shutdown error: {e}")
                # Fallback to alternative shutdown method
                try:
                    import os
                    os.system('sudo shutdown -h now')
                except Exception as e2:
                    print(f"❌ Fallback shutdown failed: {e2}")
                    print("   Manual shutdown required")
            
        elif self.__robot_button.press_d():   # D button is on the upper right side of the screen
            print("Robot Button D pressed!")
            # Add your functionality here

    def start_control_loop(self):
        """Start the main control loop"""
        # Don't exit immediately if no controller - wait for one to connect
        if not self.__controller_connected:
            print("No controller connected at startup - waiting for controller...")
            print("Press Ctrl+C to exit")
        
        self.__running = True
        
        # Initialize debug counter for periodic status updates
        if self.__debug:
            self._debug_counter = 0
        
        try:
            clock = pygame.time.Clock()
            controller_check_interval = 0.3  # Check controller every 0.3 seconds
            last_controller_check = 0
            
            # If no controller at startup, enter waiting mode immediately
            if not self.__controller_connected:
                self._enter_controller_waiting_mode()
            
            while self.__running:
                current_time = time.time()
                
                # IMPROVED CONTROLLER MONITORING - Check for controller events regularly
                if current_time - last_controller_check >= controller_check_interval:
                    self.__check_controller_activity()
                    last_controller_check = current_time
                    
                    # If controller disconnected, handle gracefully by waiting for reconnection
                    if not self.__controller_connected:
                        # Stop robot movement immediately for safety
                        self.__robot.rider_move_x(0)
                        self.__robot.rider_turn(0)
                        try:
                            self.__robot.rider_move_y(0)
                        except:
                            pass
                        
                        # Update screen status
                        if self.__screen:
                            # Override screen's controller detection with main controller status
                            self.__screen.set_external_controller_status(False)
                        
                        # Immediately update MQTT with disconnect status before entering waiting mode
                        if self.__mqtt_client:
                            try:
                                self.__update_mqtt_state()
                                if self.__debug:
                                    print("📡 MQTT immediately updated with controller disconnect status")
                            except Exception as e:
                                if self.__debug:
                                    print(f"Error updating MQTT on disconnect: {e}")
                        
                        # Enter waiting mode
                        self._enter_controller_waiting_mode()
                
                # Only process controller input if connected
                if not self.__controller_connected:
                    # Skip processing if not connected (we're in waiting mode above)
                    time.sleep(0.1)
                    continue
                
                # Process pygame events for buttons and movement (only if connected)
                if self.__controller_connected:
                    # PYGAME 2.6.1 FIX - Force event pump to ensure events are processed
                    pygame.event.pump()
                    
                    # Process button events specifically 
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            self.__running = False
                            break
                        
                        elif event.type == pygame.JOYBUTTONDOWN:
                            self.__process_buttons(event.button, True)
                            # Mark activity
                            self.__last_controller_activity = current_time
                        
                        elif event.type == pygame.JOYBUTTONUP:
                            self.__process_buttons(event.button, False)
                            # Mark activity
                            self.__last_controller_activity = current_time
                        
                        elif event.type == pygame.JOYHATMOTION:
                            self.__process_dpad(event.value[0], event.value[1])
                            # Mark activity
                            self.__last_controller_activity = current_time
                
                if not self.__running:
                    break
                
                # Get analog stick values (only if connected)
                if self.__controller_connected:
                    try:
                        # PYGAME 2.6.1 FIX - Verify controller is still connected
                        if not self.__controller.get_init():
                            print("🔴 Controller hardware disconnected!")
                            self.__controller_connected = False
                            # Don't return here - let the next iteration handle it in waiting mode
                            continue
                        
                        # Standard mapping first
                        left_stick_x = self.__controller.get_axis(self.AXIS_MAPPING['LEFT_STICK_X'])
                        left_stick_y = self.__controller.get_axis(self.AXIS_MAPPING['LEFT_STICK_Y'])
                        right_stick_x = -self.__controller.get_axis(self.AXIS_MAPPING['RIGHT_STICK_X'])  # Inverted direction
                        right_stick_y = self.__controller.get_axis(self.AXIS_MAPPING['RIGHT_STICK_Y'])
                        
                        # Mark activity if sticks are being used
                        if (abs(left_stick_x) > 0.05 or abs(left_stick_y) > 0.05 or 
                            abs(right_stick_x) > 0.05 or abs(right_stick_y) > 0.05):
                            self.__last_controller_activity = current_time
                        

                        
                        # Debug: Show controller info periodically
                        if self.__debug and hasattr(self, '_debug_counter'):
                            self._debug_counter += 1
                            if self._debug_counter % 100 == 0:  # Every 2 seconds at 50Hz
                                time_since_activity = current_time - self.__last_controller_activity
                                print(f"🎮 Controller Status: {self.__controller.get_name()}")
                                print(f"   Last activity: {time_since_activity:.1f}s ago")
                                print(f"   Axes count: {self.__controller.get_numaxes()}")
                                print(f"   Current axes: [0]={left_stick_x:.3f} [1]={left_stick_y:.3f} [3]={right_stick_x:.3f} [4]={right_stick_y:.3f}")
                                if self.__controller.get_numaxes() > 4:
                                    extra_axes = []
                                    used_axes = [self.AXIS_MAPPING['LEFT_STICK_X'], self.AXIS_MAPPING['LEFT_STICK_Y'], 
                                                self.AXIS_MAPPING['RIGHT_STICK_X'], self.AXIS_MAPPING['RIGHT_STICK_Y']]
                                    for i in range(self.__controller.get_numaxes()):
                                        if i not in used_axes:  # Show non-stick axes
                                            extra_axes.append(f"[{i}]={self.__controller.get_axis(i):.3f}")
                                    if extra_axes:
                                        print(f"   Other axes: {' '.join(extra_axes)}")
                                        
                                # Success message about right stick X
                                if abs(self.__controller.get_axis(self.AXIS_MAPPING['RIGHT_STICK_X'])) > 0.05:
                                    print(f"   ✅ Right stick X detected on axis {self.AXIS_MAPPING['RIGHT_STICK_X']}!")
                        elif self.__debug and not hasattr(self, '_debug_counter'):
                            self._debug_counter = 0
                            print(f"🎮 Controller Connected: {self.__controller.get_name()}")
                            print(f"   Total axes: {self.__controller.get_numaxes()}")
                            print(f"   Total buttons: {self.__controller.get_numbuttons()}")
                            print(f"   CORRECTED mapping: Axis {self.AXIS_MAPPING['LEFT_STICK_X']}=Left-X, {self.AXIS_MAPPING['LEFT_STICK_Y']}=Left-Y, {self.AXIS_MAPPING['RIGHT_STICK_X']}=Right-X, {self.AXIS_MAPPING['RIGHT_STICK_Y']}=Right-Y")
                            print(f"   ✅ Using axis {self.AXIS_MAPPING['RIGHT_STICK_X']} for right stick X (PlayStation controller layout)")
                        
                        # Process movement
                        self.__process_movement(left_stick_x, left_stick_y, right_stick_x, right_stick_y)
                        
                    except pygame.error:
                        print("🔴 Controller hardware disconnected!")
                        self.__controller_connected = False
                        
                        # Immediately update MQTT with disconnect status
                        if self.__mqtt_client:
                            try:
                                self.__update_mqtt_state()
                                if self.__debug:
                                    print("📡 MQTT updated after pygame error disconnect")
                            except Exception as e:
                                if self.__debug:
                                    print(f"Error updating MQTT after pygame error: {e}")
                        
                        # Don't return here - let the next iteration handle it in waiting mode
                        continue

                # Check robot buttons
                self.__check_robot_buttons()

                # Update LCD screen periodically
                if self.__screen and time.time() - self.__screen_last_update >= self.__screen_update_interval:
                    try:
                        # Update battery level from MQTT status before refreshing screen
                        if self.__mqtt_client:
                            robot_state = self.__mqtt_client.get_robot_state()
                            current_battery = robot_state.get('battery_level', 0) or 0
                            if current_battery > 0:
                                self.__screen.update_battery(current_battery)
                        
                        # Pass controller status from main controller to screen
                        self.__screen.refresh_and_update_display(self.__controller_connected)
                        self.__screen_last_update = time.time()
                    except Exception as e:
                        if self.__debug:
                            print(f"Screen update error: {e}")
                
                # Update MQTT state periodically
                if self.__mqtt_client and time.time() - self.__mqtt_last_update >= self.__mqtt_update_interval:
                    try:
                        self.__update_mqtt_state()
                        self.__mqtt_last_update = time.time()
                    except Exception as e:
                        if self.__debug:
                            print(f"MQTT update error: {e}")
                
                # Control loop frequency (50Hz)
                clock.tick(50)
                
        except KeyboardInterrupt:
            print("Control loop interrupted by user")
        except Exception as e:
            print(f"Error in control loop: {e}")
        finally:
            # Stop robot movement
            if self.__controller_connected:
                self.__robot.rider_move_x(0)
                self.__robot.rider_turn(0)
            self.__running = False
            
        return self.STATE_OK
    
    def _enter_controller_waiting_mode(self):
        """Enter waiting mode for controller connection"""
        print("🔴 Controller disconnected - waiting for reconnection...")
        print("   Move any stick or press any button to reconnect")
        print("   Press robot A button (Quit) or Ctrl+C to exit")
        
        # Immediately update MQTT with disconnected status
        if self.__mqtt_client:
            try:
                self.__update_mqtt_state()
                if self.__debug:
                    print("📡 MQTT updated with controller disconnect status")
            except Exception as e:
                if self.__debug:
                    print(f"Error updating MQTT during disconnect: {e}")
        
        # Wait for controller to reconnect indefinitely
        wait_start_time = time.time()
        wait_check_interval = 1.0  # Check every second while waiting
        last_wait_check = time.time()
        last_mqtt_update = time.time()
        
        while not self.__controller_connected and self.__running:
            wait_current_time = time.time()
            
            # Check robot buttons even while waiting for controller
            self.__check_robot_buttons()
            
            # If robot button A was pressed (quit), exit the waiting loop
            if not self.__running:
                print("🛑 Quit button pressed during controller wait - exiting...")
                break
            
            # Check for reconnection every second
            if wait_current_time - last_wait_check >= wait_check_interval:
                self.__check_controller_activity()
                last_wait_check = wait_current_time
                
                # Show waiting message periodically (every 30 seconds)
                wait_duration = wait_current_time - wait_start_time
                if int(wait_duration) % 30 == 0 and int(wait_duration) > 0:
                    print(f"⏰ Still waiting for controller... ({int(wait_duration)}s elapsed)")
                    
                # Update screen status
                if self.__screen:
                    try:
                        # Update battery level from MQTT even while waiting
                        if self.__mqtt_client:
                            robot_state = self.__mqtt_client.get_robot_state()
                            current_battery = robot_state.get('battery_level', 0) or 0
                            if current_battery > 0:
                                self.__screen.update_battery(current_battery)
                        
                        # Pass disconnected status to screen during waiting
                        self.__screen.refresh_and_update_display(False)
                    except Exception as e:
                        if self.__debug:
                            print(f"Screen update error while waiting: {e}")
            
            # Continue MQTT updates even while waiting for controller
            if self.__mqtt_client and wait_current_time - last_mqtt_update >= self.__mqtt_update_interval:
                try:
                    self.__update_mqtt_state()
                    last_mqtt_update = wait_current_time
                    if self.__debug:
                        print("📡 MQTT state updated during controller wait (disconnected)")
                except Exception as e:
                    if self.__debug:
                        print(f"Error updating MQTT during wait: {e}")
            
            # Sleep briefly to prevent excessive CPU usage
            time.sleep(0.1)
        
        # If we get here, controller was reconnected or user stopped
        if self.__controller_connected:
            print("✅ Controller reconnected!")
            if self.__screen:
                # Update screen with reconnected controller status
                self.__screen.set_external_controller_status(True)
            
            # Immediately update MQTT with reconnected status
            if self.__mqtt_client:
                try:
                    self.__update_mqtt_state()
                    if self.__debug:
                        print("📡 MQTT updated with controller reconnect status")
                except Exception as e:
                    if self.__debug:
                        print(f"Error updating MQTT during reconnect: {e}")
            
            # Reset last activity time
            self.__last_controller_activity = time.time()
    
    def stop(self):
        """Stop the control loop"""
        self.__running = False
        if self.__controller_connected:
            self.__robot.rider_move_x(0)
            self.__robot.rider_turn(0)
        print("Controller stopped")
    
    def cleanup(self):
        """Clean up resources"""
        self.stop()
        
        # Clean up camera first
        if self.__video:
            try:
                self.__video.cleanup()
            except Exception as e:
                print(f"⚠️  Error cleaning up camera: {e}")
        
        # Clean up LCD screen
        if self.__screen:
            try:
                self.__screen.cleanup()
            except Exception as e:
                print(f"⚠️  Error turning off LCD screen: {e}")
        
        # Clean up MQTT
        if self.__mqtt_client:
            try:
                self.__mqtt_client.cleanup()
                print("✅ MQTT communication stopped")
            except Exception as e:
                print(f"⚠️  Error cleaning up MQTT: {e}")
        
        if self.__controller_connected:
            self.__controller.quit()
        pygame.quit()

    def print_button_mapping(self):
        """Print current button mapping for reference"""
        print("\n" + "="*60)
        print("CURRENT BUTTON MAPPING")
        print("="*60)
        for action, button_id in self.BUTTON_MAPPING.items():
            print(f"  {action:<15}: Button {button_id}")
        print("\nAxis Mapping:")
        for axis, axis_id in self.AXIS_MAPPING.items():
            invert_note = " (inverted)" if axis == 'RIGHT_STICK_X' else ""
            print(f"  {axis:<15}: Axis {axis_id}{invert_note}")
        print("="*60)

    def __quick_battery_check(self):
        """Quick battery check for button press - now via MQTT"""
        if self.__mqtt_client:
            robot_state = self.__mqtt_client.get_robot_state()
            battery_level = robot_state.get('battery_level', 0)  # Battery percentage (0-100%)
            if battery_level and battery_level > 0:
                print(f"📱 Battery Level: {battery_level}%")
            else:
                print("❌ Battery level not available via MQTT")
        else:
            print("❌ MQTT not available for battery check")

    def get_battery_level(self):
        """Get current battery level from MQTT state (returns percentage 0-100%)"""
        if self.__mqtt_client:
            robot_state = self.__mqtt_client.get_robot_state()
            return robot_state.get('battery_level', 0) or 0  # Battery percentage (0-100%)
        return 0  # Return 0% if MQTT not available


# Example usage
if __name__ == "__main__":
    debug_mode = False
    if len(sys.argv) > 1 and sys.argv[1] == "--debug":
        debug_mode = True
    
    print("🤖 Initializing XGO-RIDER robot...")
    try:
        robot = XGO(port='/dev/ttyS0', version="xgorider")
        print("✅ Robot connected successfully!")
        
        # Read and display firmware and library versions
        try:
            firmware_version = robot.rider_read_firmware()
            print(f"📋 Firmware Version: {firmware_version}")
        except AttributeError:
            # Fallback to standard method if rider-specific method doesn't exist
            try:
                firmware_version = robot.read_firmware()
                print(f"📋 Firmware Version: {firmware_version}")
            except Exception as e:
                print(f"⚠️  Could not read firmware version: {e}")
        except Exception as e:
            print(f"⚠️  Could not read firmware version: {e}")
        
        try:
            lib_version = robot.read_lib_version()
            print(f"📚 Library Version: {lib_version}")
        except Exception as e:
            print(f"⚠️  Could not read library version: {e}")
            
    except Exception as e:
        print(f"❌ Failed to connect to robot: {e}")
        print("   • Check robot is powered on")
        print("   • Check cable connection")
        print("   • Try power cycling the robot")
        sys.exit(1)
    
    print("🎮 Setting up Bluetooth controller...")
    controller = BluetoothController_Rider(robot, controller_id=0, debug=debug_mode)
    
    # Show current button mapping if in debug mode
    if debug_mode:
        controller.print_button_mapping()
    
    # Always start the control loop, regardless of initial controller status
    if controller.is_connected():
        print("🎮 Controller ready")
    else:
        print("🎮 Waiting for controller connection...")
    
    try:
        print("\n🚀 Starting control session...")
        result = controller.start_control_loop()
        if result == controller.STATE_DISCONNECT:
            print("\n📱 Controller disconnected during operation")
        elif result == controller.STATE_OK:
            print("\n✅ Control session ended normally")
    except KeyboardInterrupt:
        print("\n🛑 Program interrupted by user")
    finally:
        print("\n🧹 Cleaning up...")
        controller.cleanup()
        robot.rider_reset()
        print("✅ Cleanup complete!") 