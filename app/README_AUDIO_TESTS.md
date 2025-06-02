# Audio Test Routines for Rider Robot

This directory contains comprehensive audio testing tools for the Rider robot's speaker and microphone functionality.

## Test Files

### 1. `test_audio.py` - Comprehensive Audio Tester
Full-featured audio testing with PyAudio integration and LCD screen support.

**Features:**
- Audio device detection and listing
- Microphone level monitoring with visual feedback
- Audio recording and quality analysis
- Speaker testing with multiple methods
- XGO robot speaker function testing
- Interactive mode with robot button controls
- Comprehensive test results summary

**Usage:**
```bash
# Run full test suite
python3 test_audio.py

# Run with debug output
python3 test_audio.py debug

# Run interactive mode (use robot buttons)
python3 test_audio.py interactive

# Run interactive mode with debug
python3 test_audio.py debug interactive
```

### 2. `test_audio_simple.py` - Basic Audio Tester
Lightweight audio testing using system commands only.

**Features:**
- Basic speaker testing with generated tones
- Simple microphone recording tests
- Audio system information display
- No external dependencies beyond standard library

**Usage:**
```bash
# Run basic test suite
python3 test_audio_simple.py

# Run interactive mode
python3 test_audio_simple.py interactive
```

## Requirements

### For `test_audio.py`:
- `pyaudio` - Audio input/output
- `numpy` - Audio signal processing
- `xgo_toolkit` - Robot communication
- `rider_screen` - LCD display integration
- `key` - Robot button input

### For `test_audio_simple.py`:
- Standard Python libraries only
- System commands: `aplay`, `arecord`, `speaker-test`, `amixer`

## Installation

Install required packages:
```bash
# For comprehensive tester
pip3 install pyaudio numpy

# For simple tester (no additional packages needed)
# System audio tools should already be installed on Raspberry Pi
```

## Test Descriptions

### Microphone Tests

1. **Device Detection**: Checks if microphone hardware is detected
2. **Level Monitoring**: Real-time audio level display with visual feedback
3. **Recording Test**: Records audio sample and analyzes quality
4. **Playback Test**: Plays back recorded audio to verify round-trip

### Speaker Tests

1. **System Sounds**: Tests using system audio utilities
2. **Generated Tones**: Creates and plays test tones at various frequencies
3. **Playback Test**: Plays back recorded audio files
4. **XGO Speaker**: Tests robot-specific speaker functions

### Interactive Controls (test_audio.py)

When running in interactive mode, use the robot's physical buttons:
- **A button (lower right)**: Exit the test
- **B button (lower left)**: Record & playback test
- **C button (upper left)**: Microphone level test  
- **D button (upper right)**: Speaker test

## Troubleshooting

### No Audio Devices Found
```bash
# Check ALSA configuration
cat /proc/asound/cards

# List audio devices
aplay -l    # Playback devices
arecord -l  # Recording devices
```

### Permission Issues
```bash
# Add user to audio group
sudo usermod -a -G audio $USER
# Then logout and login again
```

### Volume Issues
```bash
# Check and adjust volume
amixer
alsamixer

# Set specific volume levels
amixer set Master 80%
amixer set Capture 80%
```

### PyAudio Installation Issues
```bash
# Install system dependencies first
sudo apt-get update
sudo apt-get install portaudio19-dev python3-pyaudio

# Then install via pip
pip3 install pyaudio
```

## Expected Results

### Working Audio System
- Microphone: Device detected, good audio levels, clear recordings
- Speaker: System sounds play, generated tones audible, playback works
- Overall: All tests pass with green checkmarks

### Common Issues
- **Low audio levels**: Check microphone gain and positioning
- **No playback**: Check speaker connections and volume levels
- **Distorted audio**: Reduce input/output levels
- **Device not found**: Check hardware connections and drivers

## Integration with Rider Controller

The audio tests can be integrated with the main Rider controller:

```python
from test_audio import AudioTester

# In your robot controller
audio_tester = AudioTester(robot=robot, debug=True)
results = audio_tester.run_full_test_suite()

# Check if audio is working
if results['microphone_detected'] and results['speaker_working']:
    print("✅ Audio system ready")
else:
    print("⚠️  Audio system issues detected")
```

## File Locations

- Test recordings: `/tmp/test_recording.wav`
- Generated tones: `/tmp/tone_*.wav`
- Log output: Console only (no log files created)

## Notes

- Tests are designed to be non-destructive and safe
- Audio files are saved to `/tmp` and cleaned up automatically
- Interactive mode requires physical access to robot buttons
- Some tests may require external audio input (speaking into microphone)
- XGO speaker tests only work when robot is properly connected

## Support

If you encounter issues:
1. Check hardware connections
2. Verify audio system configuration
3. Run the simple tester first to isolate issues
4. Check system logs for audio-related errors
5. Ensure proper permissions for audio devices 