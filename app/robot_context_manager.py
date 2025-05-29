#!/usr/bin/env python3
import signal
import sys
import time
import atexit
from xgolib import XGO
from robot_serial_helper import get_robot_serial_port

class RobotManager:
    """
    Context manager for XGO robot connections with proper cleanup and signal handling.
    Ensures robot is safely stopped and serial connection is closed on exit.
    """
    
    def __init__(self, version="xgolite", port=None, auto_reset=True):
        self.version = version
        self.port = port or get_robot_serial_port()
        self.auto_reset = auto_reset
        self.robot = None
        self._signal_handlers_set = False
        
    def __enter__(self):
        """Enter context - connect to robot and set up signal handlers"""
        try:
            print(f"🤖 Connecting to robot on {self.port} with version {self.version}...")
            self.robot = XGO(port=self.port, version=self.version)
            print("✓ Robot connected successfully")
            
            if self.auto_reset:
                print("🔄 Resetting robot...")
                self.robot.reset()
                time.sleep(2)
                print("✓ Robot reset complete")
            
            # Set up signal handlers for graceful shutdown
            self._setup_signal_handlers()
            
            # Register cleanup function for normal exit
            atexit.register(self._cleanup_robot)
            
            return self.robot
            
        except Exception as e:
            print(f"❌ Failed to connect to robot: {e}")
            raise
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context - cleanup robot and connections"""
        self._cleanup_robot()
        
        if exc_type is KeyboardInterrupt:
            print("\n🛑 Program interrupted by user - robot cleaned up safely")
            return True  # Suppress KeyboardInterrupt
        elif exc_type:
            print(f"❌ Program exited with error: {exc_val}")
        
        return False
    
    def _setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown"""
        if self._signal_handlers_set:
            return
            
        def signal_handler(sig, frame):
            print(f"\n🛑 Received signal {sig} - shutting down gracefully...")
            self._cleanup_robot()
            sys.exit(0)
        
        # Handle common termination signals
        signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
        signal.signal(signal.SIGTERM, signal_handler)  # Termination
        
        self._signal_handlers_set = True
    
    def _cleanup_robot(self):
        """Stop robot movement and close connections"""
        if self.robot is None:
            return
            
        try:
            print("🧹 Cleaning up robot...")
            
            # Stop all movement
            if hasattr(self.robot, 'move_x'):
                self.robot.move_x(0)
            if hasattr(self.robot, 'move_y'):
                self.robot.move_y(0)
            if hasattr(self.robot, 'rider_move_x'):
                self.robot.rider_move_x(0)
            if hasattr(self.robot, 'rider_turn'):
                self.robot.rider_turn(0)
            
            # Reset to safe position
            self.robot.reset()
            time.sleep(0.5)
            
            # Close serial connection if available
            if hasattr(self.robot, 'ser') and hasattr(self.robot.ser, 'close'):
                self.robot.ser.close()
            
            print("✓ Robot cleanup complete")
            
        except Exception as e:
            print(f"⚠️ Warning during robot cleanup: {e}")
        finally:
            self.robot = None
    
    def emergency_stop(self):
        """Emergency stop - immediately halt all movement"""
        if self.robot is None:
            return
            
        try:
            print("🚨 EMERGENCY STOP")
            self.robot.move_x(0)
            self.robot.move_y(0)
            if hasattr(self.robot, 'rider_move_x'):
                self.robot.rider_move_x(0)
            if hasattr(self.robot, 'rider_turn'):
                self.robot.rider_turn(0)
        except Exception as e:
            print(f"❌ Error during emergency stop: {e}")


def safe_robot_operation(func):
    """
    Decorator for robot operations that ensures cleanup on errors.
    Usage: @safe_robot_operation
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except KeyboardInterrupt:
            print("\n🛑 Operation interrupted - cleaning up...")
            # Emergency stop if robot is passed as first argument
            if args and hasattr(args[0], 'move_x'):
                try:
                    args[0].move_x(0)
                    args[0].move_y(0)
                except:
                    pass
            raise
        except Exception as e:
            print(f"❌ Error in robot operation: {e}")
            # Emergency stop if robot is passed as first argument
            if args and hasattr(args[0], 'move_x'):
                try:
                    args[0].move_x(0)
                    args[0].move_y(0)
                except:
                    pass
            raise
    return wrapper


# Example usage function
@safe_robot_operation
def example_robot_movements(robot):
    """Example of safe robot movements with proper error handling"""
    
    print("🎯 Testing robot movements...")
    
    # Height adjustment
    print("1. Height adjustment...")
    robot.translation('z', 20)
    time.sleep(2)
    robot.translation('z', 0)
    time.sleep(1)
    
    # Forward/backward
    print("2. Forward movement...")
    robot.move_x(15)
    time.sleep(2)
    robot.move_x(0)
    time.sleep(1)
    
    print("3. Backward movement...")
    robot.move_x(-15)
    time.sleep(2)
    robot.move_x(0)
    time.sleep(1)
    
    # Side to side
    print("4. Side movement...")
    robot.move_y(10)
    time.sleep(2)
    robot.move_y(0)
    time.sleep(1)
    
    print("✅ All movements completed safely")


if __name__ == "__main__":
    print("=== Robot Context Manager Demo ===")
    
    # Example 1: Using context manager
    try:
        with RobotManager(version="xgolite") as robot:
            example_robot_movements(robot)
            
    except Exception as e:
        print(f"❌ Demo failed: {e}")
    
    print("\n✅ Demo complete - robot cleaned up automatically") 