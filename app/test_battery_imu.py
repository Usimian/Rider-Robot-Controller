#!/usr/bin/env python3
# coding=utf-8

# Test script to diagnose battery and IMU reading issues
# This script tests the robot's ability to read battery and IMU data

import sys
import time
from xgo_toolkit import XGO

def test_battery_reading(robot):
    """Test battery reading methods"""
    print("\n" + "="*50)
    print("BATTERY READING TEST")
    print("="*50)
    
    # Test rider-specific battery method
    try:
        battery_level = robot.rider_read_battery()
        print(f"✅ rider_read_battery(): {battery_level}%")
        if battery_level is None or battery_level <= 0:
            print("   ⚠️  Warning: Battery reading returned invalid value")
        return battery_level
    except AttributeError:
        print("❌ rider_read_battery() method not available")
    except Exception as e:
        print(f"❌ rider_read_battery() failed: {e}")
    
    # Test standard battery method
    try:
        battery_level = robot.read_battery()
        print(f"✅ read_battery(): {battery_level}%")
        if battery_level is None or battery_level <= 0:
            print("   ⚠️  Warning: Battery reading returned invalid value")
        return battery_level
    except AttributeError:
        print("❌ read_battery() method not available")
    except Exception as e:
        print(f"❌ read_battery() failed: {e}")
    
    print("❌ No working battery reading method found")
    return None

def test_imu_reading(robot):
    """Test IMU reading methods"""
    print("\n" + "="*50)
    print("IMU READING TEST")
    print("="*50)
    
    imu_data = {}
    
    # Test rider-specific IMU methods
    try:
        roll = robot.rider_read_roll()
        print(f"✅ rider_read_roll(): {roll}°")
        imu_data['roll'] = roll
    except AttributeError:
        print("❌ rider_read_roll() method not available")
    except Exception as e:
        print(f"❌ rider_read_roll() failed: {e}")
    
    try:
        pitch = robot.rider_read_pitch()
        print(f"✅ rider_read_pitch(): {pitch}°")
        imu_data['pitch'] = pitch
    except AttributeError:
        print("❌ rider_read_pitch() method not available")
    except Exception as e:
        print(f"❌ rider_read_pitch() failed: {e}")
    
    try:
        yaw = robot.rider_read_yaw()
        print(f"✅ rider_read_yaw(): {yaw}°")
        imu_data['yaw'] = yaw
    except AttributeError:
        print("❌ rider_read_yaw() method not available")
    except Exception as e:
        print(f"❌ rider_read_yaw() failed: {e}")
    
    # Test standard IMU methods
    if not imu_data:
        print("\nTrying standard IMU methods...")
        
        try:
            roll = robot.read_roll()
            print(f"✅ read_roll(): {roll}°")
            imu_data['roll'] = roll
        except AttributeError:
            print("❌ read_roll() method not available")
        except Exception as e:
            print(f"❌ read_roll() failed: {e}")
        
        try:
            pitch = robot.read_pitch()
            print(f"✅ read_pitch(): {pitch}°")
            imu_data['pitch'] = pitch
        except AttributeError:
            print("❌ read_pitch() method not available")
        except Exception as e:
            print(f"❌ read_pitch() failed: {e}")
        
        try:
            yaw = robot.read_yaw()
            print(f"✅ read_yaw(): {yaw}°")
            imu_data['yaw'] = yaw
        except AttributeError:
            print("❌ read_yaw() method not available")
        except Exception as e:
            print(f"❌ read_yaw() failed: {e}")
    
    # Test combined IMU method
    try:
        imu_combined = robot.read_imu()
        print(f"✅ read_imu(): {imu_combined}")
        if isinstance(imu_combined, (list, tuple)) and len(imu_combined) >= 3:
            print(f"   Roll: {imu_combined[0]}, Pitch: {imu_combined[1]}, Yaw: {imu_combined[2]}")
    except AttributeError:
        print("❌ read_imu() method not available")
    except Exception as e:
        print(f"❌ read_imu() failed: {e}")
    
    return imu_data

def test_firmware_info(robot):
    """Test firmware and version reading"""
    print("\n" + "="*50)
    print("FIRMWARE INFO TEST")
    print("="*50)
    
    # Test rider-specific firmware method
    try:
        firmware = robot.rider_read_firmware()
        print(f"✅ rider_read_firmware(): {firmware}")
    except AttributeError:
        print("❌ rider_read_firmware() method not available")
    except Exception as e:
        print(f"❌ rider_read_firmware() failed: {e}")
    
    # Test standard firmware method
    try:
        firmware = robot.read_firmware()
        print(f"✅ read_firmware(): {firmware}")
    except AttributeError:
        print("❌ read_firmware() method not available")
    except Exception as e:
        print(f"❌ read_firmware() failed: {e}")
    
    # Test library version
    try:
        lib_version = robot.read_lib_version()
        print(f"✅ read_lib_version(): {lib_version}")
    except AttributeError:
        print("❌ read_lib_version() method not available")
    except Exception as e:
        print(f"❌ read_lib_version() failed: {e}")

def continuous_monitoring(robot, duration=30):
    """Continuously monitor battery and IMU for a specified duration"""
    print(f"\n" + "="*50)
    print(f"CONTINUOUS MONITORING ({duration} seconds)")
    print("="*50)
    print("Press Ctrl+C to stop early")
    
    start_time = time.time()
    
    try:
        while time.time() - start_time < duration:
            current_time = time.time() - start_time
            
            # Read battery
            try:
                battery = robot.rider_read_battery() if hasattr(robot, 'rider_read_battery') else robot.read_battery()
                battery_status = f"{battery}%" if battery is not None else "FAIL"
            except:
                battery_status = "ERROR"
            
            # Read IMU
            try:
                roll = robot.rider_read_roll() if hasattr(robot, 'rider_read_roll') else robot.read_roll()
                pitch = robot.rider_read_pitch() if hasattr(robot, 'rider_read_pitch') else robot.read_pitch()
                yaw = robot.rider_read_yaw() if hasattr(robot, 'rider_read_yaw') else robot.read_yaw()
                imu_status = f"R:{roll:.1f}° P:{pitch:.1f}° Y:{yaw:.1f}°"
            except:
                imu_status = "ERROR"
            
            print(f"[{current_time:6.1f}s] Battery: {battery_status:>6} | IMU: {imu_status}")
            
            time.sleep(1)  # Update every second
            
    except KeyboardInterrupt:
        print("\n⏹ Monitoring stopped by user")

def main():
    print("🤖 XGO-RIDER Battery & IMU Diagnostic Tool")
    print("==========================================")
    
    # Initialize robot
    try:
        print("🔌 Connecting to robot...")
        robot = XGO(port='/dev/ttyS0', version="xgorider")
        print("✅ Robot connected successfully!")
    except Exception as e:
        print(f"❌ Failed to connect to robot: {e}")
        print("   • Check robot is powered on")
        print("   • Check cable connection")
        print("   • Try power cycling the robot")
        sys.exit(1)
    
    # Run tests
    try:
        # Test firmware info first
        test_firmware_info(robot)
        
        # Test battery reading
        battery_level = test_battery_reading(robot)
        
        # Test IMU reading
        imu_data = test_imu_reading(robot)
        
        # Summary
        print("\n" + "="*50)
        print("DIAGNOSTIC SUMMARY")
        print("="*50)
        
        if battery_level is not None and battery_level > 0:
            print(f"✅ Battery reading: WORKING ({battery_level}%)")
        else:
            print("❌ Battery reading: FAILED")
        
        if imu_data:
            print(f"✅ IMU reading: WORKING ({len(imu_data)} sensors)")
            for sensor, value in imu_data.items():
                print(f"   {sensor}: {value}°")
        else:
            print("❌ IMU reading: FAILED")
        
        # Ask for continuous monitoring
        print("\n" + "="*50)
        response = input("Run continuous monitoring for 30 seconds? (y/N): ").strip().lower()
        if response in ['y', 'yes']:
            continuous_monitoring(robot, 30)
        
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
    finally:
        try:
            robot.rider_reset()
            print("✅ Robot reset complete")
        except:
            pass

if __name__ == "__main__":
    main() 