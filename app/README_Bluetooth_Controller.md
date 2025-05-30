# Bluetooth Game Controller Setup for XGO-RIDER Two-Wheel Balancing Robot

This guide explains how to connect and use a Bluetooth game controller to operate your XGO-RIDER two-wheel balancing robot.

## Supported Controllers

- Xbox One/Series Controllers
- PlayStation 4/5 Controllers  
- Generic Bluetooth game controllers
- Most controllers that work with Linux/Raspberry Pi

## Quick Setup

### 1. Run the Setup Script

```bash
cd /home/pi/Rider-Robot-Controller/app
sudo ./setup_bluetooth_controller.sh
```

This script will:
- Install required packages (bluetooth, bluez, pygame)
- Enable Bluetooth service
- Make your Pi discoverable for pairing

### 2. Pair Your Controller

Put your controller in pairing mode:
- **Xbox Controller**: Hold Xbox button + Sync button until LED flashes
- **PS4 Controller**: Hold Share + PS button until light bar flashes
- **PS5 Controller**: Hold Create + PS button until light bar flashes

Then run:
```bash
sudo bluetoothctl
scan on
# Wait for your controller to appear in the list
pair [CONTROLLER_MAC_ADDRESS]
trust [CONTROLLER_MAC_ADDRESS]
connect [CONTROLLER_MAC_ADDRESS]
exit
```

### 3. Test the Controller

```bash
cd /home/pi/Rider-Robot-Controller/app
python3 test_bluetooth_controller.py
```

## Usage

### Option 1: Standalone Controller Mode

Run the controller directly:
```bash
cd /home/pi/Rider-Robot-Controller/app
python3 rider_controller.py
```

Add `debug` for verbose output:
```bash
python3 rider_controller.py debug
```

### Option 2: Integrated App Mode

Run the full app with both Bluetooth and mobile app support:
```bash
cd /home/pi/Rider-Robot-Controller/app
python3 app_TwoCar_bluetooth.py
```

This mode allows you to:
- Use Bluetooth controller when no mobile app is connected
- Automatically switch to mobile app control when connected
- Switch back to Bluetooth when mobile app disconnects

## Controller Mapping

### Analog Sticks
- **Left Stick Y-axis**: Forward/Backward movement
- **Right Stick X-axis**: Turn left/right

### Buttons (Xbox/PlayStation)
- **A/X**: Sway left and right action
- **B/Circle**: Up and down rotate action  
- **X/Square**: Squat down and stand up action
- **Y/Triangle**: Circular swing action
- **L1/L2**: Decrease movement speed
- **R1/R2**: Increase movement speed
- **Left Stick Click**: Decrease robot height
- **Right Stick Click**: Increase robot height
- **Back/Select**: Reset robot to default position
- **Start**: Emergency stop (stop all movement)

### D-Pad
- **Up**: Quick forward movement (0.3 seconds)
- **Down**: Quick backward movement (0.3 seconds)
- **Left**: Quick left turn (0.3 seconds)
- **Right**: Quick right turn (0.3 seconds)

## Configuration

### Speed and Sensitivity Settings

You can modify these parameters in `rider_controller.py`:

```python
# Movement parameters
self.__speed_scale = 1.0      # Movement speed multiplier (0.1 - 2.0)
self.__turn_scale = 100       # Turn speed multiplier
self.__height = 85            # Default height (75-115)
```

### Dead Zone Settings

Adjust the analog stick dead zone to prevent drift:

```python
dead_zone = 0.1  # Increase if sticks are too sensitive
```

### Button Remapping

To change button functions, modify the `__process_buttons()` method:

```python
if button_id == 0:  # Change this number for different buttons
    # Your custom action here
    self.__robot.rider_action(1, True)
```

## Troubleshooting

### Controller Not Connecting

1. **Check Bluetooth status**:
   ```bash
   sudo systemctl status bluetooth
   ```

2. **Restart Bluetooth service**:
   ```bash
   sudo systemctl restart bluetooth
   ```

3. **Check if controller is paired**:
   ```bash
   bluetoothctl
   devices
   ```

4. **Remove and re-pair controller**:
   ```bash
   bluetoothctl
   remove [CONTROLLER_MAC_ADDRESS]
   # Then pair again
   ```

### Controller Disconnects Frequently

1. **Check battery level** - Low battery causes disconnections
2. **Reduce distance** - Stay within 10 meters of the Pi
3. **Check for interference** - Other Bluetooth devices may interfere

### Robot Not Responding

1. **Check robot connection**:
   ```bash
   ls /dev/ttyAMA0
   ```

2. **Test robot directly**:
   ```python
   from xgolib import XGO
   robot = XGO(port='/dev/ttyAMA0', version="xgorider")
   robot.reset()
   ```

3. **Check permissions**:
   ```bash
   sudo usermod -a -G dialout pi
   ```

### pygame Errors

1. **Install pygame**:
   ```bash
   sudo apt install python3-pygame
   ```

2. **Update pygame**:
   ```bash
   pip3 install --upgrade pygame
   ```

## Advanced Features

### Custom Controller Profiles

Create custom profiles for different controllers by modifying the button mappings in the `__process_buttons()` method.

### Multiple Controllers

To use multiple controllers, modify the `controller_id` parameter:

```python
controller = BluetoothController_Rider(robot, controller_id=1, debug=False)
```

### Integration with Other Apps

The Bluetooth controller can be integrated with your existing applications by importing the `BluetoothController_Rider` class:

```python
from rider_controller import BluetoothController_Rider
from xgolib import XGO

robot = XGO(port='/dev/ttyAMA0', version="xgorider")
controller = BluetoothController_Rider(robot, debug=True)

if controller.is_connected():
    controller.start_control_loop()
```

## Safety Notes

- Always test in a safe, open area
- Keep the emergency stop button (Start) easily accessible
- Monitor battery levels of both robot and controller
- Be aware of the robot's movement range and obstacles
- Use appropriate speed settings for your environment

## Files Created

- `rider_controller.py` - Main controller handler
- `setup_bluetooth_controller.sh` - Setup script
- `test_bluetooth_controller.py` - Test script
- `app_TwoCar_bluetooth.py` - Integrated app with Bluetooth support
- `README_Bluetooth_Controller.md` - This documentation

## Support

If you encounter issues:

1. Run the test script with debug mode:
   ```bash
   python3 test_bluetooth_controller.py
   ```

2. Check the system logs:
   ```bash
   sudo journalctl -u bluetooth -f
   ```

3. Verify controller compatibility with:
   ```bash
   jstest /dev/input/js0
   ```

For additional help, check the XGO documentation or community forums. 