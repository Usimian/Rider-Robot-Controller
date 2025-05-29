#!/bin/bash

echo "==========================================="
echo "Manual PS4 Controller Bluetooth Pairing"
echo "==========================================="
echo ""

# Reset controller first
echo "Step 1: Reset your PS4 controller"
echo "Hold the PS button for 10 seconds to completely turn off the controller"
echo "Press Enter when the controller is completely off..."
read

# Make Pi discoverable
echo ""
echo "Step 2: Making Raspberry Pi discoverable..."
bluetoothctl <<EOF
discoverable on
pairable on
agent on
default-agent
EOF

echo ""
echo "Step 3: Put PS4 controller in pairing mode"
echo "Now hold Share + PS buttons until the light bar flashes RAPIDLY"
echo "The light should flash white quickly (not slowly)"
echo "Press Enter when the controller is flashing rapidly..."
read

echo ""
echo "Step 4: Manual pairing process"
echo "We'll now pair step by step..."

# Remove any existing pairing
bluetoothctl remove 98:B6:E9:29:18:54 2>/dev/null

echo ""
echo "Starting scan..."
bluetoothctl scan on &
SCAN_PID=$!

echo "Waiting 15 seconds for controller to be discovered..."
sleep 15

kill $SCAN_PID 2>/dev/null

echo ""
echo "Devices found:"
bluetoothctl devices

echo ""
echo "Now attempting to pair with your controller..."
bluetoothctl pair 98:B6:E9:29:18:54

echo ""
echo "Trusting the controller..."
bluetoothctl trust 98:B6:E9:29:18:54

echo ""
echo "Connecting to the controller..."
bluetoothctl connect 98:B6:E9:29:18:54

echo ""
echo "Checking connection..."
sleep 3

if bluetoothctl info 98:B6:E9:29:18:54 | grep -q "Connected: yes"; then
    echo "✓ SUCCESS! PS4 Controller is connected via Bluetooth!"
    echo ""
    echo "Testing joystick interface..."
    sleep 2
    
    if [ -e /dev/input/js0 ]; then
        echo "✓ Joystick interface found: /dev/input/js0"
        echo ""
        echo "Testing basic input..."
        echo "Move a stick or press a button on your controller..."
        timeout 5 jstest --event /dev/input/js0 | head -5
        echo ""
        echo "Controller is ready! You can test it with:"
        echo "python3 test_bluetooth_controller.py"
    else
        echo "⚠ Controller connected but no joystick interface yet."
        echo "Try unplugging/reconnecting or wait a moment for the interface to appear."
    fi
else
    echo "✗ Connection failed. Controller info:"
    bluetoothctl info 98:B6:E9:29:18:54
    echo ""
    echo "Try these troubleshooting steps:"
    echo "1. Make sure controller battery is charged"
    echo "2. Try turning controller completely off (hold PS for 10 seconds)"
    echo "3. Try the pairing process again"
    echo "4. Make sure no other devices are connected to the controller"
fi 