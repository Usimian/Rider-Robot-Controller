# Rider Robot Controller

A comprehensive control and management system for the XGO-RIDER two-wheel self-balancing robot running on Raspberry Pi Compute Module 4.

## Overview

This project provides multiple control interfaces for the XGO-RIDER robot, including Bluetooth gamepad control, MQTT network communication, camera-based vision processing, and an LCD display system. It enables both remote teleoperation and autonomous AI-powered behaviors.

## Key Features

### Control Interfaces
- **Bluetooth Gamepad**: Xbox One/PS4/generic controller support via PyGame
- **MQTT Network Control**: Remote operation over WiFi/Ethernet
- **Physical Buttons**: Direct control via robot's hardware buttons
- **LCD Menu System**: On-screen status and control interface

### Movement & Actions
- Precise directional control (forward/backward/lateral/turning)
- 255+ preset action sequences (sway, squat, dance, etc.)
- Height adjustment (60-120 range)
- Roll balancing compensation
- Performance mode for aggressive movements

### Vision & AI Capabilities
- Multi-resolution image capture (160x120, 320x240, 640x480)
- Real-time video streaming over MQTT
- YOLO-based object detection
- Face detection and recognition
- Gesture recognition and control
- Color tracking and following
- QR code detection
- Pose estimation

### Monitoring & Sensing
- Real-time battery level tracking
- IMU data display (roll, pitch, yaw)
- CPU usage and system health monitoring
- Connection status tracking
- Camera feed preview on LCD

### Audio Features
- Speaker output control
- Microphone input processing
- Text-to-speech support
- Voice command integration with GPT

### Safety Features
- Emergency stop button (immediate halt)
- Inactive client detection and auto-shutdown
- Robust reconnection handling
- Movement timeout protection
- Graceful disconnect procedures

## System Architecture

### Core Components

| Module | Purpose | Lines of Code |
|--------|---------|---------------|
| `rider_controller.py` | Main control hub with Bluetooth gamepad integration | 1,400+ |
| `rider_mqtt.py` | MQTT communication and network control | 1,000+ |
| `rider_screen.py` | LCD display management and UI | 750+ |
| `rider_video.py` | Camera capture and streaming | 500+ |
| `yolostream.py` | Real-time object detection pipeline | 600+ |
| `xgo_toolkit.py` | XGO-Rider command API | - |

### Hardware Interfaces

| Component | Interface | Purpose |
|-----------|-----------|---------|
| XGO-RIDER Robot | Serial (UART) `/dev/ttyS0` | Robot control and sensor data |
| Camera | USB or CSI | Vision processing and streaming |
| LCD Display | SPI | Status display and real-time feedback |
| Bluetooth Controller | PyGame/HID | Wireless gamepad input |
| Audio System | ALSA/PyAudio | Microphone and speaker |
| MQTT Broker | Network | Remote communication |

## Project Structure

```
Rider-Robot-Controller/
├── app/                          # Main application code
│   ├── rider_controller.py       # Primary control hub
│   ├── rider_mqtt.py             # Network communication
│   ├── rider_video.py            # Camera/video system
│   ├── rider_screen.py           # LCD display management
│   ├── test_audio.py             # Audio testing utilities
│   ├── key.py                    # Button interface
│   ├── MQTT_Protocol_Documentation.md
│   ├── README_Bluetooth_Controller.md
│   └── README_AUDIO_TESTS.md
├── yolostream.py                 # YOLO inference pipeline
├── firmware/                     # Robot firmware files
├── tools/                        # Compilation and testing utilities
└── README_IMAGE_CAPTURE.md       # Image capture protocol
```

## Technology Stack

- **Python 3.9+**: Primary programming language
- **PyGame 2.6.1**: Bluetooth controller input handling
- **Paho MQTT**: Network communication protocol
- **OpenCV**: Image processing and camera access
- **PIL/Pillow**: Image manipulation
- **NumPy**: Numerical operations
- **PyAudio**: Audio input/output
- **ONNX Runtime**: Neural network inference
- **TensorFlow Lite**: Lightweight ML models
- **psutil**: System monitoring

## Getting Started

### Prerequisites
- Raspberry Pi CM4 with XGO-RIDER robot
- Python 3.9 or higher
- Bluetooth gamepad (optional but recommended)
- MQTT broker running on your network (configure IP in `app/config.py`)
- USB or CSI camera (for vision features)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd Rider-Robot-Controller
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure the robot settings in `app/config.py`:
```python
# Edit the MQTT broker IP address to match your network
MQTT_BROKER_HOST = "192.168.1.130"  # Change this to your MQTT broker IP
MQTT_BROKER_PORT = 1883
```

All configuration settings (MQTT broker, camera, safety timeouts, etc.) are centralized in `app/config.py` for easy modification.

### Running the Controller

Start the main controller application:
```bash
python app/rider_controller.py
```

This launches:
- MQTT network communication
- LCD screen display
- Camera streaming (if available)
- Bluetooth controller input monitoring

## Usage

### Bluetooth Controller
Connect an Xbox One, PS4, or compatible gamepad via Bluetooth. The controller provides:
- Analog stick control for movement
- Button mappings for preset actions
- Emergency stop capability
- See `app/README_Bluetooth_Controller.md` for detailed mapping

### MQTT Control
Send commands over the network using MQTT topics:
- `/rider/command`: Send movement and action commands
- `/rider/status`: Receive real-time status updates
- `/rider/image_request`: Request camera captures
- See `app/MQTT_Protocol_Documentation.md` for full protocol

## MQTT Communication

The system uses MQTT 5.0 for network communication:
- **Status Updates**: Published every 2 seconds with battery, CPU, IMU data
- **Command Processing**: Real-time movement and action commands
- **Image Capture**: On-demand image requests with configurable resolution
- **Safety Monitoring**: Inactive client detection and auto-shutdown

## Safety Features

The system includes multiple safety mechanisms:
1. **Movement Timeout**: Robot stops if no command received for 2 seconds
2. **Emergency Stop**: Immediate halt via controller or button
3. **Client Monitoring**: Automatic shutdown if MQTT client inactive
4. **Connection Watchdog**: Monitors and reconnects dropped connections
5. **Graceful Shutdown**: Clean disconnect procedures

## Documentation

Additional documentation is available in the repository:
- `app/MQTT_Protocol_Documentation.md`: Complete MQTT protocol specification
- `app/README_Bluetooth_Controller.md`: Gamepad setup and button mapping
- `app/README_AUDIO_TESTS.md`: Audio system testing guide
- `README_IMAGE_CAPTURE.md`: Camera capture protocol
- `xgo_toolkit_commands.md`: Full robot command reference

## Recent Updates

- Added "tiny" video format (160x120) for lower bandwidth
- Camera capture now works independently of video feed
- Improved communication protocol reliability
- Enhanced MQTT status reporting with CPU metrics
- Fixed Bluetooth controller connection stability
- Added Roll/Pitch/Yaw display on LCD screen

## Development

The project uses a multi-threaded architecture with:
- Separate threads for MQTT, controller input, display updates, and camera capture
- Thread-safe state management
- Modular design for easy extension
- Comprehensive error handling and recovery

Total codebase: ~61,000 lines of Python across 214 files

## License

[Add license information]

## Contributing

[Add contribution guidelines]

## Support

For issues and questions, please refer to the documentation files or create an issue in the repository.
