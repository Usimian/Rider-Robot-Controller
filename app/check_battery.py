#!/usr/bin/env python3
import time
from xgolib import XGO
from robot_serial_helper import get_robot_serial_port

def check_robot_battery():
    print("=== Robot Battery Check ===")
    
    try:
        # Try to connect to robot
        robot_port = get_robot_serial_port()
        print(f"Connecting to robot on port: {robot_port}")
        
        # Try different versions if needed
        versions_to_try = ["xgorider", "xgomini", "xgolite"]
        
        robot = None
        working_version = None
        
        for version in versions_to_try:
            try:
                print(f"Trying version: {version}...")
                robot = XGO(port=robot_port, version=version)
                working_version = version
                print(f"✓ Connected with {version}")
                break
            except Exception as e:
                print(f"  Failed with {version}: {e}")
                continue
        
        if robot is None:
            print("❌ Could not connect to robot")
            print("\nPossible issues:")
            print("• Robot is powered off")
            print("• Connection cable is loose")
            print("• Robot is in wrong mode")
            return
        
        print(f"\n📶 Robot connected successfully with {working_version}")
        
        # Now try to read battery level
        print("\n🔋 Reading battery level...")
        try:
            battery_level = robot.read_battery()
            print(f"Battery level: {battery_level}%")
            
            if battery_level == 0:
                print("⚠️  WARNING: Battery reading failed or robot not responding")
            elif battery_level < 20:
                print("🚨 CRITICAL: Battery very low! Please charge robot.")
            elif battery_level < 40:
                print("⚠️  WARNING: Battery low. Consider charging soon.")
            elif battery_level < 70:
                print("📱 GOOD: Battery level is adequate.")
            else:
                print("✅ EXCELLENT: Battery level is good!")
            
            return battery_level
            
        except Exception as e:
            print(f"❌ Could not read battery: {e}")
            print("This might indicate communication issues.")
            return None
        
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return None

def test_robot_if_connected():
    """Test basic robot functionality if battery check succeeded"""
    print("\n=== Quick Robot Test ===")
    
    try:
        robot_port = get_robot_serial_port()
        robot = XGO(port=robot_port, version="xgorider")
        
        print("Testing basic movement...")
        robot.reset()
        time.sleep(1)
        
        # Small movement test
        robot.rider_move_x(0.2)
        time.sleep(1)
        robot.rider_move_x(0)
        
        print("✅ Robot movement test completed!")
        
    except Exception as e:
        print(f"❌ Robot test failed: {e}")

if __name__ == "__main__":
    battery_level = check_robot_battery()
    
    if battery_level is not None and battery_level > 0:
        print(f"\n📊 Battery Status: {battery_level}%")
        if battery_level > 20:  # Only test movement if battery is adequate
            test_robot_if_connected()
        else:
            print("⚠️ Skipping movement test due to low battery")
    else:
        print("\n❌ Could not determine battery status")
        print("Robot may be disconnected or have communication issues") 