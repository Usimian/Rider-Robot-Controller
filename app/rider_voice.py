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
import struct
import threading
import subprocess
import pyaudio
import vosk
import paho.mqtt.client as mqtt
from typing import Optional

# Configuration
VOSK_MODEL_PATH = "/home/pi/model/vosk-model-small-en-us-0.15"
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC_VOICE = "rider/voice/recognized"
MQTT_TOPIC_SPEAK = "rider/voice/speak"
MQTT_TOPIC_STOP  = "rider/voice/stop"
MQTT_TOPIC_STATUS = "rider/voice/status"
HARDWARE_SAMPLE_RATE = 44100  # wm8960 hardware rate
CHANNELS = 2                   # wm8960 requires stereo (Vosk will use 1 channel)
CHUNK_SIZE = 4000


class VoiceListener:
    def __init__(self):
        self.model = None
        self.recognizer = None
        self.mqtt_client = None
        self.audio_queue = queue.Queue()
        self.running = False

        # TTS coordination: set event to pause recording and speak
        self.tts_event = threading.Event()
        self.tts_text = ""
        self._tts_proc = None   # active aplay process (so we can kill it)

    def initialize(self):
        """Initialize Vosk model and MQTT connection"""
        print("[Voice] Initializing voice recognition service...")

        if not os.path.exists(VOSK_MODEL_PATH):
            print(f"[Voice] ERROR: Vosk model not found at {VOSK_MODEL_PATH}")
            return False

        print(f"[Voice] Loading Vosk model from {VOSK_MODEL_PATH}...")
        self.model = vosk.Model(VOSK_MODEL_PATH)
        self.recognizer = vosk.KaldiRecognizer(self.model, HARDWARE_SAMPLE_RATE)
        self.recognizer.SetWords(True)
        print("[Voice] Model loaded successfully")

        print("[Voice] Connecting to MQTT broker...")
        self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.mqtt_client.on_connect = self._on_mqtt_connect
        self.mqtt_client.on_message = self._on_mqtt_message
        try:
            self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.mqtt_client.loop_start()
        except Exception as e:
            print(f"[Voice] ERROR: Failed to connect to MQTT: {e}")
            return False

        print("[Voice] Initialization complete")
        return True

    def _on_mqtt_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            print("[Voice] Connected to MQTT broker")
            client.subscribe(MQTT_TOPIC_SPEAK)
            client.subscribe(MQTT_TOPIC_STOP)
            print(f"[Voice] Subscribed to {MQTT_TOPIC_SPEAK} and {MQTT_TOPIC_STOP}")
        else:
            print(f"[Voice] Failed to connect to MQTT, return code {rc}")

    def _on_mqtt_message(self, client, userdata, msg):
        """Handle incoming MQTT messages (TTS requests and stop)"""
        try:
            if msg.topic == MQTT_TOPIC_SPEAK:
                payload = json.loads(msg.payload.decode())
                text = payload.get('text', '').strip()
                if text:
                    print(f"[Voice] TTS requested: '{text}'")
                    self.speak(text)
            elif msg.topic == MQTT_TOPIC_STOP:
                print("[Voice] Stop TTS received")
                self.stop_tts()
        except Exception as e:
            print(f"[Voice] Error handling message: {e}")

    def find_audio_device(self):
        """Find the wm8960 audio input device index, or None if not found."""
        try:
            p = pyaudio.PyAudio()
            count = p.get_device_count()
            result = None
            for i in range(count):
                info = p.get_device_info_by_index(i)
                if info.get('maxInputChannels', 0) > 0 and 'wm8960' in info.get('name', '').lower():
                    print(f"[Voice] Found audio device [{i}]: {info['name']}")
                    result = i
                    break
            p.terminate()
            if result is None:
                print(f"[Voice] wm8960 not found among {count} devices")
            return result
        except Exception as e:
            print(f"[Voice] Device enumeration error: {e}")
            return None

    def publish_status(self, status: str):
        """Publish voice service status to PC client."""
        try:
            self.mqtt_client.publish(MQTT_TOPIC_STATUS, json.dumps({'status': status}))
        except Exception:
            pass

    def publish_recognition(self, text: str):
        """Publish recognized text to MQTT"""
        if not text or text.strip() == "":
            return

        words = text.strip().split()
        if len(words) < 2 or len(text.strip()) < 5:
            print(f"[Voice] Filtered noise: '{text}' (too short)")
            return

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
        """PyAudio callback - extract left channel mono from stereo"""
        samples = struct.unpack('<' + 'h' * (len(in_data) // 2), in_data)
        mono = samples[::2]  # every other sample = left channel
        self.audio_queue.put(struct.pack('<' + 'h' * len(mono), *mono))
        return (None, pyaudio.paContinue)

    def speak(self, text: str) -> None:
        """Request TTS — signals the listen loop to pause, speak, then resume."""
        self.tts_text = text
        self.tts_event.set()

    def stop_tts(self) -> None:
        """Kill any ongoing TTS playback immediately."""
        proc = self._tts_proc
        if proc and proc.poll() is None:
            proc.kill()
        self._tts_proc = None
        self.tts_text = ""
        self.tts_event.clear()
        # Belt-and-suspenders: kill any stray espeak/aplay processes
        subprocess.run(['pkill', '-f', 'espeak-ng'], stderr=subprocess.DEVNULL)
        subprocess.run(['pkill', '-f', 'aplay.*wm8960'], stderr=subprocess.DEVNULL)

    def _do_tts(self, text: str):
        """Execute TTS synchronously (call only when audio device is free)."""
        print(f"[Voice] Speaking: '{text}'")
        try:
            subprocess.run(
                ['espeak-ng', '-v', 'en', '-s', '150', '-w', '/tmp/_tts.wav', text],
                check=False, stderr=subprocess.DEVNULL
            )
            self._tts_proc = subprocess.Popen(
                ['aplay', '-D', 'plughw:wm8960soundcard,0', '/tmp/_tts.wav'],
                stderr=subprocess.DEVNULL
            )
            self._tts_proc.wait()
            self._tts_proc = None
        except Exception as e:
            print(f'[Voice] TTS error: {e}')
            self._tts_proc = None

    def _drain_queue(self):
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break

    def _handle_pending_tts(self) -> bool:
        """If TTS is pending, execute it and return True."""
        if self.tts_event.is_set() and self.tts_text:
            self.publish_status('ready')
            text_to_speak = self.tts_text
            self.tts_text = ""
            self.tts_event.clear()
            self._do_tts(text_to_speak)
            return True
        return False

    def start_listening(self):
        """Start listening loop. Pauses recording during TTS then resumes."""
        print("[Voice] Starting voice recognition...")
        p = pyaudio.PyAudio()
        self.running = True
        self.publish_status('ready')

        try:
            while self.running:
                # Always handle pending TTS first — works even if mic stream is broken
                if self._handle_pending_tts():
                    self._drain_queue()
                    continue

                self.tts_event.clear()
                self._drain_queue()

                # Re-probe for device every iteration (may not be visible at startup)
                device_index = self.find_audio_device()
                if device_index is None:
                    time.sleep(2)
                    continue

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
                    self.publish_status('listening')
                    print("[Voice] Recognition active - speak now!")

                    while self.running and not self.tts_event.is_set():
                        try:
                            data = self.audio_queue.get(timeout=0.1)
                        except queue.Empty:
                            continue

                        if self.recognizer.AcceptWaveform(data):
                            result = json.loads(self.recognizer.Result())
                            text = result.get('text', '').strip()
                            if text:
                                self.publish_status('processing')
                                self.publish_recognition(text)
                                self.publish_status('listening')
                        else:
                            partial = json.loads(self.recognizer.PartialResult())
                            partial_text = partial.get('partial', '').strip()
                            if partial_text:
                                print(f"[Voice] Hearing: {partial_text}", end='\r')

                    stream.stop_stream()
                    stream.close()

                except Exception as e:
                    print(f"[Voice] ERROR: Audio stream error: {e}")
                    time.sleep(2)

                # Handle TTS whether stream ran normally or errored
                self._handle_pending_tts()

        finally:
            p.terminate()

    def stop(self):
        """Stop the voice listener"""
        print("[Voice] Stopping voice recognition...")
        self.running = False
        self.stop_tts()
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
