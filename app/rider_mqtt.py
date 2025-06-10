#!/usr/bin/env python3
# coding=utf-8

# Rider Robot MQTT Communication Module
# Handles bidirectional MQTT communication for remote control and monitoring
# Enhanced with robust disconnect handling and safety features
# Marc Wester

import json
import time
import threading
import os
import psutil
import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
from typing import Optional, Callable, Dict, Any

class RiderMQTT:
    def __init__(self, robot=None, broker_host="192.168.1.173", broker_port=1883, debug=False):
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
        self.__connection_timeout = 30.0  # 30 seconds timeout for client inactivity
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
            'cpu_load_1min': 0.0,
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
            'server_status': 'rider/server/status'
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
                self.__topics['client_disconnect']
            ]
            
            for topic in control_topics:
                client.subscribe(topic)
                if self.__debug:
                    print(f"Subscribed to: {topic}")
            
            # Reset client activity tracking
            self.__last_client_activity = time.time()
            self.__inactive_client_safety_triggered = False
            self.__robot_state['client_connected'] = True
            self.__robot_state['connection_status'] = 'connected'
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
        
        # Update connection status
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
        """Handle movement control commands with enhanced safety tracking"""
        x = payload.get('x', 0)  # -100 to +100 (left/right)
        y = payload.get('y', 0)  # -100 to +100 (backward/forward)
        timestamp = payload.get('timestamp', time.time())
        source = payload.get('source', 'client')
        
        # Update movement command tracking for timeout monitoring
        self.__last_movement_command = {
            'x': x,
            'y': y,
            'timestamp': timestamp,
            'source': source
        }
        
        if self.__debug:
            print(f"🎮 Movement command: x={x}, y={y}, timestamp={timestamp}, source={source}")
        
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
                    print(f"❌ Error executing movement command: {e}")
                # On movement command error, ensure robot is stopped
                try:
                    self.__stop_robot_movement()
                except:
                    pass
        
        # Trigger callback if set
        if 'movement' in self.__command_callbacks:
            self.__command_callbacks['movement'](payload)
    
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
        while self.__running and self.__connected:
            try:
                current_time = time.time()
                
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
            'cpu_load_1min': self.__robot_state['cpu_load_1min'],
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
        """Read current CPU usage and load average data"""
        try:
            # Get CPU usage percentage with short interval for accuracy
            # Using 0.1 second interval for more reliable readings
            self.__robot_state['cpu_percent'] = psutil.cpu_percent(interval=0.1)
            
            # Get load average (1 minute only)
            load_avg = os.getloadavg()
            self.__robot_state['cpu_load_1min'] = load_avg[0]
            
            if self.__debug:
                print(f"📊 CPU: {self.__robot_state['cpu_percent']:.1f}%, Load: {self.__robot_state['cpu_load_1min']:.2f}")
                
        except Exception as e:
            if self.__debug:
                print(f"⚠️  MQTT: Error reading CPU data: {e}")
            # Set default values on error
            self.__robot_state['cpu_percent'] = 0.0
            self.__robot_state['cpu_load_1min'] = 0.0
    
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