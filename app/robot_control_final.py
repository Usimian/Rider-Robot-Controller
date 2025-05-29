#!/usr/bin/env python3
import time
import signal
import sys
from xgo_toolkit import XGO

class RobotController:
    """Final working robot controller with proper turn values and cleanup"""
    
    def __init__(self):
        self.robot = None
        self.setup_signal_handlers()
    
    def setup_signal_handlers(self):
        """Setup graceful shutdown on Ctrl+C"""
        def signal_handler(sig, frame):
            print(f"\n🛑 Shutting down gracefully...")
            self.cleanup()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def connect(self):
        """Connect to robot"""
        print("🤖 Connecting to XGO robot...")
        self.robot = XGO('xgorider')  # Using updated toolkit
        print("✅ Robot connected successfully!")
        return self.robot
    
    def cleanup(self):
        """Stop robot and cleanup"""
        if self.robot:
            print("🧹 Stopping robot...")
            try:
                self.robot.rider_move_x(0)
                self.robot.rider_turn(0)
                self.robot.rider_reset()
            except:
                pass
            print("✅ Robot stopped safely")
    
    def demo_movements(self):
        """Demonstrate all working movements"""
        if not self.robot:
            print("❌ Robot not connected")
            return
        
        print("\n=== Robot Movement Demo ===")
        
        # 1. Forward movement
        print("1. 🚶 Moving forward...")
        self.robot.rider_move_x(0.3)
        time.sleep(3)
        self.robot.rider_move_x(0)
        time.sleep(1)
        
        # 2. Backward movement  
        print("2. 🚶 Moving backward...")
        self.robot.rider_move_x(-0.3)
        time.sleep(3)
        self.robot.rider_move_x(0)
        time.sleep(1)
        
        # 3. Turn left (using working value ≥30)
        print("3. ↺ Turning left...")
        self.robot.rider_turn(45)  # Values ≥30 work
        time.sleep(3)
        self.robot.rider_turn(0)
        time.sleep(1)
        
        # 4. Turn right
        print("4. ↻ Turning right...")
        self.robot.rider_turn(-45)  # Negative for opposite direction
        time.sleep(3)
        self.robot.rider_turn(0)
        time.sleep(1)
        
        # 5. Height adjustment
        print("5. ⬆️ Adjusting height...")
        self.robot.rider_height(20)
        time.sleep(2)
        self.robot.rider_height(0)
        time.sleep(2)
        
        # 6. Action sequence
        print("6. 🎭 Performing action...")
        self.robot.action(1)
        time.sleep(4)
        
        print("✅ Demo complete!")

def main():
    print("=== Final Working XGO Robot Controller ===")
    print("Features:")
    print("• Forward/backward movement: rider_move_x()")
    print("• Turn left/right: rider_turn() with values ≥30")
    print("• Height adjustment: rider_height()")
    print("• Actions: action()")
    print("• Graceful shutdown on Ctrl+C")
    print("• No serial console interference")
    print()
    
    controller = RobotController()
    
    try:
        # Connect to robot
        controller.connect()
        
        # Run demo
        controller.demo_movements()
        
        # Interactive mode
        print("\n🎮 Interactive Mode:")
        print("Commands: w=forward, s=backward, a=left, d=right, u=up, n=down, q=quit")
        
        while True:
            cmd = input("Enter command: ").lower().strip()
            
            if cmd == 'q':
                break
            elif cmd == 'w':
                print("Moving forward...")
                controller.robot.rider_move_x(0.3)
                time.sleep(2)
                controller.robot.rider_move_x(0)
            elif cmd == 's':
                print("Moving backward...")
                controller.robot.rider_move_x(-0.3)
                time.sleep(2)
                controller.robot.rider_move_x(0)
            elif cmd == 'a':
                print("Turning left...")
                controller.robot.rider_turn(45)
                time.sleep(2)
                controller.robot.rider_turn(0)
            elif cmd == 'd':
                print("Turning right...")
                controller.robot.rider_turn(-45)
                time.sleep(2)
                controller.robot.rider_turn(0)
            elif cmd == 'u':
                print("Height up...")
                controller.robot.rider_height(20)
                time.sleep(2)
                controller.robot.rider_height(0)
            elif cmd == 'n':
                print("Height down...")
                controller.robot.rider_height(-20)
                time.sleep(2)
                controller.robot.rider_height(0)
            else:
                print("Unknown command. Use w/s/a/d/u/n/q")
        
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        controller.cleanup()
        print("\n✅ Program ended safely")

if __name__ == "__main__":
    main() 