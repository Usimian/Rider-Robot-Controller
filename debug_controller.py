#!/usr/bin/env python3

import pygame
import os
import sys
import time

def test_controller():
    """Comprehensive controller test for pygame 2.6.1"""
    
    print("="*60)
    print("PYGAME 2.6.1 CONTROLLER DEBUG TOOL")
    print("="*60)
    
    # Set up environment for headless operation
    os.environ['SDL_VIDEODRIVER'] = 'dummy'
    
    # Initialize pygame
    try:
        pygame.init()
        pygame.joystick.init()
        print(f"✅ Pygame initialized successfully")
        print(f"   Version: {pygame.version.ver}")
        print(f"   SDL Version: {pygame.version.SDL}")
    except Exception as e:
        print(f"❌ Failed to initialize pygame: {e}")
        return False
    
    # Create minimal display
    try:
        pygame.display.set_mode((1, 1))
        print("✅ Display initialized")
    except Exception as e:
        print(f"⚠️  Display init failed (non-critical): {e}")
    
    # Check for controllers
    controller_count = pygame.joystick.get_count()
    print(f"\n🎮 Controllers detected: {controller_count}")
    
    if controller_count == 0:
        print("❌ No controllers found!")
        return False
    
    # Initialize controller
    try:
        controller = pygame.joystick.Joystick(0)
        controller.init()
        print(f"✅ Controller initialized: {controller.get_name()}")
        
        # Get controller properties
        print(f"   GUID: {controller.get_guid()}")
        print(f"   Axes: {controller.get_numaxes()}")
        print(f"   Buttons: {controller.get_numbuttons()}")
        print(f"   Hats (D-pads): {controller.get_numhats()}")
        
        # Test if controller has instance ID (pygame 2.0+ feature)
        try:
            instance_id = controller.get_instance_id()
            print(f"   Instance ID: {instance_id}")
        except AttributeError:
            print("   Instance ID: Not supported")
        
        # Test power level (if supported)
        try:
            power_level = controller.get_power_level()
            print(f"   Power Level: {power_level}")
        except AttributeError:
            print("   Power Level: Not supported")
        
    except Exception as e:
        print(f"❌ Failed to initialize controller: {e}")
        return False
    
    print("\n📊 REAL-TIME CONTROLLER TEST")
    print("Move sticks and press buttons. Press Ctrl+C to exit.")
    print("-" * 40)
    
    # Track button states
    button_states = {}
    
    try:
        clock = pygame.time.Clock()
        
        for i in range(1500):  # Run for about 30 seconds at 50Hz
            # Process events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    break
                    
                elif event.type == pygame.JOYBUTTONDOWN:
                    print(f"🔽 Button {event.button} PRESSED")
                    button_states[event.button] = True
                    
                elif event.type == pygame.JOYBUTTONUP:
                    print(f"🔼 Button {event.button} RELEASED")
                    button_states[event.button] = False
                    
                elif event.type == pygame.JOYAXISMOTION:
                    # Only show significant axis movements
                    if abs(event.value) > 0.1:
                        print(f"🎯 Axis {event.axis}: {event.value:.3f}")
                        
                elif event.type == pygame.JOYHATMOTION:
                    print(f"🎪 Hat {event.hat}: {event.value}")
                    
                elif event.type == pygame.JOYDEVICEADDED:
                    print(f"🔌 Controller ADDED: {event.device_index}")
                    
                elif event.type == pygame.JOYDEVICEREMOVED:
                    print(f"🔌 Controller REMOVED: {event.instance_id}")
            
            # Sample current axis values every 50 frames (1 second)
            if i % 50 == 0 and i > 0:
                print(f"\n📋 Current Axis Values (frame {i}):")
                for axis in range(controller.get_numaxes()):
                    value = controller.get_axis(axis)
                    if abs(value) > 0.05:  # Only show active axes
                        print(f"   Axis {axis}: {value:.3f}")
                
                # Check button states
                pressed_buttons = []
                for button in range(controller.get_numbuttons()):
                    if controller.get_button(button):
                        pressed_buttons.append(str(button))
                if pressed_buttons:
                    print(f"   Pressed buttons: {', '.join(pressed_buttons)}")
                
                # Check hat states
                for hat in range(controller.get_numhats()):
                    hat_value = controller.get_hat(hat)
                    if hat_value != (0, 0):
                        print(f"   Hat {hat}: {hat_value}")
            
            clock.tick(50)
            
    except KeyboardInterrupt:
        print("\n\n🛑 Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        try:
            controller.quit()
            pygame.quit()
            print("✅ Cleanup completed")
        except Exception as e:
            print(f"⚠️  Cleanup error: {e}")
    
    return True

def test_specific_mappings():
    """Test specific button/axis mappings used in rider_controller.py"""
    
    print("\n" + "="*60)
    print("TESTING RIDER CONTROLLER MAPPINGS")
    print("="*60)
    
    # Button mapping from rider_controller.py
    BUTTON_MAPPING = {
        'MIN_HEIGHT': 0,           # A/X button
        'BATTERY_CHECK': 1,        # B/Circle button
        'MAX_HEIGHT': 2,          # Triangle button
        'ACTION_SWING': 3,         # Square button
        'SPEED_DOWN': 4,           # L1
        'SPEED_UP': 5,             # R1
        'RESET': 9,                # Back/Select
        'EMERGENCY_STOP': 10,       # Home button
        'HEIGHT_DOWN': 11,         # Left stick click
        'HEIGHT_UP': 12,           # PS button
    }
    
    # Axis mapping from rider_controller.py
    AXIS_MAPPING = {
        'LEFT_STICK_X': 0,
        'LEFT_STICK_Y': 1, 
        'RIGHT_STICK_X': 3,
        'RIGHT_STICK_Y': 4,
    }
    
    print("\nExpected Button Mapping:")
    for action, button_id in BUTTON_MAPPING.items():
        print(f"  {action}: Button {button_id}")
    
    print("\nExpected Axis Mapping:")
    for axis_name, axis_id in AXIS_MAPPING.items():
        print(f"  {axis_name}: Axis {axis_id}")
    
    print("\n🧪 Press the following to test mapping:")
    print("  - Move left stick in all directions")
    print("  - Move right stick in all directions") 
    print("  - Press A/X button (should be button 0)")
    print("  - Press B/Circle button (should be button 1)")
    print("  - Press any other buttons")
    print("\nPress Ctrl+C when done testing")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "mapping":
        test_specific_mappings()
    
    success = test_controller()
    
    if success:
        print("\n🎉 Controller test completed successfully!")
        print("\nIf you saw any issues:")
        print("1. Axis values not changing when moving sticks")
        print("2. Button numbers different than expected")
        print("3. Events not being detected")
        print("4. Controller disconnecting unexpectedly")
        print("\nPlease report what you observed.")
    else:
        print("\n❌ Controller test failed!") 