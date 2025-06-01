#!/usr/bin/env python3
# coding=utf-8

# Very basic camera test using direct OpenCV
# Displays camera feed on robot's LCD screen
# Marc Wester

import cv2 as cv
import time
import sys
from PIL import Image
import xgoscreen.LCD_2inch as LCD_2inch
from key import Button

def test_camera_direct():
    """Direct OpenCV camera test"""
    
    print("🎥 Testing camera with direct OpenCV...")
    
    # Initialize LCD display
    try:
        display = LCD_2inch.LCD_2inch()
        display.Init()
        display.clear()
        print("✅ LCD display ready")
    except Exception as e:
        print(f"❌ LCD display error: {e}")
        return False
    
    # Initialize camera directly with OpenCV
    try:
        cap = cv.VideoCapture(0)  # Try camera 0
        if not cap.isOpened():
            print("❌ Failed to open camera 0, trying camera 1...")
            cap = cv.VideoCapture(1)
            if not cap.isOpened():
                print("❌ No camera found on ports 0 or 1")
                return False
        
        # Set camera properties
        cap.set(cv.CAP_PROP_FRAME_WIDTH, 320)
        cap.set(cv.CAP_PROP_FRAME_HEIGHT, 240)
        cap.set(cv.CAP_PROP_FOURCC, cv.VideoWriter.fourcc('M', 'J', 'P', 'G'))
        
        print("✅ Camera opened successfully")
        print(f"   Resolution: {int(cap.get(cv.CAP_PROP_FRAME_WIDTH))}x{int(cap.get(cv.CAP_PROP_FRAME_HEIGHT))}")
        
    except Exception as e:
        print(f"❌ Camera setup error: {e}")
        return False
    
    # Initialize button for exit
    button = Button()
    
    print("📹 Starting live camera feed...")
    print("   Press robot button B to exit, or Ctrl+C")
    
    frame_count = 0
    start_time = time.time()
    
    try:
        while True:
            # Capture frame
            ret, frame = cap.read()
            
            if not ret:
                print("❌ Failed to read frame")
                break
            
            frame_count += 1
            
            # Add simple overlay
            timestamp = time.strftime("%H:%M:%S")
            cv.putText(frame, f"Time: {timestamp}", (5, 20), 
                       cv.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            cv.putText(frame, f"Frame: {frame_count}", (5, 40), 
                       cv.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
            
            # Calculate FPS every 30 frames
            if frame_count % 30 == 0:
                elapsed = time.time() - start_time
                fps = 30 / elapsed
                print(f"📊 FPS: {fps:.1f}")
                start_time = time.time()
            
            # Convert BGR to RGB for PIL/LCD display
            frame_rgb = cv.cvtColor(frame, cv.COLOR_BGR2RGB)
            
            # Convert to PIL and display
            pil_img = Image.fromarray(frame_rgb)
            display.ShowImage(pil_img)
            
            # Check exit condition
            if button.press_b():
                print("🛑 Exit button pressed")
                break
            
            # Control frame rate
            time.sleep(0.03)  # ~33 FPS max
            
    except KeyboardInterrupt:
        print("\n🛑 Stopped by user")
    except Exception as e:
        print(f"❌ Camera loop error: {e}")
    finally:
        # Cleanup
        print("🧹 Cleaning up...")
        try:
            cap.release()
            display.clear()
            print("✅ Cleanup done")
        except Exception as e:
            print(f"⚠️  Cleanup error: {e}")
    
    return True

def test_camera_photo():
    """Simple photo capture test"""
    
    print("📸 Testing photo capture...")
    
    try:
        # Open camera
        cap = cv.VideoCapture(0)
        if not cap.isOpened():
            cap = cv.VideoCapture(1)
            if not cap.isOpened():
                print("❌ No camera available")
                return False
        
        # Set high resolution for photo
        cap.set(cv.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv.CAP_PROP_FRAME_HEIGHT, 480)
        
        print("✅ Camera ready for photo")
        print("📸 Capturing photo in 3 seconds...")
        
        # Warm up camera
        for i in range(10):
            ret, frame = cap.read()
            time.sleep(0.1)
        
        # Wait countdown
        for i in range(3, 0, -1):
            print(f"   {i}...")
            time.sleep(1)
        
        # Capture photo
        ret, frame = cap.read()
        
        if ret:
            # Add timestamp
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            cv.putText(frame, timestamp, (10, 30), 
                       cv.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            
            # Save with timestamp filename
            filename = f"camera_test_{time.strftime('%Y%m%d_%H%M%S')}.jpg"
            cv.imwrite(filename, frame)
            
            print(f"✅ Photo saved: {filename}")
            print(f"   Size: {frame.shape[1]}x{frame.shape[0]} pixels")
            
        else:
            print("❌ Failed to capture photo")
            return False
        
        cap.release()
        return True
        
    except Exception as e:
        print(f"❌ Photo capture error: {e}")
        return False

def main():
    print("=" * 60)
    print("🎥 BASIC CAMERA TEST")
    print("=" * 60)
    
    # Check arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "photo":
            success = test_camera_photo()
        elif sys.argv[1] == "live":
            success = test_camera_direct()
        else:
            print("❌ Unknown option. Use 'photo' or 'live'")
            success = False
    else:
        print("📋 Available tests:")
        print("   python test_camera_basic.py live  - Live camera feed on LCD")
        print("   python test_camera_basic.py photo - Capture single photo")
        print()
        print("🎯 Running live camera test by default...")
        success = test_camera_direct()
    
    if success:
        print("\n✅ Camera test completed successfully!")
    else:
        print("\n❌ Camera test failed!")
    
    print("=" * 60)

if __name__ == "__main__":
    main() 