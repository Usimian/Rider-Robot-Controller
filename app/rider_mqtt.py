# coding=utf-8

# Rider Robot MQTT Communication Module
# Handles bidirectional MQTT communication for remote control and monitoring
# Enhanced with robust disconnect handling and safety features
# Marc Wester

import json
import time
import threading
import os
import subprocess
import psutil
import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
from typing import Optional, Callable, Dict, Any
from config import MQTT_BROKER_HOST, MQTT_BROKER_PORT

class RiderMQTT:
    def __init__(self, robot=None, broker_host=MQTT_BROKER_HOST, broker_port=MQTT_BROKER_PORT, debug=False):
        self.__debug = debug
        self.__robot = robot
        self.__broker_host = broker_host
        self.__broker_port = broker_port
        self.__client_id = f"rider_robot_{int(time.time())}"
        
        # MQTT client
        self.__client = None
        self.__connected = False
        self.__running = False
        
        # Connection monitoring
        self.__connection_timeout = 7.0   # 7 seconds timeout for client inactivity (fallback if disconnect msg lost)
        self.__last_client_activity = time.time()
        self.__client_heartbeat_topic = 'rider/client/heartbeat'
        self.__inactive_client_safety_triggered = False
        
        # Safety shutdown tracking
        self.__safety_shutdown_in_progress = False
        self.__safety_commands_timeout = 3.0  # Wait 3 seconds for safety commands
        
        # Message tracking for corruption prevention
        self.__last_movement_command = {'x': 0, 'y': 0, 'timestamp': 0}
        self.__movement_command_timeout = 2.0  # Stop movement if no commands for 2 seconds
        
        # Publishing intervals (seconds)
        self.__status_interval = 2.0  # Status updates every 2 seconds (includes battery)
        self.__imu_interval = 0.5     # IMU data every 500ms
        
        # Last publish times
        self.__last_status_publish = 0
        self.__last_imu_publish = 0
        
        # Current robot state
        self.__robot_state = {
            'battery_level': None,  # Battery percentage (0-100%) - Will be read from hardware on first read
            'speed_scale': 1.0,
            'roll_balance_enabled': False,
            'performance_mode_enabled': False,
            'camera_enabled': False,
            'controller_connected': False,
            'roll': 0.0,
            'pitch': 0.0,
            'yaw': 0.0,
            'height': 85,
            'connection_status': 'disconnected',
            'cpu_percent': 0.0,
            'cpu_temp': 0.0,
            'client_connected': False,
            'last_client_seen': 0
        }
        
        # Battery reading state
        self.__battery_read_failures = 0
        self.__max_battery_failures = 3  # Allow 3 failures before using last known good value
        self.__last_known_battery = 50  # Reasonable default until first successful read
        
        # Command callbacks
        self.__command_callbacks = {}
        
        # Topic structure
        self.__topics = {
            'status': 'rider/status',
            'imu': 'rider/status/imu',
            'camera': 'rider/status/camera',
            'connection': 'rider/status/connection',
            'control_movement': 'rider/control/movement',
            'control_settings': 'rider/control/settings',
            'control_camera': 'rider/control/camera',
            'control_system': 'rider/control/system',
            'client_heartbeat': 'rider/client/heartbeat',
            'client_disconnect': 'rider/client/disconnect',
            'server_status': 'rider/server/status',
            'image_capture_request': 'rider/control/image_capture',
            'image_capture_response': 'rider/response/image_capture',
            'movement_response': 'rider/response/movement',
            'voice_control': 'rider/voice/control',
            'voice_status': 'rider/voice/status'
        }
        
        # Publishing thread
        self.__publish_thread = None
        
        # Connection monitoring thread
        self.__monitor_thread = None
        
        if self.__debug:
            print(f"RiderMQTT initialized - Broker: {broker_host}:{broker_port}")
            print(f"🛡️ Enhanced with robust disconnect handling and safety features")
    
    def set_command_callback(self, command_type: str, callback: Callable):
        """Set callback function for specific command types"""
        self.__command_callbacks[command_type] = callback
        if self.__debug:
            print(f"Command callback set for: {command_type}")
    
    def connect(self) -> bool:
        """Connect to MQTT broker"""
        try:
            self.__client = mqtt.Client(
                client_id=self.__client_id,
                callback_api_version=CallbackAPIVersion.VERSION2,
                protocol=mqtt.MQTTv5
            )
            self.__client.on_connect = self.__on_connect
            self.__client.on_disconnect = self.__on_disconnect
            self.__client.on_message = self.__on_message
            
            if self.__debug:
                print(f"Connecting to MQTT broker at {self.__broker_host}:{self.__broker_port}")
            
            self.__client.connect(self.__broker_host, self.__broker_port, 60)
            self.__client.loop_start()
            
            # Wait for connection
            timeout = 10
            start_time = time.time()
            while not self.__connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)
            
            if self.__connected:
                self.__running = True
                self.__start_publishing_thread()
                self.__start_connection_monitor()
                if self.__debug:
                    print("✅ MQTT connected successfully with enhanced robustness")
                return True
            else:
                if self.__debug:
                    print("❌ MQTT connection timeout")
                return False
                
        except Exception as e:
            if self.__debug:
                print(f"❌ MQTT connection failed: {e}")
            return False
    
    def graceful_disconnect(self):
        """Gracefully disconnect with safety shutdown commands"""
        if self.__debug:
            print("📡 Graceful MQTT disconnect initiated...")
        
        self.__safety_shutdown_in_progress = True
        
        try:
            # Send safety shutdown commands
            self.__send_safety_shutdown_commands()
            
            # Wait briefly for message delivery
            time.sleep(0.5)
            
            # Properly disconnect
            self.disconnect()
            
            if self.__debug:
                print("✅ Graceful MQTT disconnect completed")
        except Exception as e:
            if self.__debug:
                print(f"⚠️ Error during graceful disconnect: {e}")
            # Fallback to force disconnect
            self.disconnect()
    
    def __send_safety_shutdown_commands(self):
        """Send safety shutdown commands to ensure robot safety"""
        if not self.__robot or not self.__connected:
            return
            
        try:
            if self.__debug:
                print("🛡️ Sending safety shutdown commands...")
            
            # Emergency stop command
            self.__robot.rider_move_x(0)
            self.__robot.rider_turn(0)
            try:
                self.__robot.rider_move_y(0)
            except:
                pass
            
            # Publish emergency stop event
            if self.__client and self.__connected:
                emergency_data = {
                    'timestamp': time.time(),
                    'source': 'disconnect_safety',
                    'reason': 'graceful_disconnect'
                }
                self.publish_event('emergency_stop', emergency_data)
                
                # Update robot state to stopped
                self.__robot_state['connection_status'] = 'disconnecting'
                self.__publish_status()
            
            if self.__debug:
                print("[CLEANUP] Emergency stop sent during disconnect")
                print("[CLEANUP] Movement stop sent during disconnect")
        except Exception as e:
            if self.__debug:
                print(f"⚠️ Error sending safety shutdown commands: {e}")
    
    def disconnect(self):
        """Disconnect from MQTT broker"""
        self.__running = False
        
        # Stop monitoring thread
        if self.__monitor_thread and self.__monitor_thread.is_alive():
            self.__monitor_thread.join(timeout=2)
        
        # Stop publishing thread
        if self.__publish_thread and self.__publish_thread.is_alive():
            self.__publish_thread.join(timeout=2)
        
        if self.__client:
            self.__client.loop_stop()
            self.__client.disconnect()
            self.__connected = False
        
        if self.__debug:
            print("MQTT disconnected")
    
    def __start_connection_monitor(self):
        """Start connection monitoring thread"""
        self.__monitor_thread = threading.Thread(target=self.__connection_monitoring_loop, daemon=True)
        self.__monitor_thread.start()
        if self.__debug:
            print("🔍 MQTT connection monitoring started")
    
    def __connection_monitoring_loop(self):
        """Monitor client connections and trigger safety actions if needed"""
        while self.__running and self.__connected:
            try:
                current_time = time.time()
                
                # Check for client inactivity
                time_since_activity = current_time - self.__last_client_activity
                
                if time_since_activity > self.__connection_timeout:
                    if not self.__inactive_client_safety_triggered:
                        if self.__debug:
                            print(f"⚠️ Client inactive for {time_since_activity:.1f}s - triggering safety stop")
                        
                        self.__trigger_safety_stop_for_inactive_client()
                        self.__inactive_client_safety_triggered = True
                        
                        # Update robot state
                        self.__robot_state['client_connected'] = False
                        self.__robot_state['connection_status'] = 'client_timeout'
                else:
                    # Reset safety trigger if client becomes active again
                    if self.__inactive_client_safety_triggered:
                        if self.__debug:
                            print("✅ Client activity resumed - resetting safety state")
                        self.__inactive_client_safety_triggered = False
                        self.__robot_state['client_connected'] = True
                        self.__robot_state['connection_status'] = 'connected'
                
                # Check for stale movement commands
                movement_age = current_time - self.__last_movement_command['timestamp']
                if movement_age > self.__movement_command_timeout:
                    if (self.__last_movement_command['x'] != 0 or 
                        self.__last_movement_command['y'] != 0):
                        if self.__debug:
                            print(f"⚠️ Movement command timeout ({movement_age:.1f}s) - stopping robot")
                        self.__stop_robot_movement()
                        self.__last_movement_command = {'x': 0, 'y': 0, 'timestamp': current_time}
                
                time.sleep(1.0)  # Check every second
                
            except Exception as e:
                if self.__debug:
                    print(f"Error in connection monitoring: {e}")
                time.sleep(5.0)
    
    def __trigger_safety_stop_for_inactive_client(self):
        """Trigger safety stop when client becomes inactive"""
        if not self.__robot:
            return
            
        try:
            # Stop all movement immediately
            self.__robot.rider_move_x(0)
            self.__robot.rider_turn(0)
            try:
                self.__robot.rider_move_y(0)
            except:
                pass
            
            # Publish safety event
            if self.__client and self.__connected:
                safety_data = {
                    'timestamp': time.time(),
                    'source': 'connection_monitor',
                    'reason': 'client_timeout',
                    'timeout_duration': time.time() - self.__last_client_activity
                }
                self.publish_event('safety_stop', safety_data)
            
        except Exception as e:
            if self.__debug:
                print(f"Error during safety stop: {e}")
    
    def __stop_robot_movement(self):
        """Stop robot movement (internal method)"""
        if not self.__robot:
            return
            
        try:
            self.__robot.rider_move_x(0)
            self.__robot.rider_turn(0)
            try:
                self.__robot.rider_move_y(0)
            except:
                pass
        except Exception as e:
            if self.__debug:
                print(f"Error stopping robot movement: {e}")
    
    def __on_connect(self, client, userdata, flags, reason_code, properties):
        """Callback for MQTT connection"""
        if reason_code == 0:
            self.__connected = True
            if self.__debug:
                print("MQTT 5.0 broker connected")
            
            # Subscribe to control topics
            control_topics = [
                self.__topics['control_movement'],
                self.__topics['control_settings'],
                self.__topics['control_camera'],
                self.__topics['control_system'],
                self.__topics['client_heartbeat'],
                self.__topics['client_disconnect'],
                self.__topics['image_capture_request'],
                self.__topics['voice_control']
            ]
            
            for topic in control_topics:
                client.subscribe(topic)
                if self.__debug:
                    print(f"Subscribed to: {topic}")
            
            # Set startup speaker volume to a known audible level
            import subprocess as _sp
            _sp.run(['amixer', '-c', 'wm8960soundcard', 'set', 'Speaker', '120'],
                    check=False, stderr=_sp.DEVNULL)

            # Reset client activity tracking — client_connected stays False until
            # a real PC client message arrives (heartbeat, command, etc.)
            self.__last_client_activity = 0  # Forces timeout to fire quickly
            self.__inactive_client_safety_triggered = False
            self.__robot_state['client_connected'] = False
            self.__robot_state['connection_status'] = 'waiting_for_client'
        else:
            if self.__debug:
                print(f"MQTT 5.0 connection failed with reason code: {reason_code}")
    
    def __on_disconnect(self, client, userdata, flags, reason_code, properties):
        """Callback for MQTT disconnection"""
        self.__connected = False
        if self.__debug:
            print(f"MQTT 5.0 broker disconnected with reason code: {reason_code}")
        
        # Trigger safety stop on unexpected disconnection
        if not self.__safety_shutdown_in_progress:
            if self.__debug:
                print("🛑 Unexpected MQTT disconnection - triggering safety stop")
            self.__stop_robot_movement()
    
    def __on_message(self, client, userdata, msg):
        """Handle incoming MQTT messages with enhanced error handling"""
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode())
            
            # Update client activity time for any message
            self.__last_client_activity = time.time()
            self.__robot_state['last_client_seen'] = self.__last_client_activity
            first_message = not self.__robot_state.get('client_connected', False)
            if first_message:
                self.__robot_state['client_connected'] = True
                self.__robot_state['connection_status'] = 'connected'
                self.__inactive_client_safety_triggered = False
                # Publish full state immediately so client doesn't wait for next timer tick
                threading.Thread(target=self.__publish_all_immediately, daemon=True).start()
            
            if self.__debug:
                print(f"MQTT message received - Topic: {topic}, Payload: {payload}")
            
            # Route message to appropriate handler with error recovery
            try:
                if topic == self.__topics['control_movement']:
                    self.__handle_movement_command(payload)
                elif topic == self.__topics['control_settings']:
                    self.__handle_settings_command(payload)
                elif topic == self.__topics['control_camera']:
                    self.__handle_camera_command(payload)
                elif topic == self.__topics['control_system']:
                    self.__handle_system_command(payload)
                elif topic == self.__topics['client_heartbeat']:
                    self.__handle_client_heartbeat(payload)
                elif topic == self.__topics['client_disconnect']:
                    self.__handle_client_disconnect(payload)
                elif topic == self.__topics['image_capture_request']:
                    self.__handle_image_capture_request(payload)
                elif topic == self.__topics['voice_control']:
                    self.__handle_voice_control(payload)
            except Exception as handler_error:
                if self.__debug:
                    print(f"⚠️ Error in message handler for {topic}: {handler_error}")
                # Continue processing other messages even if one fails
                
        except json.JSONDecodeError as e:
            if self.__debug:
                print(f"⚠️ Invalid JSON in MQTT message: {e}")
                print(f"   Raw payload: {msg.payload}")
        except Exception as e:
            if self.__debug:
                print(f"⚠️ Error processing MQTT message: {e}")
    
    def __handle_client_heartbeat(self, payload: Dict[str, Any]):
        """Handle client heartbeat messages"""
        if self.__debug:
            print("💓 Client heartbeat received")
        
        # Update activity time (already done in __on_message)
        # Additional heartbeat-specific processing can be added here
        pass
    
    def __handle_client_disconnect(self, payload: Dict[str, Any]):
        """Handle explicit client disconnect messages"""
        source = payload.get('source', 'unknown')
        reason = payload.get('reason', 'client_disconnect')
        
        if self.__debug:
            print(f"📤 Client disconnect message received - Source: {source}, Reason: {reason}")
        
        # Trigger immediate safety stop
        self.__stop_robot_movement()
        
        # Update connection status - reset activity timer so is_client_connected() returns False immediately
        self.__last_client_activity = 0
        self.__robot_state['client_connected'] = False
        self.__robot_state['connection_status'] = 'client_disconnected'
        
        # Publish disconnect acknowledgment
        disconnect_ack = {
            'timestamp': time.time(),
            'acknowledged': True,
            'source': source,
            'reason': reason
        }
        self.publish_event('client_disconnect_ack', disconnect_ack)
    
    def __handle_movement_command(self, payload: Dict[str, Any]):
        """Handle movement control commands with enhanced safety tracking
        
        Supports two command formats:
        1. Legacy joystick control: {"x": 0-100, "y": 0-100}
        2. New movement commands: {"action": "move/turn/stop", "distance": mm, "angle": degrees}
        """
        timestamp = payload.get('timestamp', time.time())
        source = payload.get('source', 'client')
        
        # Check if this is a new-style movement command
        action = payload.get('action')
        
        if action:
            # New movement command format
            self.__handle_action_command(payload, timestamp, source)
        else:
            # Legacy joystick control format
            self.__handle_joystick_command(payload, timestamp, source)
    
    def __handle_action_command(self, payload: Dict[str, Any], timestamp: float, source: str):
        """Handle new action-based movement commands (move, turn, stop)"""
        action = payload.get('action')
        
        if self.__debug:
            print(f"🎯 Action command: {action}, timestamp={timestamp}, source={source}")
        
        if action == 'stop':
            # Emergency stop command
            self.__stop_robot_movement()
            if self.__debug:
                print("   🛑 STOP command executed")
            
            # Update movement tracking
            self.__last_movement_command = {
                'x': 0,
                'y': 0,
                'timestamp': timestamp,
                'source': source
            }
            
            # Publish completion status
            self.__publish_movement_completion('stop', success=True)
            
        elif action == 'move':
            # Linear movement command
            distance_mm = payload.get('distance', 0)
            
            if self.__debug:
                direction = "forward" if distance_mm > 0 else "backward"
                print(f"   ➡ Moving {direction} {abs(distance_mm)}mm")
            
            # Execute movement using threaded handler to avoid blocking
            movement_thread = threading.Thread(
                target=self.__execute_linear_movement,
                args=(distance_mm, timestamp, source),
                daemon=True
            )
            movement_thread.start()
            
        elif action == 'turn':
            # Rotation command
            angle_deg = payload.get('angle', 0)
            
            if self.__debug:
                direction = "right" if angle_deg > 0 else "left"
                print(f"   🔄 Turning {direction} {abs(angle_deg)}°")
            
            # Execute turn using threaded handler to avoid blocking
            turn_thread = threading.Thread(
                target=self.__execute_turn_movement,
                args=(angle_deg, timestamp, source),
                daemon=True
            )
            turn_thread.start()
        
        elif action == 'speak':
            # Forward TTS to rider_voice.py via MQTT so it can pause recording first
            text = payload.get('text', '')
            if text:
                if self.__debug:
                    print(f"   🔊 TTS: {text}")
                self.__publish_json('rider/voice/speak', {'text': text})
        
        else:
            if self.__debug:
                print(f"   ⚠️ Unknown action: {action}")
    
    def __execute_linear_movement(self, distance_mm: int, timestamp: float, source: str):
        """Execute linear movement and stop when complete"""
        if not self.__robot:
            return
        
        try:
            # Calculate movement parameters
            # Typical speed for rider: ~100mm/s at speed 0.3
            # Adjust these values based on testing
            base_speed = 0.3  # Base forward speed
            speed_mm_per_sec = 100.0  # Approximate speed in mm/s at base_speed
            
            # Calculate speed and duration
            if distance_mm > 0:
                # Forward movement
                speed = base_speed * self.__robot_state['speed_scale']
                duration = abs(distance_mm) / speed_mm_per_sec
            else:
                # Backward movement (may need adjustment)
                speed = -base_speed * self.__robot_state['speed_scale'] * 1.5  # Backward compensation
                duration = abs(distance_mm) / speed_mm_per_sec
            
            if self.__debug:
                print(f"   📐 Movement params: speed={speed:.3f}, duration={duration:.2f}s")
            
            # Start movement
            self.__robot.rider_move_x(speed)
            
            # Wait for completion
            time.sleep(duration)
            
            # Stop movement
            self.__robot.rider_move_x(0)
            
            if self.__debug:
                print(f"   ✅ Movement completed: {distance_mm}mm")
            
            # Publish completion status
            self.__publish_movement_completion('move', success=True, 
                                              distance=distance_mm, 
                                              actual_duration=duration)
            
        except Exception as e:
            if self.__debug:
                print(f"❌ Error executing linear movement: {e}")
            # Ensure robot is stopped on error
            try:
                self.__robot.rider_move_x(0)
            except:
                pass
            # Publish failure status
            self.__publish_movement_completion('move', success=False, 
                                              distance=distance_mm,
                                              error=str(e))
    
    def __execute_turn_movement(self, angle_deg: int, timestamp: float, source: str):
        """Execute turn movement and stop when complete"""
        if not self.__robot:
            return
        
        try:
            # Calculate turn parameters
            # Typical turn rate: ~30 degrees/second at turn_speed 30
            base_turn_speed = 50  # Base turn speed value
            degrees_per_sec = 30.0  # Approximate turn rate
            
            # Calculate turn speed and duration
            if angle_deg > 0:
                # Turn right (positive)
                turn_speed = base_turn_speed
            else:
                # Turn left (negative)
                turn_speed = -base_turn_speed
            
            duration = abs(angle_deg) / degrees_per_sec
            
            if self.__debug:
                print(f"   📐 Turn params: speed={turn_speed}, duration={duration:.2f}s")
            
            # Start turning
            self.__robot.rider_turn(turn_speed)
            
            # Wait for completion
            time.sleep(duration)
            
            # Stop turning
            self.__robot.rider_turn(0)
            
            if self.__debug:
                print(f"   ✅ Turn completed: {angle_deg}°")
            
            # Publish completion status
            self.__publish_movement_completion('turn', success=True,
                                              angle=angle_deg,
                                              actual_duration=duration)
            
        except Exception as e:
            if self.__debug:
                print(f"❌ Error executing turn movement: {e}")
            # Ensure robot is stopped on error
            try:
                self.__robot.rider_turn(0)
            except:
                pass
            # Publish failure status
            self.__publish_movement_completion('turn', success=False,
                                              angle=angle_deg,
                                              error=str(e))
    
    def __handle_joystick_command(self, payload: Dict[str, Any], timestamp: float, source: str):
        """Handle legacy joystick control commands"""
        x = payload.get('x', 0)  # -100 to +100 (left/right)
        y = payload.get('y', 0)  # -100 to +100 (backward/forward)
        
        # Update movement command tracking for timeout monitoring
        self.__last_movement_command = {
            'x': x,
            'y': y,
            'timestamp': timestamp,
            'source': source
        }
        
        if self.__debug:
            print(f"🎮 Joystick command: x={x}, y={y}, timestamp={timestamp}, source={source}")
        
        # Convert x,y values (-100 to +100) to robot movement commands
        if self.__robot:
            try:
                # Convert movement values to robot scale
                # X axis: left/right movement (turning)
                if x != 0:
                    # Convert -100 to +100 range to robot turn values
                    turn_value = int(x * 1.0)  # Adjust scaling as needed
                    self.__robot.rider_turn(turn_value)
                    if self.__debug:
                        direction = "right" if x > 0 else "left"
                        print(f"   ↔ Turning {direction} (value: {turn_value})")
                
                # Y axis: forward/backward movement
                if y != 0:
                    # Convert -100 to +100 range to robot speed values
                    speed_value = y / 100.0 * self.__robot_state['speed_scale']
                    self.__robot.rider_move_x(speed_value)
                    if self.__debug:
                        direction = "forward" if y > 0 else "backward"
                        print(f"   ⬆ Moving {direction} (speed: {speed_value:.2f})")
                
                # Stop movement if both are zero
                if x == 0 and y == 0:
                    self.__robot.rider_move_x(0)
                    self.__robot.rider_turn(0)
                    if self.__debug:
                        print("   ⏹ Stopping robot")
                        
            except Exception as e:
                if self.__debug:
                    print(f"❌ Error executing joystick command: {e}")
                # On movement command error, ensure robot is stopped
                try:
                    self.__stop_robot_movement()
                except:
                    pass
        
        # Trigger callback if set
        if 'movement' in self.__command_callbacks:
            self.__command_callbacks['movement'](payload)
    
    def __publish_movement_completion(self, action: str, success: bool, **kwargs):
        """Publish movement completion status"""
        if not self.__connected:
            return
        
        completion_data = {
            'timestamp': time.time(),
            'action': action,
            'success': success
        }
        
        # Add additional parameters
        completion_data.update(kwargs)
        
        # Publish to movement response topic
        self.__publish_json(self.__topics['movement_response'], completion_data)
        
        if self.__debug:
            status = "✅ Success" if success else "❌ Failed"
            print(f"   📡 Movement completion published: {action} - {status}")
    
    def __handle_settings_command(self, payload: Dict[str, Any]):
        """Handle settings control commands"""
        action = payload.get('action')
        timestamp = payload.get('timestamp', time.time())
        
        if self.__debug:
            print(f"⚙️ Settings command: {action}, timestamp={timestamp}")
        
        if self.__robot and action:
            try:
                if action == 'toggle_roll_balance':
                    self.__robot_state['roll_balance_enabled'] = not self.__robot_state['roll_balance_enabled']
                    self.__robot.rider_balance_roll(1 if self.__robot_state['roll_balance_enabled'] else 0)
                    status = "enabled" if self.__robot_state['roll_balance_enabled'] else "disabled"
                    if self.__debug:
                        print(f"   🎯 Roll balance {status}")
                
                elif action == 'toggle_performance':
                    self.__robot_state['performance_mode_enabled'] = not self.__robot_state['performance_mode_enabled']
                    self.__robot.rider_perform(1 if self.__robot_state['performance_mode_enabled'] else 0)
                    status = "enabled" if self.__robot_state['performance_mode_enabled'] else "disabled"
                    if self.__debug:
                        print(f"   🚀 Performance mode {status}")
                
                elif action == 'change_speed':
                    new_speed = payload.get('value', 1.0)
                    # Validate speed range (0.1 - 2.0)
                    new_speed = max(0.1, min(2.0, new_speed))
                    self.__robot_state['speed_scale'] = new_speed
                    if self.__debug:
                        print(f"   🏃 Speed changed to {new_speed}x")
                
                elif action == 'change_height':
                    new_height = payload.get('value', 85)
                    # Validate height range (60-120mm)
                    new_height = max(60, min(120, new_height))
                    self.__robot_state['height'] = new_height
                    # Call XGO method to change height (non-blocking, instant)
                    self.__robot.rider_height(new_height)
                    if self.__debug:
                        print(f"   📏 Height changed to {new_height}mm")
                
                elif action == 'change_body_tilt':
                    new_tilt = payload.get('value', 0)
                    # Validate tilt range (-30 to +30 degrees)
                    new_tilt = max(-30, min(30, new_tilt))
                    
                    # Only apply tilt if roll balance is NOT enabled
                    if not self.__robot_state['roll_balance_enabled']:
                        # Call XGO method to change tilt (non-blocking, instant)
                        self.__robot.rider_roll(new_tilt)
                        if self.__debug:
                            print(f"   🎯 Body tilt changed to {new_tilt}°")
                    else:
                        if self.__debug:
                            print(f"   ⚠️  Body tilt ignored - roll balance is enabled")
                
                elif action == 'set_volume':
                    # value is 0-100; map to WM8960 Speaker range 80-127
                    # (below 80 is near-silent on WM8960, so map full slider to audible range)
                    pct = max(0, min(100, int(payload.get('value', 80))))
                    hw_val = 80 + int(pct * 47 / 100)
                    import subprocess
                    subprocess.run(
                        ['amixer', '-c', 'wm8960soundcard', 'set', 'Speaker', str(hw_val)],
                        check=False, stderr=subprocess.DEVNULL
                    )
                    if self.__debug:
                        print(f'   🔊 Volume set to {pct}% (hw {hw_val}/127)')

                # For height/tilt changes, don't publish status immediately to avoid delays
                # The periodic status updates will reflect the changes within 2 seconds
                # Only publish for mode changes that need immediate UI feedback
                if action not in ['change_height', 'change_body_tilt', 'set_volume']:
                    # Publish updated status after settings change
                    self.__publish_status()
                
            except Exception as e:
                if self.__debug:
                    print(f"❌ Error executing settings command: {e}")
        
        # Trigger callback if set
        if 'settings' in self.__command_callbacks:
            self.__command_callbacks['settings'](payload)
    
    def __handle_camera_command(self, payload: Dict[str, Any]):
        """Handle camera control commands"""
        action = payload.get('action', 'toggle_camera')
        timestamp = payload.get('timestamp', time.time())
        
        if self.__debug:
            print(f"📷 Camera command: {action}, timestamp={timestamp}")
        
        if action == 'toggle_camera':
            self.__robot_state['camera_enabled'] = not self.__robot_state['camera_enabled']
            status = "enabled" if self.__robot_state['camera_enabled'] else "disabled"
            if self.__debug:
                print(f"   📹 Camera {status}")
            
            # Publish updated status after camera change
            self.__publish_status()
        
        # Trigger callback if set
        if 'camera' in self.__command_callbacks:
            self.__command_callbacks['camera'](payload)
    

    def __handle_voice_control(self, payload: Dict[str, Any]):
        """Handle voice enable/disable from PC client."""
        enabled = payload.get('enabled', True)
        if self.__debug:
            print(f"Voice control: {'enable' if enabled else 'disable'}")
        if 'voice_control' in self.__command_callbacks:
            self.__command_callbacks['voice_control'](enabled)

    def publish_voice_enabled(self, enabled: bool):
        """Publish voice enabled/disabled state to PC client."""
        self.__publish_json(self.__topics['voice_status'], {'enabled': enabled})

    def __handle_image_capture_request(self, payload: Dict[str, Any]):
        """Handle image capture requests"""
        request_id = payload.get('request_id', f"img_{int(time.time())}")
        resolution = payload.get('resolution', 'high')  # 'high' or 'low'
        timestamp = payload.get('timestamp', time.time())
        client_id = payload.get('client_id', 'unknown')
        
        if self.__debug:
            print(f"📸 Image capture request: ID={request_id}, resolution={resolution}, client={client_id}")
        
        try:
            # Trigger callback to controller to actually capture the image
            if 'image_capture' in self.__command_callbacks:
                capture_result = self.__command_callbacks['image_capture'](payload)
                
                if capture_result and capture_result.get('success'):
                    # Send successful response
                    response_payload = {
                        'request_id': request_id,
                        'timestamp': time.time(),
                        'success': True,
                        'image_data': capture_result.get('image_data'),
                        'resolution': resolution,
                        'client_id': client_id,
                        'image_size': capture_result.get('image_size', 'unknown'),
                        'capture_timestamp': capture_result.get('capture_timestamp', timestamp)
                    }
                    
                    if self.__debug:
                        img_size_info = capture_result.get('image_size', 'unknown')
                        print(f"✅ Image capture successful: {img_size_info}")
                else:
                    # Send failure response
                    response_payload = {
                        'request_id': request_id,
                        'timestamp': time.time(),
                        'success': False,
                        'error': capture_result.get('error', 'Unknown capture error') if capture_result else 'Camera not available',
                        'client_id': client_id
                    }
                    
                    if self.__debug:
                        error_msg = response_payload['error']
                        print(f"❌ Image capture failed: {error_msg}")
            else:
                # No callback set - camera not available
                response_payload = {
                    'request_id': request_id,
                    'timestamp': time.time(),
                    'success': False,
                    'error': 'Image capture not available - no camera handler',
                    'client_id': client_id
                }
                
                if self.__debug:
                    print("❌ Image capture failed: No camera handler available")
            
            # Publish response
            self.__publish_json(self.__topics['image_capture_response'], response_payload)
            
        except Exception as e:
            if self.__debug:
                print(f"❌ Error handling image capture request: {e}")
            
            # Send error response
            error_response = {
                'request_id': request_id,
                'timestamp': time.time(),
                'success': False,
                'error': f'Server error: {str(e)}',
                'client_id': client_id
            }
            
            try:
                self.__publish_json(self.__topics['image_capture_response'], error_response)
            except Exception as publish_error:
                if self.__debug:
                    print(f"❌ Failed to publish error response: {publish_error}")
    
    def __handle_system_command(self, payload: Dict[str, Any]):
        """Handle system control commands"""
        action = payload.get('action')
        timestamp = payload.get('timestamp', time.time())
        
        if self.__debug:
            print(f"🛑 System command: {action}, timestamp={timestamp}")
        
        if self.__robot and action == 'emergency_stop':
            try:
                if self.__debug:
                    print("   🚨 EMERGENCY STOP - Stopping all movement")
                
                # Immediately stop all movement
                self.__robot.rider_move_x(0)
                self.__robot.rider_turn(0)
                try:
                    self.__robot.rider_move_y(0)
                except:
                    pass
                
                # Reset odometry for safety
                self.__robot.rider_reset_odom()
                
                # Publish updated status after emergency stop
                self.__publish_status()
                
            except Exception as e:
                if self.__debug:
                    print(f"❌ Error executing emergency stop: {e}")
        
        elif self.__robot and action == 'reset_robot':
            try:
                if self.__debug:
                    print("   🔄 RESET ROBOT - Resetting to default state")
                
                # Reset robot to default state
                self.__robot.rider_reset()
                
                # Update robot state to default values
                self.__robot_state['speed_scale'] = 1.0
                self.__robot_state['roll_balance_enabled'] = False
                self.__robot_state['performance_mode_enabled'] = False
                self.__robot_state['height'] = 85
                
                # Publish updated status after reset
                self.__publish_status()
                
                if self.__debug:
                    print("   ✅ Robot reset completed")
                
            except Exception as e:
                if self.__debug:
                    print(f"❌ Error executing robot reset: {e}")
        
        elif action == 'reboot_pi':
            try:
                if self.__debug:
                    print("   🔄 REBOOT PI - Initiating system reboot")
                
                # Send safety shutdown commands first
                if self.__robot:
                    self.__robot.rider_move_x(0)
                    self.__robot.rider_turn(0)
                    try:
                        self.__robot.rider_move_y(0)
                    except:
                        pass
                
                # Publish status before reboot
                reboot_status = {
                    'timestamp': time.time(),
                    'status': 'rebooting',
                    'message': 'System reboot initiated via MQTT'
                }
                self.__publish_json(self.__topics['server_status'], reboot_status)
                
                # Wait briefly for message delivery
                time.sleep(0.5)
                
                # Execute reboot command
                import subprocess
                if self.__debug:
                    print("   🔄 Executing system reboot...")
                subprocess.run(['sudo', 'reboot'], check=True)
                
            except subprocess.CalledProcessError as e:
                if self.__debug:
                    print(f"❌ Failed to execute reboot command: {e}")
            except Exception as e:
                if self.__debug:
                    print(f"❌ Error executing reboot: {e}")
        
        elif action == 'poweroff_pi':
            try:
                if self.__debug:
                    print("   🔌 POWEROFF PI - Initiating system shutdown")
                
                # Send safety shutdown commands first
                if self.__robot:
                    self.__robot.rider_move_x(0)
                    self.__robot.rider_turn(0)
                    try:
                        self.__robot.rider_move_y(0)
                    except:
                        pass
                
                # Publish status before shutdown
                shutdown_status = {
                    'timestamp': time.time(),
                    'status': 'shutting_down',
                    'message': 'System shutdown initiated via MQTT'
                }
                self.__publish_json(self.__topics['server_status'], shutdown_status)
                
                # Wait briefly for message delivery
                time.sleep(0.5)
                
                # Execute shutdown command
                import subprocess
                if self.__debug:
                    print("   🔌 Executing system shutdown...")
                subprocess.run(['sudo', 'shutdown', '-h', 'now'], check=True)
                
            except subprocess.CalledProcessError as e:
                if self.__debug:
                    print(f"❌ Failed to execute shutdown command: {e}")
            except Exception as e:
                if self.__debug:
                    print(f"❌ Error executing shutdown: {e}")
        
        # Trigger callback if set
        if 'system' in self.__command_callbacks:
            self.__command_callbacks['system'](payload)
    def update_robot_state(self, **kwargs):
        """Update robot state for publishing"""
        for key, value in kwargs.items():
            if key in self.__robot_state:
                self.__robot_state[key] = value
                if self.__debug and key in ['battery_level', 'speed_scale']:
                    print(f"Robot state updated - {key}: {value}")
    
    def __start_publishing_thread(self):
        """Start the publishing thread"""
        self.__publish_thread = threading.Thread(target=self.__publishing_loop, daemon=True)
        self.__publish_thread.start()
        if self.__debug:
            print("MQTT publishing thread started")
    
    def __publishing_loop(self):
        """Main publishing loop"""
        # Initialize CPU monitoring with a blocking call
        # This primes psutil for subsequent non-blocking calls
        try:
            psutil.cpu_percent(interval=0.1)
        except:
            pass
        
        while self.__running and self.__connected:
            try:
                current_time = time.time()
                
                # Sample CPU usage periodically (non-blocking after first call)
                # This keeps the CPU data fresh for status publishing
                try:
                    cpu_sample = psutil.cpu_percent(interval=None)  # Non-blocking sample
                    if cpu_sample is not None:
                        self.__robot_state['cpu_percent'] = cpu_sample
                except:
                    pass
                
                # Publish status updates
                if current_time - self.__last_status_publish >= self.__status_interval:
                    self.__publish_status()
                    self.__last_status_publish = current_time
                
                # Publish IMU data
                if current_time - self.__last_imu_publish >= self.__imu_interval:
                    self.__publish_imu_data()
                    self.__last_imu_publish = current_time
                
                time.sleep(0.1)  # Small sleep to prevent excessive CPU usage
                
            except Exception as e:
                if self.__debug:
                    print(f"Error in publishing loop: {e}")
                time.sleep(1)
    
    def __publish_status(self):
        """Publish general status information including battery"""
        if not self.__connected:
            return
        
        # Update CPU data before publishing
        self.__get_cpu_data()
        
        # Update battery data before publishing
        self.__update_battery_data()
        
        status_data = {
            'timestamp': time.time(),
            'speed_scale': self.__robot_state['speed_scale'],
            'roll_balance_enabled': self.__robot_state['roll_balance_enabled'],
            'performance_mode_enabled': self.__robot_state['performance_mode_enabled'],
            'camera_enabled': self.__robot_state['camera_enabled'],
            'controller_connected': self.__robot_state['controller_connected'],
            'height': self.__robot_state['height'],
            'connection_status': self.__robot_state['connection_status'],
            'cpu_percent': self.__robot_state['cpu_percent'],
            'cpu_temp': self.__robot_state['cpu_temp'],
            'battery_level': self.__robot_state['battery_level']  # Battery percentage (0-100%)
        }
        
        self.__publish_json(self.__topics['status'], status_data)
    
    def __publish_imu_data(self):
        """Publish IMU/odometry data"""
        if not self.__connected:
            return
        
        # Try to get real IMU data from robot if available
        real_imu_data = self.__get_real_imu_data()
        if real_imu_data:
            self.__robot_state['roll'] = real_imu_data['roll']
            self.__robot_state['pitch'] = real_imu_data['pitch']
            self.__robot_state['yaw'] = real_imu_data['yaw']
        
        imu_data = {
            'timestamp': time.time(),
            'roll': self.__robot_state['roll'],
            'pitch': self.__robot_state['pitch'],
            'yaw': self.__robot_state['yaw']
        }
        
        self.__publish_json(self.__topics['imu'], imu_data)
    
    def __get_real_imu_data(self) -> Optional[Dict[str, float]]:
        """Try to get real IMU data from robot hardware"""
        if not self.__robot:
            return None
            
        try:
            # Try to read IMU data from robot
            # Note: Specific method names may vary depending on xgo-toolkit version
            try:
                roll = self.__robot.read_roll() if hasattr(self.__robot, 'read_roll') else 0.0
                pitch = self.__robot.read_pitch() if hasattr(self.__robot, 'read_pitch') else 0.0
                yaw = self.__robot.read_yaw() if hasattr(self.__robot, 'read_yaw') else 0.0
                
                return {
                    'roll': float(roll),
                    'pitch': float(pitch),
                    'yaw': float(yaw)
                }
            except AttributeError:
                # Try alternative method names
                try:
                    imu_data = self.__robot.read_imu() if hasattr(self.__robot, 'read_imu') else None
                    if imu_data and isinstance(imu_data, (list, tuple)) and len(imu_data) >= 3:
                        return {
                            'roll': float(imu_data[0]),
                            'pitch': float(imu_data[1]),
                            'yaw': float(imu_data[2])
                        }
                except:
                    pass
                return None
        except Exception as e:
            if self.__debug:
                print(f"⚠️  MQTT: Error reading IMU data: {e}")
            return None
    
    def __update_battery_data(self):
        """Update battery data in robot state"""
        # Try to get real battery reading from robot if available
        real_battery_level = self.__get_real_battery_level()
        
        # Handle battery reading logic with improved error recovery
        if real_battery_level is not None:
            # Successfully read battery - reset failure counter
            self.__battery_read_failures = 0
            self.__last_known_battery = real_battery_level  # Store battery percentage (0-100%)
            self.__robot_state['battery_level'] = real_battery_level  # Battery percentage (0-100%)
            if self.__debug:
                print(f"✅ Battery reading successful: {real_battery_level}%")
        else:
            # Failed to read battery
            self.__battery_read_failures += 1
            
            if self.__battery_read_failures <= self.__max_battery_failures:
                # Use last known good value for a few failures
                if self.__robot_state['battery_level'] is None:
                    self.__robot_state['battery_level'] = self.__last_known_battery  # Use cached battery percentage (0-100%)
                if self.__debug:
                    print(f"⚠️  Battery read failed ({self.__battery_read_failures}/{self.__max_battery_failures}), using cached value: {self.__robot_state['battery_level']}%")
            else:
                # Too many failures, use last known good value
                self.__robot_state['battery_level'] = self.__last_known_battery  # Use fallback battery percentage (0-100%)
                if self.__debug:
                    print(f"⚠️  Battery reading consistently failing, using fallback value: {self.__robot_state['battery_level']}%")
        
        # Ensure battery level is valid
        battery_level = self.__robot_state['battery_level']
        if battery_level is None:
            battery_level = self.__last_known_battery
        
        # If both current and last known battery are None, use a safe default
        if battery_level is None:
            battery_level = 50  # Default to 50% if no battery data available
            if self.__debug:
                print("⚠️  No battery data available, using default 50%")
        
        # Clamp battery level to valid percentage range (0-100%)
        battery_level = max(0, min(100, battery_level))
        self.__robot_state['battery_level'] = battery_level  # Store final battery percentage (0-100%)
    
    def __get_real_battery_level(self) -> Optional[int]:
        """Try to get real battery level from robot hardware (returns percentage 0-100%)"""
        if not self.__robot:
            return None
            
        try:
            battery_level = None
            
            # First try the rider-specific method
            try:
                raw_battery = self.__robot.rider_read_battery()
                if raw_battery is not None:
                    battery_level = int(raw_battery)
                    if self.__debug:
                        print(f"📊 MQTT Battery reading (rider method): {battery_level}%")
            except AttributeError:
                # Fallback to standard method
                try:
                    raw_battery = self.__robot.read_battery()
                    if raw_battery is not None:
                        battery_level = int(raw_battery)
                        if self.__debug:
                            print(f"📊 MQTT Battery reading (standard method): {battery_level}%")
                except AttributeError:
                    if self.__debug:
                        print("⚠️  MQTT: Battery reading method not available")
                    return None
            
            # Validate the reading
            if battery_level is not None:
                # Check for obviously invalid readings
                if battery_level < 0:
                    if self.__debug:
                        print(f"⚠️  Invalid battery reading (negative): {battery_level}%, ignoring")
                    return None
                elif battery_level > 100:
                    if self.__debug:
                        print(f"⚠️  Invalid battery reading (>100%): {battery_level}%, clamping to 100%")
                    return 100
                else:
                    return battery_level
            else:
                return None
                
        except (ValueError, TypeError) as e:
            if self.__debug:
                print(f"⚠️  MQTT: Invalid battery data format: {e}")
            return None
        except Exception as e:
            if self.__debug:
                print(f"⚠️  MQTT: Error reading battery: {e}")
            return None
    
    def __get_cpu_data(self):
        """Read current CPU usage and temperature"""
        try:
            # cpu_percent is already sampled every 0.1s in __publishing_loop
            # Do NOT call psutil.cpu_percent() here — a second back-to-back call
            # measures a near-zero interval and returns 0 or 100 (noise).

            # Read CPU temperature from thermal zone
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                self.__robot_state['cpu_temp'] = int(f.read().strip()) / 1000.0

            if self.__debug:
                print(f"📊 CPU: {self.__robot_state['cpu_percent']:.1f}%, Temp: {self.__robot_state['cpu_temp']:.1f}°C")

        except Exception as e:
            if self.__debug:
                print(f"⚠️  MQTT: Error reading CPU data: {e}")
            self.__robot_state['cpu_temp'] = 0.0

    def __publish_all_immediately(self):
        """Publish full status and IMU immediately when a new client connects."""
        time.sleep(0.3)  # Brief pause to let client finish subscribing
        self.__get_cpu_data()
        self.__publish_status()
        self.__publish_imu_data()

    def is_client_connected(self) -> bool:
        """Return whether a PC client is currently connected.
        Uses recency of last message rather than the flag to avoid race conditions."""
        if self.__last_client_activity == 0:
            return False
        return (time.time() - self.__last_client_activity) < self.__connection_timeout

    def get_cpu_load_data(self):
        """Public method to get current CPU and Temp data for screen display
        Returns: tuple (cpu_percent, cpu_temp)
        """
        return (
            self.__robot_state.get('cpu_percent', 0.0),
            self.__robot_state.get('cpu_temp', 0.0)
        )

    def __publish_json(self, topic: str, data: Dict[str, Any]):
        """Publish JSON data to MQTT topic"""
        if not self.__client or not self.__connected:
            return
            
        try:
            json_payload = json.dumps(data)
            self.__client.publish(topic, json_payload)
            
            # Debug output for specific topics (removed battery topic reference)
            if self.__debug and topic == self.__topics['status']:
                print(f"📡 Published status to {topic}: battery={data.get('battery_level', 'N/A')}%")
                
        except Exception as e:
            if self.__debug:
                print(f"Error publishing to {topic}: {e}")
    
    def publish_event(self, event_type: str, event_data: Dict[str, Any]):
        """Publish one-time events"""
        if not self.__connected:
            return
        
        event_payload = {
            'timestamp': time.time(),
            'event_type': event_type,
            'data': event_data
        }
        
        self.__publish_json(f"rider/events/{event_type}", event_payload)
        
        if self.__debug:
            print(f"Event published: {event_type} - {event_data}")
    
    def is_connected(self) -> bool:
        """Check if MQTT is connected"""
        return self.__connected
    
    def get_broker_info(self) -> Dict[str, Any]:
        """Get broker connection information"""
        return {
            'host': self.__broker_host,
            'port': self.__broker_port,
            'connected': self.__connected,
            'client_id': self.__client_id,
            'protocol': 'MQTT 5.0'
        }
    
    def get_robot_state(self) -> Dict[str, Any]:
        """Get current robot state"""
        return self.__robot_state.copy()
    
    def cleanup(self):
        """Clean up MQTT resources with graceful disconnect"""
        if self.__debug:
            print("Cleaning up MQTT resources...")
        
        # Use graceful disconnect if connected, otherwise force disconnect
        if self.__connected:
            self.graceful_disconnect()
        else:
            self.disconnect() 