#!/usr/bin/env python3
# coding=utf-8

# Rider Robot MQTT Communication Module
# Handles bidirectional MQTT communication for remote control and monitoring
# Marc Wester

import json
import time
import threading
import paho.mqtt.client as mqtt
from typing import Optional, Callable, Dict, Any

class RiderMQTT:
    def __init__(self, robot=None, broker_host="localhost", broker_port=1883, debug=False):
        self.__debug = debug
        self.__robot = robot
        self.__broker_host = broker_host
        self.__broker_port = broker_port
        self.__client_id = f"rider_robot_{int(time.time())}"
        
        # MQTT client
        self.__client = None
        self.__connected = False
        self.__running = False
        
        # Publishing intervals (seconds)
        self.__status_interval = 2.0  # Status updates every 2 seconds
        self.__imu_interval = 0.5     # IMU data every 500ms
        self.__battery_interval = 10.0  # Battery every 10 seconds
        
        # Last publish times
        self.__last_status_publish = 0
        self.__last_imu_publish = 0
        self.__last_battery_publish = 0
        
        # Current robot state
        self.__robot_state = {
            'battery_level': 0,
            'speed_scale': 1.0,
            'roll_balance_enabled': False,
            'performance_mode_enabled': False,
            'camera_enabled': False,
            'controller_connected': False,
            'roll': 0.0,
            'pitch': 0.0,
            'yaw': 0.0,
            'height': 85,
            'connection_status': 'disconnected'
        }
        
        # Command callbacks
        self.__command_callbacks = {}
        
        # Topic structure
        self.__topics = {
            'status': 'rider/status',
            'battery': 'rider/status/battery',
            'imu': 'rider/status/imu',
            'camera': 'rider/status/camera',
            'connection': 'rider/status/connection',
            'control_movement': 'rider/control/movement',
            'control_settings': 'rider/control/settings',
            'control_camera': 'rider/control/camera',
            'control_system': 'rider/control/system',
            'request_battery': 'rider/request/battery'
        }
        
        # Publishing thread
        self.__publish_thread = None
        
        if self.__debug:
            print(f"RiderMQTT initialized - Broker: {broker_host}:{broker_port}")
    
    def set_command_callback(self, command_type: str, callback: Callable):
        """Set callback function for specific command types"""
        self.__command_callbacks[command_type] = callback
        if self.__debug:
            print(f"Command callback set for: {command_type}")
    
    def connect(self) -> bool:
        """Connect to MQTT broker"""
        try:
            self.__client = mqtt.Client(client_id=self.__client_id)
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
                if self.__debug:
                    print("✅ MQTT connected successfully")
                return True
            else:
                if self.__debug:
                    print("❌ MQTT connection timeout")
                return False
                
        except Exception as e:
            if self.__debug:
                print(f"❌ MQTT connection failed: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from MQTT broker"""
        self.__running = False
        
        if self.__publish_thread and self.__publish_thread.is_alive():
            self.__publish_thread.join(timeout=2)
        
        if self.__client:
            self.__client.loop_stop()
            self.__client.disconnect()
            self.__connected = False
        
        if self.__debug:
            print("MQTT disconnected")
    
    def __on_connect(self, client, userdata, flags, rc):
        """Callback for MQTT connection"""
        if rc == 0:
            self.__connected = True
            if self.__debug:
                print("MQTT broker connected")
            
            # Subscribe to control topics
            control_topics = [
                self.__topics['control_movement'],
                self.__topics['control_settings'],
                self.__topics['control_camera'],
                self.__topics['control_system'],
                self.__topics['request_battery']
            ]
            
            for topic in control_topics:
                client.subscribe(topic)
                if self.__debug:
                    print(f"Subscribed to: {topic}")
        else:
            if self.__debug:
                print(f"MQTT connection failed with code: {rc}")
    
    def __on_disconnect(self, client, userdata, rc):
        """Callback for MQTT disconnection"""
        self.__connected = False
        if self.__debug:
            print(f"MQTT broker disconnected with code: {rc}")
    
    def __on_message(self, client, userdata, msg):
        """Handle incoming MQTT messages"""
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode())
            
            if self.__debug:
                print(f"MQTT message received - Topic: {topic}, Payload: {payload}")
            
            # Route message to appropriate handler
            if topic == self.__topics['control_movement']:
                self.__handle_movement_command(payload)
            elif topic == self.__topics['control_settings']:
                self.__handle_settings_command(payload)
            elif topic == self.__topics['control_camera']:
                self.__handle_camera_command(payload)
            elif topic == self.__topics['control_system']:
                self.__handle_system_command(payload)
            elif topic == self.__topics['request_battery']:
                self.__handle_battery_request(payload)
                
        except Exception as e:
            if self.__debug:
                print(f"Error processing MQTT message: {e}")
    
    def __handle_movement_command(self, payload: Dict[str, Any]):
        """Handle movement control commands"""
        if 'movement' in self.__command_callbacks:
            self.__command_callbacks['movement'](payload)
        elif self.__debug:
            print(f"Movement command received but no callback set: {payload}")
    
    def __handle_settings_command(self, payload: Dict[str, Any]):
        """Handle settings control commands"""
        if 'settings' in self.__command_callbacks:
            self.__command_callbacks['settings'](payload)
        elif self.__debug:
            print(f"Settings command received but no callback set: {payload}")
    
    def __handle_camera_command(self, payload: Dict[str, Any]):
        """Handle camera control commands"""
        if 'camera' in self.__command_callbacks:
            self.__command_callbacks['camera'](payload)
        elif self.__debug:
            print(f"Camera command received but no callback set: {payload}")
    
    def __handle_system_command(self, payload: Dict[str, Any]):
        """Handle system control commands"""
        if 'system' in self.__command_callbacks:
            self.__command_callbacks['system'](payload)
        elif self.__debug:
            print(f"System command received but no callback set: {payload}")
    
    def __handle_battery_request(self, payload: Dict[str, Any]):
        """Handle battery level request"""
        if self.__debug:
            print(f"Battery request received: {payload}")
        
        # Immediately publish current battery level
        self.__publish_battery()
        
        # Also trigger callback if set
        if 'battery_request' in self.__command_callbacks:
            self.__command_callbacks['battery_request'](payload)
    
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
                
                # Publish battery data
                if current_time - self.__last_battery_publish >= self.__battery_interval:
                    self.__publish_battery()
                    self.__last_battery_publish = current_time
                
                time.sleep(0.1)  # Small sleep to prevent excessive CPU usage
                
            except Exception as e:
                if self.__debug:
                    print(f"Error in publishing loop: {e}")
                time.sleep(1)
    
    def __publish_status(self):
        """Publish general status information"""
        if not self.__connected:
            return
        
        status_data = {
            'timestamp': time.time(),
            'speed_scale': self.__robot_state['speed_scale'],
            'roll_balance_enabled': self.__robot_state['roll_balance_enabled'],
            'performance_mode_enabled': self.__robot_state['performance_mode_enabled'],
            'camera_enabled': self.__robot_state['camera_enabled'],
            'controller_connected': self.__robot_state['controller_connected'],
            'height': self.__robot_state['height'],
            'connection_status': self.__robot_state['connection_status']
        }
        
        self.__publish_json(self.__topics['status'], status_data)
    
    def __publish_imu_data(self):
        """Publish IMU/odometry data"""
        if not self.__connected:
            return
        
        imu_data = {
            'timestamp': time.time(),
            'roll': self.__robot_state['roll'],
            'pitch': self.__robot_state['pitch'],
            'yaw': self.__robot_state['yaw']
        }
        
        self.__publish_json(self.__topics['imu'], imu_data)
    
    def __publish_battery(self):
        """Publish battery information"""
        if not self.__connected:
            return
        
        battery_data = {
            'timestamp': time.time(),
            'level': self.__robot_state['battery_level'],
            'status': 'normal' if self.__robot_state['battery_level'] > 20 else 'low'
        }
        
        self.__publish_json(self.__topics['battery'], battery_data)
    
    def __publish_json(self, topic: str, data: Dict[str, Any]):
        """Publish JSON data to MQTT topic"""
        if not self.__client or not self.__connected:
            return
            
        try:
            json_payload = json.dumps(data)
            self.__client.publish(topic, json_payload)
            
            if self.__debug and topic == self.__topics['battery']:
                print(f"Published to {topic}: {data}")
                
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
            'client_id': self.__client_id
        }
    
    def cleanup(self):
        """Clean up MQTT resources"""
        if self.__debug:
            print("Cleaning up MQTT resources...")
        self.disconnect() 