#!/usr/bin/env python3
"""
Robot Serial Port Helper
Automatically detects the correct serial port for XGO robot communication
"""

import os
import glob

def get_robot_serial_port():
    """
    Automatically detect the correct serial port for the robot.
    Returns the first available port from the priority list.
    """
    # Priority order: ttyAMA0 (preferred), ttyS0 (fallback), other ttyS ports
    possible_ports = [
        '/dev/ttyAMA0',
        '/dev/ttyS0',
        '/dev/ttyS1',
        '/dev/ttyS2'
    ]
    
    # Also check for any other ttyS* ports
    tty_ports = glob.glob('/dev/ttyS*')
    for port in tty_ports:
        if port not in possible_ports:
            possible_ports.append(port)
    
    # Return the first port that exists
    for port in possible_ports:
        if os.path.exists(port):
            return port
    
    raise RuntimeError("No suitable serial port found for robot communication")

def create_ttyama0_link():
    """
    Create ttyAMA0 symbolic link if it doesn't exist and ttyS0 does
    """
    if not os.path.exists('/dev/ttyAMA0') and os.path.exists('/dev/ttyS0'):
        try:
            os.symlink('/dev/ttyS0', '/dev/ttyAMA0')
            print("Created /dev/ttyAMA0 -> /dev/ttyS0 symbolic link")
            return True
        except (PermissionError, OSError) as e:
            print(f"Could not create symbolic link: {e}")
            return False
    return os.path.exists('/dev/ttyAMA0')

if __name__ == "__main__":
    # Test the functions
    print("Testing robot serial port detection...")
    try:
        port = get_robot_serial_port()
        print(f"✓ Found robot serial port: {port}")
    except RuntimeError as e:
        print(f"❌ {e}")
    
    print("\nTesting ttyAMA0 link creation...")
    if create_ttyama0_link():
        print("✓ /dev/ttyAMA0 is available")
    else:
        print("❌ /dev/ttyAMA0 not available") 