#!/usr/bin/env python3
# coding=utf-8

# Test script for Rider MQTT communication module
# Marc Wester

import time
import sys
import os
from rider_mqtt import RiderMQTT

def test_movement_callback(payload):
    """Test callback for movement commands"""
    print(f"🎮 Movement command received: {payload}")

def test_settings_callback(payload):
    """Test callback for settings commands"""
    print(f"⚙️  Settings command received: {payload}")

def test_camera_callback(payload):
    """Test callback for camera commands"""
    print(f"📷 Camera command received: {payload}")

def test_system_callback(payload):
    """Test callback for system commands"""
    print(f"🔧 System command received: {payload}")

def main():
    print("🤖 Testing Rider MQTT Communication Module")
    print("=" * 50)
    
    # Initialize MQTT with debug enabled
    mqtt_client = RiderMQTT(debug=True)
    
    # Set up command callbacks
    mqtt_client.set_command_callback('movement', test_movement_callback)
    mqtt_client.set_command_callback('settings', test_settings_callback)
    mqtt_client.set_command_callback('camera', test_camera_callback)
    mqtt_client.set_command_callback('system', test_system_callback)
    
    # Connect to MQTT broker
    print("\n📡 Connecting to MQTT broker...")
    if not mqtt_client.connect():
        print("❌ Failed to connect to MQTT broker")
        return
    
    print("✅ Connected to MQTT broker")
    print(f"📊 Broker info: {mqtt_client.get_broker_info()}")
    
    # Simulate robot state updates
    print("\n🔄 Starting robot state simulation...")
    
    try:
        for i in range(30):  # Run for 30 seconds
            # Update robot state with simulated data
            battery_level = max(20, 100 - (i * 2))  # Simulate battery drain
            speed_scale = 1.0 + (i % 3) * 0.5  # Cycle through speed scales
            roll = (i % 10) - 5  # Simulate roll movement
            pitch = (i % 8) - 4  # Simulate pitch movement
            yaw = i % 360  # Simulate yaw rotation
            
            mqtt_client.update_robot_state(
                battery_level=battery_level,
                speed_scale=speed_scale,
                roll_balance_enabled=(i % 4) == 0,
                performance_mode_enabled=(i % 6) == 0,
                camera_enabled=(i % 8) == 0,
                controller_connected=True,
                roll=roll,
                pitch=pitch,
                yaw=yaw,
                height=85 + (i % 10),
                connection_status='connected'
            )
            
            # Publish some test events
            if i % 10 == 0:
                mqtt_client.publish_event('test_event', {
                    'iteration': i,
                    'message': f'Test event at iteration {i}'
                })
            
            print(f"📈 Iteration {i+1}/30 - Battery: {battery_level}%, Speed: {speed_scale:.1f}x")
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
    
    # Clean up
    print("\n🧹 Cleaning up...")
    mqtt_client.cleanup()
    print("✅ Test completed")

if __name__ == "__main__":
    main() 