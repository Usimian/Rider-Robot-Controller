#!/usr/bin/env python3
"""
Voice recognition service for XGO Rider robot
Uses Vosk for local speech-to-text recognition
"""

import json
import queue
import sys
import os
import time
import pyaudio
import vosk
import paho.mqtt.client as mqtt
from typing import Optional

# Configuration
VOSK_MODEL_PATH = "/home/pi/model/vosk-model-small-en-us-0.15"
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC_VOICE = "rider/voice/recognized"
HARDWARE_SAMPLE_RATE = 44100  # wm8960 hardware rate
VOSK_SAMPLE_RATE = 16000      # Vosk required rate
CHANNELS = 2                   # wm8960 requires stereo (Vosk will use 1 channel)
CHUNK_SIZE = 4000

# Audio input device (wm8960 soundcard)
AUDIO_DEVICE_INDEX = None  # Will auto-detect


class VoiceListener:
    def __init__(self):
        self.model = None
        self.recognizer = None
        self.mqtt_client = None
        self.audio_queue = queue.Queue()
        self.running = False
        
    def initialize(self):
        """Initialize Vosk model and MQTT connection"""
        print("[Voice] Initializing voice recognition service...")
        
        # Check if model exists
        if not os.path.exists(VOSK_MODEL_PATH):
            print(f"[Voice] ERROR: Vosk model not found at {VOSK_MODEL_PATH}")
            print("[Voice] Please download the model first:")
            print("  wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip")
            print("  unzip vosk-model-small-en-us-0.15.zip -d /home/pi/model/")
            return False
        
        # Load Vosk model
        print(f"[Voice] Loading Vosk model from {VOSK_MODEL_PATH}...")
        self.model = vosk.Model(VOSK_MODEL_PATH)
        # Use hardware sample rate (44100) - Vosk will handle it
        self.recognizer = vosk.KaldiRecognizer(self.model, HARDWARE_SAMPLE_RATE)
        self.recognizer.SetWords(True)
        print("[Voice] Model loaded successfully")
        
        # Initialize MQTT
        print("[Voice] Connecting to MQTT broker...")
        self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.mqtt_client.on_connect = self._on_mqtt_connect
        try:
            self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.mqtt_client.loop_start()
        except Exception as e:
            print(f"[Voice] ERROR: Failed to connect to MQTT: {e}")
            return False
        
        print("[Voice] Initialization complete")
        return True
    
    def _on_mqtt_connect(self, client, userdata, flags, rc, properties=None):
        """MQTT connection callback"""
        if rc == 0:
            print("[Voice] Connected to MQTT broker")
        else:
            print(f"[Voice] Failed to connect to MQTT, return code {rc}")
    
    def find_audio_device(self):
        """Find the wm8960 audio input device"""
        p = pyaudio.PyAudio()
        info = p.get_host_api_info_by_index(0)
        numdevices = info.get('deviceCount')
        
        print("[Voice] Available audio input devices:")
        for i in range(0, numdevices):
            device_info = p.get_device_info_by_host_api_device_index(0, i)
            if device_info.get('maxInputChannels') > 0:
                print(f"  [{i}] {device_info.get('name')}")
                if 'wm8960' in device_info.get('name').lower():
                    print(f"[Voice] Using device: {device_info.get('name')}")
                    p.terminate()
                    return i
        
        p.terminate()
        print("[Voice] Using default input device")
        return None
    
    def publish_recognition(self, text: str):
        """Publish recognized text to MQTT"""
        if not text or text.strip() == "":
            return

        # Filter out noise: require at least 2 words and minimum 5 characters
        words = text.strip().split()
        if len(words) < 2 or len(text.strip()) < 5:
            print(f"[Voice] Filtered noise: '{text}' (too short)")
            return

        # Filter out common noise words that appear alone
        noise_phrases = ['uh', 'um', 'ah', 'huh', 'the the', 'a a']
        if text.strip().lower() in noise_phrases:
            print(f"[Voice] Filtered noise phrase: '{text}'")
            return

        message = {
            'text': text,
            'timestamp': time.time()
        }
        
        try:
            self.mqtt_client.publish(MQTT_TOPIC_VOICE, json.dumps(message))
            print(f"[Voice] Recognized: '{text}'")
        except Exception as e:
            print(f"[Voice] ERROR: Failed to publish to MQTT: {e}")
    
    def audio_callback(self, in_data, frame_count, time_info, status):
        """PyAudio callback for audio stream"""
        self.audio_queue.put(bytes(in_data))
        return (None, pyaudio.paContinue)
    
    def start_listening(self):
        """Start listening to microphone and recognizing speech"""
        print("[Voice] Starting voice recognition...")
        print("[Voice] Listening... Speak into the robot's microphone")
        
        device_index = self.find_audio_device()
        
        p = pyaudio.PyAudio()
        
        try:
            stream = p.open(
                format=pyaudio.paInt16,
                channels=CHANNELS,
                rate=HARDWARE_SAMPLE_RATE,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=CHUNK_SIZE,
                stream_callback=self.audio_callback
            )
            
            stream.start_stream()
            self.running = True
            
            print("[Voice] Recognition active - speak now!")
            
            while self.running:
                try:
                    data = self.audio_queue.get(timeout=1)
                except queue.Empty:
                    continue
                
                if self.recognizer.AcceptWaveform(data):
                    # Final result (end of speech)
                    result = json.loads(self.recognizer.Result())
                    text = result.get('text', '').strip()
                    if text:
                        self.publish_recognition(text)
                else:
                    # Partial result (ongoing speech)
                    partial = json.loads(self.recognizer.PartialResult())
                    partial_text = partial.get('partial', '').strip()
                    if partial_text:
                        print(f"[Voice] Hearing: {partial_text}", end='\r')
            
            stream.stop_stream()
            stream.close()
            
        except Exception as e:
            print(f"[Voice] ERROR: Audio stream error: {e}")
        finally:
            p.terminate()
    
    def stop(self):
        """Stop the voice listener"""
        print("[Voice] Stopping voice recognition...")
        self.running = False
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()


def main():
    listener = VoiceListener()
    
    if not listener.initialize():
        print("[Voice] Initialization failed, exiting")
        return 1
    
    try:
        listener.start_listening()
    except KeyboardInterrupt:
        print("\n[Voice] Interrupted by user")
    except Exception as e:
        print(f"[Voice] ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        listener.stop()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
