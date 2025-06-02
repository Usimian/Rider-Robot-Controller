#!/usr/bin/env python3
# coding=utf-8

# Test file for video streaming functionality
# This tests the rider_video.py module independently
# Marc Wester

import time
import sys
from rider_video import RiderVideo

def test_video_streaming():
    """Test video streaming functionality"""
    print("🎥 Testing Rider Video Streaming...")
    print("="*50)
    
    # Initialize video
    video = RiderVideo(camera_id=0, debug=True)
    
    if not video.is_camera_available():
        print("❌ No camera available for testing")
        print("   • Check camera is connected")
        print("   • Check camera permissions")
        print("   • Try: sudo usermod -a -G video $USER")
        return False
    
    print("✅ Camera detected!")
    
    # Start streaming
    if not video.start_streaming():
        print("❌ Failed to start video streaming")
        video.cleanup()
        return False
    
    print("✅ Video streaming started!")
    
    # Test frame capture for 10 seconds
    print("\n📹 Testing frame capture for 10 seconds...")
    start_time = time.time()
    frame_count = 0
    last_status_time = 0
    
    try:
        while time.time() - start_time < 10.0:
            current_time = time.time()
            
            # Get frame
            frame = video.get_current_frame()
            if frame:
                frame_count += 1
                
                # Show status every 2 seconds
                if current_time - last_status_time >= 2.0:
                    fps = frame_count / (current_time - start_time)
                    frame_size = frame.size
                    print(f"   📊 Frames captured: {frame_count}, FPS: {fps:.1f}, Size: {frame_size}")
                    last_status_time = current_time
            
            time.sleep(0.1)  # Check 10 times per second
            
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
    
    # Final statistics
    total_time = time.time() - start_time
    avg_fps = frame_count / total_time if total_time > 0 else 0
    
    print(f"\n📈 Final Results:")
    print(f"   • Total frames: {frame_count}")
    print(f"   • Total time: {total_time:.1f}s")
    print(f"   • Average FPS: {avg_fps:.1f}")
    
    # Cleanup
    video.cleanup()
    print("✅ Video test completed successfully!")
    return True

def test_video_integration():
    """Test video integration with screen"""
    print("\n🖥️  Testing Video + Screen Integration...")
    print("="*50)
    
    try:
        from rider_screen import RiderScreen
        
        # Test screen with video
        screen = RiderScreen(robot=None, debug=True)
        
        print("✅ Screen with video initialized!")
        
        # Test display updates
        print("📺 Testing display updates for 5 seconds...")
        for i in range(5):
            screen.refresh_and_update_display(True)  # Simulate controller connected
            time.sleep(1)
            print(f"   Update {i+1}/5 completed")
        
        # Cleanup
        screen.cleanup()
        print("✅ Screen integration test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Screen integration test failed: {e}")
        return False

if __name__ == "__main__":
    print("🤖 Rider Video System Test")
    print("="*60)
    
    success = True
    
    # Test 1: Video streaming
    if not test_video_streaming():
        success = False
    
    # Test 2: Screen integration
    if not test_video_integration():
        success = False
    
    print("\n" + "="*60)
    if success:
        print("🎉 ALL TESTS PASSED!")
        print("   Video system is ready for use")
    else:
        print("❌ SOME TESTS FAILED!")
        print("   Check error messages above")
        sys.exit(1) 