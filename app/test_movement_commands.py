#!/usr/bin/env python3
# coding=utf-8

"""
Test script for new movement command specification
Tests move, turn, and stop commands with auto-completion
"""

import time
import json
import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
from config import MQTT_BROKER_HOST, MQTT_BROKER_PORT

class MovementCommandTester:
    def __init__(self, broker_host=MQTT_BROKER_HOST, broker_port=MQTT_BROKER_PORT):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.client_id = f"movement_tester_{int(time.time())}"
        self.client = None
        self.connected = False
        self.completion_received = False
        self.last_completion = None
        
    def on_connect(self, client, userdata, flags, reason_code, properties):
        """Callback for MQTT connection"""
        if reason_code == 0:
            self.connected = True
            print(f"✅ Connected to MQTT broker at {self.broker_host}:{self.broker_port}")
            
            # Subscribe to movement response topic
            client.subscribe("rider/response/movement")
            print("📡 Subscribed to rider/response/movement")
        else:
            print(f"❌ Connection failed with reason code: {reason_code}")
    
    def on_disconnect(self, client, userdata, flags, reason_code, properties):
        """Callback for MQTT disconnection"""
        self.connected = False
        print(f"📤 Disconnected from MQTT broker (reason: {reason_code})")
    
    def on_message(self, client, userdata, msg):
        """Handle incoming MQTT messages"""
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode())
            
            if topic == "rider/response/movement":
                self.completion_received = True
                self.last_completion = payload
                
                action = payload.get('action')
                success = payload.get('success')
                status_icon = "✅" if success else "❌"
                
                print(f"\n{status_icon} Movement completion received:")
                print(f"   Action: {action}")
                print(f"   Success: {success}")
                
                if 'distance' in payload:
                    print(f"   Distance: {payload['distance']}mm")
                if 'angle' in payload:
                    print(f"   Angle: {payload['angle']}°")
                if 'actual_duration' in payload:
                    print(f"   Duration: {payload['actual_duration']:.2f}s")
                if 'error' in payload:
                    print(f"   Error: {payload['error']}")
                    
        except json.JSONDecodeError as e:
            print(f"⚠️ Invalid JSON in MQTT message: {e}")
        except Exception as e:
            print(f"⚠️ Error processing MQTT message: {e}")
    
    def connect(self):
        """Connect to MQTT broker"""
        try:
            self.client = mqtt.Client(
                client_id=self.client_id,
                callback_api_version=CallbackAPIVersion.VERSION2,
                protocol=mqtt.MQTTv5
            )
            self.client.on_connect = self.on_connect
            self.client.on_disconnect = self.on_disconnect
            self.client.on_message = self.on_message
            
            print(f"Connecting to MQTT broker at {self.broker_host}:{self.broker_port}...")
            self.client.connect(self.broker_host, self.broker_port, 60)
            self.client.loop_start()
            
            # Wait for connection
            timeout = 10
            start_time = time.time()
            while not self.connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)
            
            return self.connected
            
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from MQTT broker"""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            self.connected = False
    
    def send_command(self, command_data):
        """Send movement command and wait for completion"""
        if not self.connected:
            print("❌ Not connected to MQTT broker")
            return False
        
        try:
            # Reset completion flag
            self.completion_received = False
            self.last_completion = None
            
            # Publish command
            topic = "rider/control/movement"
            command_data['timestamp'] = time.time()
            json_payload = json.dumps(command_data)
            
            self.client.publish(topic, json_payload)
            print(f"\n📤 Command sent: {json.dumps(command_data, indent=2)}")
            
            # Wait for completion (with timeout)
            timeout = 30.0  # 30 second timeout
            start_time = time.time()
            
            while not self.completion_received and (time.time() - start_time) < timeout:
                time.sleep(0.1)
            
            if self.completion_received:
                return self.last_completion.get('success', False)
            else:
                print("⏰ Timeout waiting for completion response")
                return False
                
        except Exception as e:
            print(f"❌ Error sending command: {e}")
            return False
    
    def test_move_forward(self, distance_mm=200):
        """Test forward movement"""
        print("\n" + "="*60)
        print(f"TEST: Move Forward {distance_mm}mm")
        print("="*60)
        
        command = {
            "action": "move",
            "distance": distance_mm
        }
        
        return self.send_command(command)
    
    def test_move_backward(self, distance_mm=200):
        """Test backward movement"""
        print("\n" + "="*60)
        print(f"TEST: Move Backward {distance_mm}mm")
        print("="*60)
        
        command = {
            "action": "move",
            "distance": -distance_mm
        }
        
        return self.send_command(command)
    
    def test_turn_left(self, angle_deg=90):
        """Test left turn"""
        print("\n" + "="*60)
        print(f"TEST: Turn Left {angle_deg}°")
        print("="*60)
        
        command = {
            "action": "turn",
            "angle": -angle_deg
        }
        
        return self.send_command(command)
    
    def test_turn_right(self, angle_deg=90):
        """Test right turn"""
        print("\n" + "="*60)
        print(f"TEST: Turn Right {angle_deg}°")
        print("="*60)
        
        command = {
            "action": "turn",
            "angle": angle_deg
        }
        
        return self.send_command(command)
    
    def test_stop(self):
        """Test emergency stop"""
        print("\n" + "="*60)
        print("TEST: Emergency Stop")
        print("="*60)
        
        command = {
            "action": "stop"
        }
        
        return self.send_command(command)
    
    def run_all_tests(self):
        """Run all movement tests"""
        print("\n" + "🤖 MOVEMENT COMMAND TEST SUITE ".center(60, "="))
        
        tests = [
            ("Move Forward 200mm", lambda: self.test_move_forward(200)),
            ("Move Backward 200mm", lambda: self.test_move_backward(200)),
            ("Turn Right 90°", lambda: self.test_turn_right(90)),
            ("Turn Left 90°", lambda: self.test_turn_left(90)),
            ("Emergency Stop", lambda: self.test_stop())
        ]
        
        results = []
        
        for test_name, test_func in tests:
            print(f"\n⏳ Running: {test_name}")
            success = test_func()
            results.append((test_name, success))
            
            # Brief pause between tests
            if test_name != "Emergency Stop":
                time.sleep(1)
        
        # Print summary
        print("\n" + "📊 TEST SUMMARY ".center(60, "="))
        passed = sum(1 for _, success in results if success)
        total = len(results)
        
        for test_name, success in results:
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{status}: {test_name}")
        
        print(f"\n{'='*60}")
        print(f"Results: {passed}/{total} tests passed")
        print("="*60)
        
        return passed == total


def main():
    import sys
    
    print("🤖 Robot Movement Command Tester")
    print("="*60)
    
    tester = MovementCommandTester()
    
    if not tester.connect():
        print("❌ Failed to connect to MQTT broker")
        sys.exit(1)
    
    try:
        if len(sys.argv) > 1:
            # Interactive mode - specific test
            test_type = sys.argv[1].lower()
            
            if test_type == "forward":
                distance = int(sys.argv[2]) if len(sys.argv) > 2 else 200
                tester.test_move_forward(distance)
            elif test_type == "backward":
                distance = int(sys.argv[2]) if len(sys.argv) > 2 else 200
                tester.test_move_backward(distance)
            elif test_type == "left":
                angle = int(sys.argv[2]) if len(sys.argv) > 2 else 90
                tester.test_turn_left(angle)
            elif test_type == "right":
                angle = int(sys.argv[2]) if len(sys.argv) > 2 else 90
                tester.test_turn_right(angle)
            elif test_type == "stop":
                tester.test_stop()
            elif test_type == "all":
                tester.run_all_tests()
            else:
                print(f"❌ Unknown test type: {test_type}")
                print("\nUsage:")
                print("  python3 test_movement_commands.py [test_type] [value]")
                print("\nTest types:")
                print("  forward [distance_mm]  - Test forward movement (default: 200mm)")
                print("  backward [distance_mm] - Test backward movement (default: 200mm)")
                print("  left [angle_deg]       - Test left turn (default: 90°)")
                print("  right [angle_deg]      - Test right turn (default: 90°)")
                print("  stop                   - Test emergency stop")
                print("  all                    - Run all tests")
        else:
            # Default: run all tests
            tester.run_all_tests()
            
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
    finally:
        print("\n🧹 Cleaning up...")
        tester.disconnect()
        print("✅ Cleanup complete!")


if __name__ == "__main__":
    main()
