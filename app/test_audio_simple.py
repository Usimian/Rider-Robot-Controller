#!/usr/bin/env python3
# coding=utf-8

# Simple Audio Test for Rider Robot
# Basic speaker and microphone testing
# Marc Wester

import os
import sys
import time
import subprocess
import math
import wave
import struct

def generate_test_tone(filename="test_tone.wav", frequency=1000, duration=2, sample_rate=16000):
    """Generate a simple test tone for speaker testing"""
    print(f"🎵 Generating test tone: {frequency}Hz for {duration}s...")
    
    try:
        # Generate sine wave
        frames = []
        for i in range(int(duration * sample_rate)):
            # Generate sine wave sample
            sample = int(32767 * math.sin(2 * math.pi * frequency * i / sample_rate))
            # Pack as 16-bit signed integer
            frames.append(struct.pack('<h', sample))
        
        # Save as WAV file
        filepath = os.path.join("/tmp", filename)
        with wave.open(filepath, 'wb') as wf:
            wf.setnchannels(1)  # Mono
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(sample_rate)
            wf.writeframes(b''.join(frames))
        
        print(f"✅ Test tone saved to: {filepath}")
        return filepath
        
    except Exception as e:
        print(f"❌ Failed to generate test tone: {e}")
        return None

def test_speaker_basic():
    """Basic speaker test using system commands"""
    print("\n🔊 BASIC SPEAKER TEST")
    print("="*40)
    
    # Test 1: Generate and play test tone
    print("\n🎵 Test 1: Generated tone test")
    tone_file = generate_test_tone(frequency=800, duration=3)
    if tone_file:
        print("Playing test tone...")
        try:
            result = subprocess.run(f"aplay {tone_file}", shell=True, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print("✅ Test tone played successfully")
            else:
                print(f"❌ Test tone failed: {result.stderr}")
        except Exception as e:
            print(f"❌ Playback error: {e}")
    
    # Test 2: System beep
    print("\n🔔 Test 2: System beep test")
    try:
        subprocess.run("echo -e '\\a'", shell=True, timeout=5)
        print("✅ System beep command sent")
    except Exception as e:
        print(f"❌ System beep failed: {e}")
    
    # Test 3: Speaker test utility
    print("\n🎛️  Test 3: Speaker test utility")
    try:
        result = subprocess.run("timeout 3s speaker-test -t sine -f 1000 -l 1 -s 1", 
                              shell=True, capture_output=True, text=True, timeout=10)
        if result.returncode == 0 or result.returncode == 124:  # 124 is timeout exit code
            print("✅ Speaker test utility ran")
        else:
            print(f"⚠️  Speaker test utility: {result.stderr}")
    except Exception as e:
        print(f"❌ Speaker test utility error: {e}")

def test_microphone_basic():
    """Basic microphone test using system commands"""
    print("\n🎤 BASIC MICROPHONE TEST")
    print("="*40)
    
    # Test 1: Check if microphone device exists
    print("\n🔍 Test 1: Microphone device detection")
    try:
        result = subprocess.run("arecord -l", shell=True, capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✅ Audio recording devices found:")
            print(result.stdout)
        else:
            print("❌ No audio recording devices found")
    except Exception as e:
        print(f"❌ Device detection error: {e}")
    
    # Test 2: Quick recording test
    print("\n🎙️  Test 2: Quick recording test (3 seconds)")
    print("Please speak into the microphone...")
    
    test_file = "/tmp/mic_test.wav"
    try:
        # Record for 3 seconds
        cmd = f"timeout 3s arecord -f cd -t wav {test_file}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        
        if os.path.exists(test_file):
            file_size = os.path.getsize(test_file)
            print(f"✅ Recording created: {file_size} bytes")
            
            # Try to play it back
            print("Playing back recording...")
            playback = subprocess.run(f"aplay {test_file}", shell=True, capture_output=True, text=True, timeout=10)
            if playback.returncode == 0:
                print("✅ Playback successful")
            else:
                print(f"⚠️  Playback issue: {playback.stderr}")
        else:
            print("❌ No recording file created")
            
    except Exception as e:
        print(f"❌ Recording test error: {e}")

def test_audio_system():
    """Test overall audio system"""
    print("\n🎵 AUDIO SYSTEM INFORMATION")
    print("="*40)
    
    # Check ALSA configuration
    print("\n🔧 ALSA Configuration:")
    try:
        result = subprocess.run("cat /proc/asound/cards", shell=True, capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(result.stdout)
        else:
            print("❌ Could not read ALSA cards")
    except Exception as e:
        print(f"❌ ALSA check error: {e}")
    
    # Check audio mixer
    print("\n🎚️  Audio Mixer Levels:")
    try:
        result = subprocess.run("amixer", shell=True, capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            # Show just the important parts
            lines = result.stdout.split('\n')
            for line in lines:
                if 'Playback' in line or 'Capture' in line or 'Master' in line:
                    print(f"  {line.strip()}")
        else:
            print("❌ Could not read mixer settings")
    except Exception as e:
        print(f"❌ Mixer check error: {e}")

def interactive_test():
    """Simple interactive test"""
    print("\n🎮 INTERACTIVE AUDIO TEST")
    print("="*40)
    print("Commands:")
    print("  1 - Test speaker")
    print("  2 - Test microphone") 
    print("  3 - System info")
    print("  4 - Generate test tones")
    print("  q - Quit")
    
    while True:
        try:
            choice = input("\nEnter choice (1-4, q): ").strip().lower()
            
            if choice == 'q':
                print("👋 Goodbye!")
                break
            elif choice == '1':
                test_speaker_basic()
            elif choice == '2':
                test_microphone_basic()
            elif choice == '3':
                test_audio_system()
            elif choice == '4':
                print("\n🎵 Generating multiple test tones...")
                frequencies = [440, 800, 1000, 1500, 2000]
                for freq in frequencies:
                    tone_file = generate_test_tone(f"tone_{freq}hz.wav", freq, 1)
                    if tone_file:
                        print(f"Playing {freq}Hz tone...")
                        subprocess.run(f"aplay {tone_file}", shell=True, capture_output=True, timeout=5)
                        time.sleep(0.5)
            else:
                print("❌ Invalid choice. Please enter 1-4 or q.")
                
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

def main():
    """Main function"""
    print("🎵 SIMPLE AUDIO TESTER FOR RIDER ROBOT")
    print("="*50)
    
    if len(sys.argv) > 1 and sys.argv[1] == "interactive":
        interactive_test()
    else:
        # Run all basic tests
        test_audio_system()
        test_speaker_basic()
        test_microphone_basic()
        
        print("\n📊 BASIC AUDIO TEST COMPLETE")
        print("="*40)
        print("If you heard sounds and saw recording activity,")
        print("your audio system is likely working correctly.")
        print("\nFor interactive testing, run:")
        print("python3 test_audio_simple.py interactive")

if __name__ == "__main__":
    main() 