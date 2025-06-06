# Rider Robot MQTT Protocol Update

This update implements the complete MQTT protocol as documented in `MQTT_Protocol_Documentation.md`. The system now supports full bidirectional communication between the PC client and the Raspberry Pi robot.

## What's Updated

### 1. Fixed Template Server (`raspberry_pi_server_template.py`)
- Fixed the linter error with `CallbackAPIVersion` import
- The template now shows proper MQTT 5.0 implementation

### 2. Enhanced MQTT Communication (`rider_mqtt.py`)
- **Movement Control**: Implemented proper x,y coordinate handling (-100 to +100 range)
- **Settings Control**: Added real robot control for roll balance, performance mode, and speed changes
- **Camera Control**: Integrated with actual camera hardware control
- **System Control**: Emergency stop functionality with immediate robot safety stop
- **Battery Requests**: Real-time battery level reading from robot hardware
- **IMU Data**: Automatic publishing of roll, pitch, yaw data from robot sensors
- **Status Publishing**: Regular status updates with all robot parameters

### 3. Controller Integration (`rider_controller.py`)
- Added proper MQTT command callbacks that sync with local controller state
- Camera control now works via MQTT commands
- Settings changes from MQTT are reflected on the LCD screen
- Movement commands from MQTT work alongside gamepad control

### 4. New Test Tool (`test_mqtt_integration.py`)
- Comprehensive MQTT protocol testing
- Monitors message frequencies and formats
- Sends test commands to verify remote control functionality
- Reports message statistics and protocol compliance

## Key Features Implemented

### Remote Control Commands
All commands follow the exact protocol specification:

```bash
# Movement control (PC → Robot)
Topic: rider/control/movement
Message: {"x": 0, "y": 50, "timestamp": 1749239765.7873564}

# Settings control (PC → Robot)  
Topic: rider/control/settings
Message: {"action": "toggle_roll_balance", "timestamp": 1749239770.7899299}
Message: {"action": "change_speed", "value": 1.5, "timestamp": 1749239772.7912588}

# Camera control (PC → Robot)
Topic: rider/control/camera  
Message: {"action": "toggle_camera", "timestamp": 1749239773.7919118}

# System control (PC → Robot)
Topic: rider/control/system
Message: {"action": "emergency_stop", "timestamp": 1749239780.1234567}

# Battery request (PC → Robot)
Topic: rider/request/battery
Message: {"action": "request_battery", "timestamp": 1749239773.7923646}
```

### Status Publishing (Robot → PC)
The robot automatically publishes status updates:

```bash
# General status (every 2 seconds)
Topic: rider/status
Message: {
  "timestamp": 1749239530.312921,
  "speed_scale": 1.0,
  "roll_balance_enabled": true,
  "performance_mode_enabled": false,
  "camera_enabled": false,
  "controller_connected": true,
  "height": 85,
  "connection_status": "connected"
}

# Battery status (every 10 seconds)
Topic: rider/status/battery
Message: {
  "timestamp": 1749239636.9426005,
  "level": 54,
  "status": "normal",
  "source": "hardware"
}

# IMU data (every 0.5 seconds)  
Topic: rider/status/imu
Message: {
  "timestamp": 1749239641.1890562,
  "roll": 0.0,
  "pitch": 0.0,
  "yaw": 0.0
}
```

## How to Use

### 1. Run the Robot Controller
The MQTT system is automatically initialized when you run the main controller:

```bash
cd ~/Rider-Robot-Controller/app
python3 rider_controller.py
```

The robot will:
- Connect to MQTT broker at `192.168.1.173:1883` by default
- Start publishing status, battery, and IMU data
- Listen for remote control commands
- Display MQTT status on the LCD screen

### 2. Test the MQTT Protocol
Use the test tool to verify everything is working:

```bash
# Test with default broker (localhost) for 30 seconds
python3 test_mqtt_integration.py

# Test with specific broker for 60 seconds  
python3 test_mqtt_integration.py 192.168.1.173 60
```

The test will:
- Connect to the MQTT broker
- Subscribe to all status topics
- Send test commands (movement, settings, camera, battery request)
- Monitor message frequencies and report statistics

### 3. Monitor MQTT Traffic
You can monitor all MQTT traffic using any MQTT client:

```bash
# Using mosquitto_sub to monitor all rider topics
mosquitto_sub -h 192.168.1.173 -t "rider/#" -v

# Monitor specific topics
mosquitto_sub -h 192.168.1.173 -t "rider/status"
mosquitto_sub -h 192.168.1.173 -t "rider/status/battery"  
mosquitto_sub -h 192.168.1.173 -t "rider/status/imu"
```

### 4. Send Remote Commands
You can send commands using any MQTT client:

```bash
# Move robot forward
mosquitto_pub -h 192.168.1.173 -t "rider/control/movement" \
  -m '{"x": 0, "y": 50, "timestamp": '$(date +%s.%N)'}'

# Stop robot
mosquitto_pub -h 192.168.1.173 -t "rider/control/movement" \
  -m '{"x": 0, "y": 0, "timestamp": '$(date +%s.%N)'}'

# Toggle roll balance
mosquitto_pub -h 192.168.1.173 -t "rider/control/settings" \
  -m '{"action": "toggle_roll_balance", "timestamp": '$(date +%s.%N)'}'

# Emergency stop
mosquitto_pub -h 192.168.1.173 -t "rider/control/system" \
  -m '{"action": "emergency_stop", "timestamp": '$(date +%s.%N)'}'
```

## Configuration

### Change MQTT Broker
To use a different MQTT broker, modify the default in `rider_mqtt.py`:

```python
# In rider_mqtt.py, line 14:
def __init__(self, robot=None, broker_host="YOUR_BROKER_IP", broker_port=1883, debug=False):
```

Or pass it when initializing:
```python
mqtt_client = RiderMQTT(robot=robot, broker_host="192.168.1.100", debug=True)
```

### Enable Debug Mode
For detailed MQTT logging, enable debug mode:

```bash
python3 rider_controller.py debug
```

This will show all MQTT messages, robot commands, and status updates.

## Troubleshooting

### MQTT Connection Issues
1. Check broker IP address and port
2. Ensure broker is running: `systemctl status mosquitto`
3. Check network connectivity: `ping 192.168.1.173`
4. Verify firewall allows MQTT port 1883

### Robot Not Responding to Commands
1. Check robot is connected: Look for "✅ Robot connected" at startup
2. Verify MQTT messages are being received: Enable debug mode
3. Check robot battery level: Low battery may affect response
4. Ensure robot is not in emergency stop state

### Message Frequency Issues
Expected frequencies (check with test tool):
- Status: ~0.5 messages/second (every 2 seconds)
- IMU: ~2.0 messages/second (every 0.5 seconds)  
- Battery: ~0.1 messages/second (every 10 seconds)

If frequencies are off, check system load and MQTT broker performance.

## Integration with PC Client

The robot now fully supports the PC client application. The PC client should:

1. Connect to the same MQTT broker (`192.168.1.173:1883`)
2. Subscribe to status topics for real-time robot monitoring
3. Publish to control topics for remote operation
4. Follow the exact message formats in the protocol documentation

The robot will respond to all PC client commands while maintaining compatibility with the gamepad controller. 