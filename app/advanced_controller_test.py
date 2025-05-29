#!/usr/bin/env python3
# coding=utf-8

"""
Advanced Controller Detection and Test Script
Works with USB, Bluetooth, and various input methods
"""

import pygame
import sys
import time
import subprocess
import os

def check_evdev_devices():
    """Check for input devices using evdev"""
    try:
        import evdev
        devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
        
        print("=== Input Devices (evdev) ===")
        for device in devices:
            print(f"Device: {device.path}")
            print(f"  Name: {device.name}")
            print(f"  Phys: {device.phys}")
            
            # Check if it's a game controller
            caps = device.capabilities()
            if evdev.ecodes.EV_ABS in caps:  # Has analog inputs
                abs_events = caps[evdev.ecodes.EV_ABS]
                if any(code in abs_events for code in [evdev.ecodes.ABS_X, evdev.ecodes.ABS_Y]):
                    print(f"  -> Looks like a game controller!")
                    return device
            print()
        
        return None
    except ImportError:
        print("evdev not available")
        return None

def test_evdev_controller(device):
    """Test controller using evdev"""
    print(f"\nTesting controller with evdev: {device.name}")
    print("Move sticks and press buttons (Ctrl+C to exit)")
    print("-" * 50)
    
    try:
        for event in device.read_loop():
            if event.type == evdev.ecodes.EV_ABS:
                # Analog stick/trigger events
                if event.code in [evdev.ecodes.ABS_X, evdev.ecodes.ABS_Y]:
                    print(f"Left stick: X={event.value if event.code == evdev.ecodes.ABS_X else 'unchanged'}, Y={event.value if event.code == evdev.ecodes.ABS_Y else 'unchanged'}")
                elif event.code in [evdev.ecodes.ABS_RX, evdev.ecodes.ABS_RY]:
                    print(f"Right stick: X={event.value if event.code == evdev.ecodes.ABS_RX else 'unchanged'}, Y={event.value if event.code == evdev.ecodes.ABS_RY else 'unchanged'}")
                elif event.code in [evdev.ecodes.ABS_Z, evdev.ecodes.ABS_RZ]:
                    print(f"Triggers: L2={event.value if event.code == evdev.ecodes.ABS_Z else 'unchanged'}, R2={event.value if event.code == evdev.ecodes.ABS_RZ else 'unchanged'}")
            
            elif event.type == evdev.ecodes.EV_KEY:
                # Button events
                if event.value == 1:  # Button pressed
                    button_names = {
                        evdev.ecodes.BTN_SOUTH: "X (Cross)",
                        evdev.ecodes.BTN_EAST: "Circle", 
                        evdev.ecodes.BTN_WEST: "Square",
                        evdev.ecodes.BTN_NORTH: "Triangle",
                        evdev.ecodes.BTN_TL: "L1",
                        evdev.ecodes.BTN_TR: "R1",
                        evdev.ecodes.BTN_SELECT: "Share",
                        evdev.ecodes.BTN_START: "Options",
                        evdev.ecodes.BTN_MODE: "PS Button"
                    }
                    button_name = button_names.get(event.code, f"Button {event.code}")
                    print(f"Button pressed: {button_name}")
    
    except KeyboardInterrupt:
        print("\nController test ended")

def detect_pygame_controllers():
    """Detect controllers using pygame"""
    pygame.init()
    pygame.joystick.init()
    
    controller_count = pygame.joystick.get_count()
    print(f"=== Pygame Controllers ===")
    print(f"Found {controller_count} controller(s)")
    
    controllers = []
    for i in range(controller_count):
        controller = pygame.joystick.Joystick(i)
        controller.init()
        controllers.append(controller)
        print(f"Controller {i}: {controller.get_name()}")
        print(f"  - Axes: {controller.get_numaxes()}")
        print(f"  - Buttons: {controller.get_numbuttons()}")
        print(f"  - Hats: {controller.get_numhats()}")
    
    return controllers

def test_pygame_controller(controller):
    """Test controller using pygame"""
    print(f"\nTesting controller with pygame: {controller.get_name()}")
    print("Move sticks and press buttons (Press Start/Menu to exit)")
    print("-" * 50)
    
    clock = pygame.time.Clock()
    running = True
    
    while running:
        pygame.event.pump()
        
        # Check for exit conditions
        for event in pygame.event.get():
            if event.type == pygame.JOYBUTTONDOWN:
                if event.button in [7, 9, 10]:  # Start, Menu, or Guide buttons
                    print("Exit button pressed!")
                    running = False
        
        # Read controller state
        axes = []
        for i in range(controller.get_numaxes()):
            axes.append(round(controller.get_axis(i), 3))
        
        buttons = []
        for i in range(controller.get_numbuttons()):
            if controller.get_button(i):
                buttons.append(i)
        
        hats = []
        for i in range(controller.get_numhats()):
            hat = controller.get_hat(i)
            if hat != (0, 0):
                hats.append(f"Hat{i}: {hat}")
        
        # Print current state (only if something is active)
        if any(abs(axis) > 0.1 for axis in axes) or buttons or hats:
            print(f"Axes: {axes}")
            if buttons:
                print(f"Buttons pressed: {buttons}")
            if hats:
                print(f"Hats: {hats}")
            print("-" * 30)
        
        clock.tick(10)  # 10 FPS
    
    print("Controller test ended")

def check_bluetooth_status():
    """Check Bluetooth connection status"""
    print("=== Bluetooth Status ===")
    try:
        result = subprocess.run(['bluetoothctl', 'devices'], capture_output=True, text=True)
        if result.returncode == 0:
            print("Bluetooth devices:")
            print(result.stdout)
        
        # Check for connected devices
        result = subprocess.run(['bluetoothctl', 'info', '98:B6:E9:29:18:54'], capture_output=True, text=True)
        if result.returncode == 0 and 'Connected: yes' in result.stdout:
            print("PS4 Controller is connected via Bluetooth!")
        else:
            print("PS4 Controller not connected via Bluetooth")
    except Exception as e:
        print(f"Error checking Bluetooth: {e}")

def main():
    print("=== Advanced Game Controller Detection and Test ===")
    print()
    
    # Check Bluetooth status
    check_bluetooth_status()
    print()
    
    # Try evdev first (more reliable for Bluetooth controllers)
    evdev_device = check_evdev_devices()
    print()
    
    # Try pygame
    pygame_controllers = detect_pygame_controllers()
    print()
    
    # Test available controllers
    if evdev_device:
        print("Found controller via evdev - testing...")
        test_evdev_controller(evdev_device)
    elif pygame_controllers:
        print("Found controller via pygame - testing...")
        test_pygame_controller(pygame_controllers[0])
    else:
        print("No controllers found!")
        print()
        print("Troubleshooting:")
        print("1. For USB: Connect controller via USB cable")
        print("2. For Bluetooth: Make sure controller is paired and connected")
        print("3. Try: sudo ds4drv --hidraw (for PS4 controllers)")
        print("4. Check: ls -la /dev/input/")
        return False
    
    return True

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        pygame.quit() 