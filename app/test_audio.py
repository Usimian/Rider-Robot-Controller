#!/usr/bin/env python3
# coding=utf-8

# Audio Test Routine for Rider Robot
# Tests both speaker and microphone functionality
# Marc Wester

import os
import sys
import time
import wave
import numpy as np
import pyaudio
from threading import Thread
import subprocess
import tempfile
from xgo_toolkit import XGO
from rider_screen import RiderScreen
from key import Button

class AudioTester:
    def __init__(self, robot=None, debug=False):
        self.__debug = debug
        self.__robot = robot
        self.__running = False
        
        # Audio settings
        self.__sample_rate = 16000
        self.__channels = 1
        self.__chunk_size = 1024
        self.__format = pyaudio.paInt16
        
        # Initialize PyAudio
        self.__audio = pyaudio.PyAudio()
        
        # Initialize screen if available
        self.__screen = None
        try:
            self.__screen = RiderScreen(robot=self.__robot, debug=self.__debug)
            print("✅ LCD screen initialized for audio testing")
        except Exception as e:
            print(f"⚠️  LCD screen not available: {e}")
        
        # Initialize button reader
        self.__button = Button()
        
        # Test results
        self.__test_results = {
            'microphone_detected': False,
            'speaker_working': False,
            'audio_levels_good': False,
            'recording_quality': 'unknown',
            'playback_quality': 'unknown'
        }
        
        if self.__debug:
            print("AudioTester initialized")
    
    def __update_screen_status(self, message, color_type="info"):
        """Update screen with current test status"""
        if self.__screen:
            try:
                # You could extend RiderScreen to show custom messages
                # For now, just refresh the display
                self.__screen.refresh_and_update_display()
            except Exception as e:
                if self.__debug:
                    print(f"Screen update error: {e}")
    
    def list_audio_devices(self):
        """List all available audio devices"""
        print("\n" + "="*60)
        print("AUDIO DEVICES DETECTED")
        print("="*60)
        
        device_count = self.__audio.get_device_count()
        input_devices = []
        output_devices = []
        
        for i in range(device_count):
            device_info = self.__audio.get_device_info_by_index(i)
            
            print(f"\nDevice {i}: {device_info['name']}")
            print(f"  Max Input Channels: {device_info['maxInputChannels']}")
            print(f"  Max Output Channels: {device_info['maxOutputChannels']}")
            print(f"  Default Sample Rate: {device_info['defaultSampleRate']}")
            
            if int(device_info['maxInputChannels']) > 0:
                input_devices.append(i)
            if int(device_info['maxOutputChannels']) > 0:
                output_devices.append(i)
        
        print(f"\n📱 Input devices (microphones): {input_devices}")
        print(f"🔊 Output devices (speakers): {output_devices}")
        print("="*60)
        
        return input_devices, output_devices
    
    def test_microphone_detection(self):
        """Test if microphone is detected and accessible"""
        print("\n🎤 TESTING MICROPHONE DETECTION...")
        
        try:
            input_devices, _ = self.list_audio_devices()
            
            if not input_devices:
                print("❌ No microphone devices detected!")
                self.__test_results['microphone_detected'] = False
                return False
            
            # Try to open the default input device
            test_device = input_devices[0]
            stream = self.__audio.open(
                format=self.__format,
                channels=self.__channels,
                rate=self.__sample_rate,
                input=True,
                input_device_index=test_device,
                frames_per_buffer=self.__chunk_size
            )
            
            print(f"✅ Microphone detected and accessible (Device {test_device})")
            stream.close()
            self.__test_results['microphone_detected'] = True
            return True
            
        except Exception as e:
            print(f"❌ Microphone test failed: {e}")
            self.__test_results['microphone_detected'] = False
            return False
    
    def test_microphone_levels(self, duration=5):
        """Test microphone input levels"""
        print(f"\n🎤 TESTING MICROPHONE LEVELS ({duration} seconds)...")
        print("Please speak into the microphone or make some noise...")
        
        try:
            stream = self.__audio.open(
                format=self.__format,
                channels=self.__channels,
                rate=self.__sample_rate,
                input=True,
                frames_per_buffer=self.__chunk_size
            )
            
            max_level = 0
            avg_levels = []
            
            for i in range(int(self.__sample_rate / self.__chunk_size * duration)):
                data = stream.read(self.__chunk_size, exception_on_overflow=False)
                audio_data = np.frombuffer(data, dtype=np.int16)
                
                # Calculate RMS level
                rms = np.sqrt(np.mean(audio_data**2))
                max_level = max(max_level, rms)
                avg_levels.append(rms)
                
                # Show progress
                if i % 10 == 0:  # Update every ~0.2 seconds
                    level_bar = "█" * int(rms / 1000) + "░" * (20 - int(rms / 1000))
                    print(f"\rLevel: [{level_bar}] RMS: {rms:6.0f}", end="", flush=True)
            
            stream.close()
            print()  # New line after progress bar
            
            avg_level = np.mean(avg_levels)
            
            print(f"📊 Audio Level Results:")
            print(f"   Maximum Level: {max_level:.0f}")
            print(f"   Average Level: {avg_level:.0f}")
            
            # Evaluate levels
            if max_level < 100:
                print("❌ Audio levels too low - check microphone connection")
                self.__test_results['audio_levels_good'] = False
                return False
            elif max_level > 20000:
                print("⚠️  Audio levels very high - may cause distortion")
                self.__test_results['audio_levels_good'] = True
                return True
            else:
                print("✅ Audio levels are good")
                self.__test_results['audio_levels_good'] = True
                return True
                
        except Exception as e:
            print(f"❌ Microphone level test failed: {e}")
            self.__test_results['audio_levels_good'] = False
            return False
    
    def record_test_audio(self, duration=3, filename="test_recording.wav"):
        """Record a test audio sample"""
        print(f"\n🎤 RECORDING TEST AUDIO ({duration} seconds)...")
        print("Please speak clearly into the microphone...")
        
        try:
            stream = self.__audio.open(
                format=self.__format,
                channels=self.__channels,
                rate=self.__sample_rate,
                input=True,
                frames_per_buffer=self.__chunk_size
            )
            
            frames = []
            
            for i in range(int(self.__sample_rate / self.__chunk_size * duration)):
                data = stream.read(self.__chunk_size, exception_on_overflow=False)
                frames.append(data)
                
                # Show countdown
                remaining = duration - (i * self.__chunk_size / self.__sample_rate)
                print(f"\rRecording... {remaining:.1f}s remaining", end="", flush=True)
            
            stream.close()
            print("\n✅ Recording complete!")
            
            # Save the recording
            filepath = os.path.join("/tmp", filename)
            wf = wave.open(filepath, 'wb')
            wf.setnchannels(self.__channels)
            wf.setsampwidth(self.__audio.get_sample_size(self.__format))
            wf.setframerate(self.__sample_rate)
            wf.writeframes(b''.join(frames))
            wf.close()
            
            print(f"📁 Recording saved to: {filepath}")
            
            # Analyze recording quality
            audio_data = np.frombuffer(b''.join(frames), dtype=np.int16)
            rms = np.sqrt(np.mean(audio_data**2))
            
            if rms > 1000:
                self.__test_results['recording_quality'] = 'good'
                print("✅ Recording quality: Good")
            elif rms > 500:
                self.__test_results['recording_quality'] = 'fair'
                print("⚠️  Recording quality: Fair")
            else:
                self.__test_results['recording_quality'] = 'poor'
                print("❌ Recording quality: Poor")
            
            return filepath
            
        except Exception as e:
            print(f"❌ Recording failed: {e}")
            self.__test_results['recording_quality'] = 'failed'
            return None
    
    def test_speaker_system_sounds(self):
        """Test speaker using system sounds"""
        print("\n🔊 TESTING SPEAKER WITH SYSTEM SOUNDS...")
        
        # Test with different methods
        test_sounds = [
            ("System beep", "speaker-test -t sine -f 1000 -l 1 -s 1"),
            ("ALSA test", "aplay /usr/share/sounds/alsa/Front_Left.wav"),
            ("Simple tone", "timeout 2s speaker-test -t sine -f 800 -c 2")
        ]
        
        for test_name, command in test_sounds:
            print(f"\n🔊 Testing: {test_name}")
            print(f"Command: {command}")
            
            try:
                result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    print(f"✅ {test_name} - Command executed successfully")
                    self.__test_results['speaker_working'] = True
                else:
                    print(f"⚠️  {test_name} - Command failed (exit code: {result.returncode})")
                    if result.stderr:
                        print(f"   Error: {result.stderr.strip()}")
                
            except subprocess.TimeoutExpired:
                print(f"⏰ {test_name} - Command timed out")
            except Exception as e:
                print(f"❌ {test_name} - Error: {e}")
            
            # Wait between tests
            time.sleep(1)
    
    def test_speaker_playback(self, audio_file=None):
        """Test speaker by playing back recorded audio"""
        if audio_file is None:
            print("\n🔊 No audio file provided for playback test")
            return False
        
        print(f"\n🔊 TESTING SPEAKER PLAYBACK...")
        print(f"Playing back: {audio_file}")
        
        try:
            # Use aplay command (standard on Raspberry Pi)
            command = f"aplay {audio_file}"
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                print("✅ Playback completed successfully")
                self.__test_results['speaker_working'] = True
                self.__test_results['playback_quality'] = 'good'
                return True
            else:
                print(f"❌ Playback failed (exit code: {result.returncode})")
                if result.stderr:
                    print(f"   Error: {result.stderr.strip()}")
                self.__test_results['playback_quality'] = 'failed'
                return False
                
        except subprocess.TimeoutExpired:
            print("⏰ Playback timed out")
            self.__test_results['playback_quality'] = 'timeout'
            return False
        except Exception as e:
            print(f"❌ Playback error: {e}")
            self.__test_results['playback_quality'] = 'error'
            return False
    
    def test_xgo_speaker(self):
        """Test XGO robot speaker functions if available"""
        print("\n🤖 TESTING XGO ROBOT SPEAKER...")
        
        if self.__robot is None:
            print("❌ No robot connection available")
            return False
        
        # Test different XGO speaker sounds
        xgo_sounds = [
            "like", "happy", "sad", "angry", "surprise", 
            "sleepy", "naughty", "apologize"
        ]
        
        for sound in xgo_sounds:
            try:
                print(f"🔊 Testing XGO sound: {sound}")
                
                # Try different XGO speaker methods
                if hasattr(self.__robot, 'xgoSpeaker'):
                    self.__robot.xgoSpeaker(sound)
                elif hasattr(self.__robot, 'rider_speaker'):
                    self.__robot.rider_speaker(sound)
                else:
                    print("⚠️  XGO speaker method not found")
                    return False
                
                print(f"✅ XGO sound '{sound}' played")
                time.sleep(2)  # Wait between sounds
                
            except Exception as e:
                print(f"❌ XGO sound '{sound}' failed: {e}")
        
        print("✅ XGO speaker test completed")
        return True
    
    def interactive_test(self):
        """Interactive test allowing user to control tests"""
        print("\n🎮 INTERACTIVE AUDIO TEST")
        print("Use robot buttons to control tests:")
        print("  A button (lower right): Exit")
        print("  B button (lower left): Record & playback test")
        print("  C button (upper left): Microphone level test")
        print("  D button (upper right): Speaker test")
        
        self.__running = True
        
        while self.__running:
            try:
                if self.__button.press_a():
                    print("🛑 Exit button pressed")
                    self.__running = False
                    break
                
                elif self.__button.press_b():
                    print("🎤 Record & Playback test...")
                    audio_file = self.record_test_audio(duration=3)
                    if audio_file:
                        time.sleep(1)
                        self.test_speaker_playback(audio_file)
                
                elif self.__button.press_c():
                    print("🎤 Microphone level test...")
                    self.test_microphone_levels(duration=5)
                
                elif self.__button.press_d():
                    print("🔊 Speaker test...")
                    self.test_speaker_system_sounds()
                
                time.sleep(0.1)  # Small delay to prevent excessive CPU usage
                
            except KeyboardInterrupt:
                print("\n🛑 Interactive test interrupted")
                self.__running = False
                break
    
    def run_full_test_suite(self):
        """Run the complete audio test suite"""
        print("\n" + "="*60)
        print("RIDER ROBOT AUDIO TEST SUITE")
        print("="*60)
        
        # Update screen
        self.__update_screen_status("Running audio tests...")
        
        # Test 1: Device detection
        print("\n📋 TEST 1: Audio Device Detection")
        self.list_audio_devices()
        
        # Test 2: Microphone detection
        print("\n📋 TEST 2: Microphone Detection")
        mic_detected = self.test_microphone_detection()
        
        # Test 3: Microphone levels (only if detected)
        if mic_detected:
            print("\n📋 TEST 3: Microphone Level Test")
            self.test_microphone_levels(duration=3)
            
            # Test 4: Recording test
            print("\n📋 TEST 4: Audio Recording Test")
            audio_file = self.record_test_audio(duration=3)
        else:
            audio_file = None
        
        # Test 5: Speaker system sounds
        print("\n📋 TEST 5: Speaker System Sounds")
        self.test_speaker_system_sounds()
        
        # Test 6: Playback test (only if we have a recording)
        if audio_file:
            print("\n📋 TEST 6: Audio Playback Test")
            self.test_speaker_playback(audio_file)
        
        # Test 7: XGO speaker test (only if robot available)
        if self.__robot:
            print("\n📋 TEST 7: XGO Robot Speaker Test")
            self.test_xgo_speaker()
        
        # Print results summary
        self.print_test_results()
        
        return self.__test_results
    
    def print_test_results(self):
        """Print a summary of all test results"""
        print("\n" + "="*60)
        print("AUDIO TEST RESULTS SUMMARY")
        print("="*60)
        
        results = self.__test_results
        
        # Microphone results
        print("🎤 MICROPHONE:")
        print(f"   Detection: {'✅ PASS' if results['microphone_detected'] else '❌ FAIL'}")
        print(f"   Audio Levels: {'✅ GOOD' if results['audio_levels_good'] else '❌ POOR'}")
        print(f"   Recording Quality: {results['recording_quality'].upper()}")
        
        # Speaker results
        print("\n🔊 SPEAKER:")
        print(f"   System Sounds: {'✅ WORKING' if results['speaker_working'] else '❌ NOT WORKING'}")
        print(f"   Playback Quality: {results['playback_quality'].upper()}")
        
        # Overall assessment
        print("\n📊 OVERALL ASSESSMENT:")
        mic_ok = results['microphone_detected'] and results['audio_levels_good']
        speaker_ok = results['speaker_working']
        
        if mic_ok and speaker_ok:
            print("✅ AUDIO SYSTEM: FULLY FUNCTIONAL")
        elif mic_ok:
            print("⚠️  AUDIO SYSTEM: MICROPHONE OK, SPEAKER ISSUES")
        elif speaker_ok:
            print("⚠️  AUDIO SYSTEM: SPEAKER OK, MICROPHONE ISSUES")
        else:
            print("❌ AUDIO SYSTEM: MAJOR ISSUES DETECTED")
        
        print("="*60)
    
    def cleanup(self):
        """Clean up resources"""
        self.__running = False
        
        try:
            self.__audio.terminate()
        except:
            pass
        
        if self.__screen:
            try:
                self.__screen.cleanup()
            except:
                pass
        
        print("🧹 Audio tester cleanup complete")


def main():
    """Main function to run audio tests"""
    debug_mode = False
    if len(sys.argv) > 1 and sys.argv[1] == "debug":
        debug_mode = True
    
    print("🤖 Initializing XGO-RIDER robot...")
    robot = None
    try:
        robot = XGO(port='/dev/ttyS0', version="xgorider")
        print("✅ Robot connected successfully!")
    except Exception as e:
        print(f"⚠️  Robot connection failed: {e}")
        print("   Continuing with audio tests only...")
    
    print("🎵 Initializing audio tester...")
    tester = AudioTester(robot=robot, debug=debug_mode)
    
    try:
        if len(sys.argv) > 1 and sys.argv[-1] == "interactive":
            # Interactive mode
            tester.interactive_test()
        else:
            # Full test suite
            tester.run_full_test_suite()
            
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
    except Exception as e:
        print(f"❌ Test error: {e}")
    finally:
        print("\n🧹 Cleaning up...")
        tester.cleanup()
        if robot:
            try:
                robot.rider_reset()
            except:
                pass
        print("✅ Cleanup complete!")


if __name__ == "__main__":
    main() 