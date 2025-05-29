#!/usr/bin/env python3
import time
import os
from xgolib import XGO
from robot_serial_helper import get_robot_serial_port

def try_recover_connection():
    print("=== Robot Connection Recovery ===")
    
    # Step 1: Check if the robot is physically connected
    print("1. Please check the following:")
    print("   • Is the robot powered ON? (LED lights visible?)")
    print("   • Is the USB/serial cable firmly connected?")
    print("   • Are there any loose connections?")
    input("   Press Enter after checking...")
    
    # Step 2: Try different recovery methods
    recovery_methods = [
        ("Standard xgorider connection", "xgorider"),
        ("Alternative xgomini connection", "xgomini"), 
        ("Fallback xgolite connection", "xgolite"),
    ]
    
    for method_name, version in recovery_methods:
        print(f"\n2. Trying {method_name}...")
        try:
            robot_port = get_robot_serial_port()
            print(f"   Using port: {robot_port}")
            
            # Try connection with a longer timeout
            robot = XGO(port=robot_port, version=version)
            print(f"   ✓ Connected with {version}")
            
            # Test if it responds
            print("   Testing response...")
            robot.reset()
            time.sleep(3)  # Longer wait
            
            # Try a simple movement
            robot.rider_move_x(0.2)
            time.sleep(2)
            robot.rider_move_x(0)
            
            print(f"   🎉 SUCCESS! Robot is working with {version}")
            return robot, version
            
        except Exception as e:
            print(f"   ❌ Failed with {version}: {e}")
            time.sleep(1)
            continue
    
    print("\n3. All recovery methods failed.")
    print("\nTroubleshooting steps:")
    print("📋 Hardware checks:")
    print("   • Turn robot OFF and ON again")
    print("   • Check cable connections")
    print("   • Try a different USB cable")
    print("   • Check battery level")
    
    print("\n📋 Software checks:")
    print("   • Restart this Raspberry Pi")
    print("   • Check if robot is in correct mode")
    print("   • Try connecting robot to a different device")
    
    return None, None

def test_recovered_robot(robot, version):
    """Test the recovered robot connection"""
    if robot is None:
        return
        
    print(f"\n=== Testing Recovered Robot ({version}) ===")
    try:
        print("Testing basic movements...")
        
        # Forward
        print("• Forward...")
        robot.rider_move_x(0.3)
        time.sleep(2)
        robot.rider_move_x(0)
        time.sleep(1)
        
        # Turn
        print("• Turn...")
        robot.rider_turn(40)
        time.sleep(2)
        robot.rider_turn(0)
        
        print("✅ Robot recovery successful!")
        
    except Exception as e:
        print(f"❌ Robot still not responding: {e}")

if __name__ == "__main__":
    robot, version = try_recover_connection()
    test_recovered_robot(robot, version) 