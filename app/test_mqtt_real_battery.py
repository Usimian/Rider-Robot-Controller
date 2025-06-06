#!/usr/bin/env python3
# coding=utf-8

# Test script for Rider MQTT communication module with REAL battery readings
# Marc Wester

import time
from rider_mqtt import RiderMQTT

# Try to import the robot controller to get real battery readings
try:
    from xgo_toolkit import XGO

    ROBOT_AVAILABLE = True
except ImportError:
    ROBOT_AVAILABLE = False
    print("⚠️  XGO toolkit not available - using simulated data")


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


def test_battery_request_callback(payload):
    """Test callback for battery request commands"""
    print(f"🔋 Battery request received: {payload}")


def read_real_battery(robot):
    """Read real battery level from robot"""
    if not robot:
        return None

    try:
        # Try rider-specific method first
        try:
            battery_level = robot.rider_read_battery()
            print(f"📊 Real battery reading (rider method): {battery_level}%")
            return battery_level
        except AttributeError:
            # Fallback to standard method
            try:
                battery_level = robot.read_battery()
                msg = f"📊 Real battery reading (standard method): {battery_level}%"
                print(msg)
                return battery_level
            except AttributeError:
                print("⚠️  No battery reading method available")
                return None
    except Exception as e:
        print(f"❌ Error reading real battery: {e}")
        return None


def main():
    print("🤖 Testing Rider MQTT Communication Module with REAL Battery")
    print("=" * 60)

    # Initialize robot if available
    robot = None
    if ROBOT_AVAILABLE:
        try:
            print("🔌 Connecting to robot...")
            robot = XGO(port="/dev/ttyAMA0", version="xgomini")
            print("✅ Robot connected successfully")
        except Exception as e:
            print(f"⚠️  Could not connect to robot: {e}")
            print("📊 Will use simulated data instead")
            robot = None

    # Initialize MQTT with debug enabled
    mqtt_client = RiderMQTT(robot=robot, debug=True)

    # Set up command callbacks
    mqtt_client.set_command_callback("movement", test_movement_callback)
    mqtt_client.set_command_callback("settings", test_settings_callback)
    mqtt_client.set_command_callback("camera", test_camera_callback)
    mqtt_client.set_command_callback("system", test_system_callback)
    mqtt_client.set_command_callback("battery_request", test_battery_request_callback)

    # Connect to MQTT broker
    print("\n📡 Connecting to MQTT broker...")
    if not mqtt_client.connect():
        print("❌ Failed to connect to MQTT broker")
        return

    print("✅ Connected to MQTT broker")
    print(f"📊 Broker info: {mqtt_client.get_broker_info()}")

    # Test real battery reading
    print("\n🔋 Testing battery reading...")
    real_battery = read_real_battery(robot)

    if real_battery is not None:
        print(f"✅ Real battery level: {real_battery}%")
        use_real_battery = True
    else:
        print("⚠️  Using simulated battery data for testing")
        use_real_battery = False

    # Start robot state updates
    print("\n🔄 Starting robot state updates...")

    try:
        for i in range(60):  # Run for 60 seconds
            # Get battery level
            if use_real_battery:
                battery_level = read_real_battery(robot)
                if battery_level is None:
                    battery_level = 50  # Fallback value
            else:
                # Use a more stable simulated battery
                # (only drops 1% every 10 iterations)
                battery_level = max(20, 100 - (i // 10))

            # Other simulated data
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
                connection_status="connected",
            )

            # Publish some test events
            if i % 15 == 0:
                mqtt_client.publish_event(
                    "battery_check",
                    {
                        "iteration": i,
                        "battery_level": battery_level,
                        "real_reading": use_real_battery,
                        "message": f"Battery check at iteration {i}",
                    },
                )

            battery_status = "REAL" if use_real_battery else "SIM"
            msg = (
                f"📈 Iteration {i+1}/60 - Battery: {battery_level}% "
                f"({battery_status}), Speed: {speed_scale:.1f}x"
            )
            print(msg)
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")

    # Clean up
    print("\n🧹 Cleaning up...")
    mqtt_client.cleanup()

    if robot:
        try:
            robot.reset()
            print("🤖 Robot reset")
        except Exception:
            pass

    print("✅ Test completed")


if __name__ == "__main__":
    main()
