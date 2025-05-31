# XGO-Toolkit Robot Commands Reference

## 🔄 **Movement Commands**

### Basic Movement
- `move_x(step, runtime=0)` - Move forward/backward (-1.5 to 1.5 for Rider)
- `move_y(step, runtime=0)` - Move left/right (-1.0 to 1.0 for Rider)  
- `turn(step, runtime=0)` - Turn left/right (-360° to 360° for Rider)
- `stop()` - Stop all movement

### Convenience Movement Functions
- `forward(step)` - Move forward
- `back(step)` - Move backward
- `left(step)` - Move left
- `right(step)` - Move right
- `turnleft(step)` - Turn left
- `turnright(step)` - Turn right

### Advanced Movement
- `move_by(distance, vx, vy, k, mintime)` - Move a specific distance
- `move_x_by(distance, vx=18, k=0.035, mintime=0.55)` - Move X distance
- `move_y_by(distance, vy=18, k=0.0373, mintime=0.5)` - Move Y distance
- `turn_by(theta, mintime, vyaw=16, k=0.08)` - Turn by specific angle
- `turn_to(theta, vyaw=60, emax=10)` - Turn to specific heading

## 🎪 **XGO-Rider Specific Commands**

### Rider Movement
- `rider_move_x(speed, runtime=0)` - Forward/backward movement
- `rider_turn(speed, runtime=0)` - Rotation movement
- `rider_reset_odom()` - Reset odometry

### Rider Actions (Preset Movements)
- `rider_action(action_id, wait=False)` - Execute preset action
  - Action 1: Sway left and right
  - Action 2: Up and down rotate
  - Action 3: (Custom action)
  - Action 4: (Custom action)
  - Action 5: Squat down and stand up
  - Action 6: Circular swing
  - Action 255: Reset to default position

### Rider Pose Control
- `rider_height(data)` - Set height (60-120 range for Rider)
- `rider_roll(data)` - Set roll angle
- `rider_periodic_roll(period)` - Periodic roll motion
- `rider_periodic_z(period)` - Periodic height motion

### Rider Settings
- `rider_balance_roll(mode)` - Enable/disable roll balance (0/1)
- `rider_perform(mode)` - Enable/disable performance mode (0/1)
- `rider_calibration(state)` - Calibration mode ('start'/'end')
- `rider_reset()` - Reset to default state

### Rider LED Control
- `rider_led(index, color)` - Control LED colors
  - index: LED position
  - color: [R, G, B] values (0-255)

## 🤖 **General Robot Commands**

### Pose Control
- `translation(direction, data)` - Body translation without moving feet
  - direction: 'x', 'y', 'z' or list of directions
- `attitude(direction, data)` - Body rotation without moving feet
  - direction: 'r' (roll), 'p' (pitch), 'y' (yaw) or list

### Preset Actions (action_id 1-255)
- `action(action_id, wait=False)` - Execute preset movements
  
**Common Action IDs:**
- 1: Prone
- 2: Stand up
- 3: Crawl
- 4: Turn in circle
- 6: Squat up/down
- 7-9: Various movements
- 11: Take a pee
- 12: Sit down
- 13: Wave hand
- 14: Stretch
- 15: Wave
- 16: Sway
- 17: Beg/Pray
- 18: Look for food
- 19: Handshake
- 20: Chicken head
- 21: Push-up
- 22: Look around
- 23: Dance
- 24: Naughty
- 128-130: Arm grabbing actions
- 255: Reset to default

### Motor Control
- `motor(motor_id, data)` - Control individual servos
- `motor_speed(speed)` - Set servo speed (1-255)
- `unload_motor(leg_id)` - Disable motor for leg (1-5)
- `load_motor(leg_id)` - Enable motor for leg (1-5)
- `unload_allmotor()` - Disable all motors
- `load_allmotor()` - Enable all motors

### Leg Control
- `leg(leg_id, data)` - Control single leg position
  - leg_id: 1-4 (legs)
  - data: [x, y, z] coordinates

### Gait Control
- `gait_type(mode)` - Set walking style
  - "trot", "walk", "high_walk", "slow_trot"
- `pace(mode)` - Set step frequency
  - "normal", "slow", "high"
- `mark_time(data)` - Marching in place

### Periodic Motion
- `periodic_rot(direction, period)` - Periodic rotation
- `periodic_tran(direction, period)` - Periodic translation

## 📊 **Sensor Reading Commands**

### Battery & System
- `read_battery()` / `rider_read_battery()` - Battery percentage
- `read_firmware()` / `rider_read_firmware()` - Firmware version
- `read_lib_version()` - Library version

### IMU Sensors
- `read_roll()` / `rider_read_roll()` - Roll angle
- `read_pitch()` / `rider_read_pitch()` - Pitch angle  
- `read_yaw()` / `rider_read_yaw()` - Yaw angle
- `read_imu()` - Full IMU data
- `read_imu_int16(direction)` - 16-bit IMU data

### Motor Feedback
- `read_motor()` - Read all servo angles

## ⚙️ **System Commands**

### Control Modes
- `imu(mode)` - Enable/disable self-balancing (0/1)
- `perform(mode)` - Enable/disable continuous actions (0/1)

### Calibration & Setup
- `calibration(state)` - Software calibration ('start'/'end')
- `set_origin()` - Set current position as origin
- `reset()` / `rider_reset()` - Reset to default state

### Communication
- `bt_rename(name)` - Rename Bluetooth device

### Arm Control (XGO-Mini/Lite)
- `arm(arm_x, arm_z)` - Control arm position
- `arm_polar(arm_theta, arm_r)` - Polar coordinate control
- `arm_mode(mode)` - Set arm control mode
- `claw(pos)` - Control claw position
- `arm_speed(speed)` - Set arm movement speed

### Teaching Mode
- `teach(mode, pos_id)` - Record/play movements
- `teach_arm(mode, pos_id)` - Record/play arm movements

### Hardware Control
- `output_analog(data)` - Analog output control
- `output_digital(data)` - Digital output control
- `move_to(data)` - Move to specific position
- `upgrade(filename)` / `rider_upgrade(filename)` - Firmware update

## 📝 **Parameter Limits for XGO-Rider**

- **Movement Speed**: X: ±1.5, Y: ±1.0, Turn: ±360°
- **Height Range**: 60-120
- **Roll Range**: ±17°
- **Pitch/Yaw**: ±1° (limited for balancing)

