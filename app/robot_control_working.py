#!/usr/bin/env python3
import time
import signal
import sys
from xgolib import XGO
from robot_serial_helper import get_robot_serial_port
from robot_context_manager import RobotManager, safe_robot_operation

@safe_robot_operation
def robot_control_demo(robot):
    print("=== Working Robot Control Demo ===")
    print("Using correct xgolite version and commands")
    
    print("\n=== Movement Demo ===")
    
    # 1. Height adjustments
    print("1. Height adjustments...")
    robot.translation('z', 25)   # 25mm up
    time.sleep(2)
    robot.translation('z', -15)  # 15mm down from start
    time.sleep(2)
    robot.translation('z', 0)    # back to original height
    time.sleep(2)
    print("   ✓ Height demo complete")
    
    # 2. Forward and backward
    print("2. Forward/backward movement...")
    robot.move_x(20)  # 20mm forward
    time.sleep(2)
    robot.move_x(0)   # stop
    time.sleep(1)
    
    robot.move_x(-20) # 20mm backward
    time.sleep(2)
    robot.move_x(0)   # stop
    time.sleep(1)
    print("   ✓ Forward/backward demo complete")
    
    # 3. Side to side
    print("3. Side to side movement...")
    robot.move_y(15)  # 15mm left
    time.sleep(2)
    robot.move_y(0)   # stop
    time.sleep(1)
    
    robot.move_y(-15) # 15mm right
    time.sleep(2)
    robot.move_y(0)   # stop
    time.sleep(1)
    print("   ✓ Side movement demo complete")
    
    # 4. Combined movements
    print("4. Combined movement demo...")
    robot.move_x(15)      # forward
    robot.move_y(10)      # and left
    time.sleep(2)
    robot.move_x(0)       # stop forward
    robot.move_y(0)       # stop left
    time.sleep(1)
    
    robot.move_x(-10)     # backward
    robot.translation('z', 20)  # and up
    time.sleep(2)
    robot.move_x(0)       # stop all
    robot.translation('z', 0)
    time.sleep(1)
    print("   ✓ Combined movement demo complete")
    
    print("\n✅ All robot movements working perfectly!")

def main():
    print("=== Safe Robot Control Demo ===")
    print("Ctrl+C to stop safely at any time")
    print()
    
    try:
        # Use context manager for safe robot connection and cleanup
        with RobotManager(version="xgolite", auto_reset=True) as robot:
            robot_control_demo(robot)
            
        print("\n📝 Summary of working commands:")
        print("   • with RobotManager(version='xgolite') as robot:")
        print("   • robot.move_x(mm)     # Forward/backward in millimeters")
        print("   • robot.move_y(mm)     # Left/right in millimeters") 
        print("   • robot.translation('z', mm)  # Height in millimeters")
        print("   • robot.reset()        # Reset robot")
        print("   • Automatic cleanup on exit/interrupt")
        
    except KeyboardInterrupt:
        print("\n🛑 Demo interrupted by user")
    except Exception as e:
        print(f"❌ Demo failed: {e}")
    finally:
        print("\n✅ Demo complete - robot cleaned up safely")

if __name__ == "__main__":
    main() 