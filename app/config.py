#!/usr/bin/env python3
# coding=utf-8

"""
Rider Robot Controller Configuration
Centralized configuration file for easy modification of settings
"""

# MQTT Broker Configuration
# The robot runs its own MQTT broker locally
MQTT_BROKER_HOST = "localhost"  # Robot's local MQTT broker
MQTT_BROKER_PORT = 1883

# Robot Serial Configuration
ROBOT_SERIAL_PORT = "/dev/ttyS0"
ROBOT_BAUDRATE = 115200

# Camera Configuration
CAMERA_INDEX = 0  # USB camera index (0 for /dev/video0)
DEFAULT_IMAGE_QUALITY = 85  # JPEG quality (0-100)

# Image Resolution Presets
IMAGE_RESOLUTIONS = {
    'tiny': (160, 120),
    'low': (320, 240),
    'high': (640, 480)
}

# Safety Configuration
CLIENT_TIMEOUT = 30.0  # Seconds of inactivity before safety shutdown
MOVEMENT_TIMEOUT = 2.0  # Seconds without commands before stopping movement
SAFETY_COMMANDS_TIMEOUT = 3.0  # Wait time for safety commands during shutdown

# Publishing Intervals (seconds)
STATUS_PUBLISH_INTERVAL = 2.0  # Battery, CPU, system status
IMU_PUBLISH_INTERVAL = 0.5  # Roll, pitch, yaw data

# Display Configuration
LCD_SPI_PORT = 0
LCD_SPI_DEVICE = 0
LCD_ROTATION = 0  # 0, 90, 180, or 270 degrees

# Debug Mode
DEBUG_MODE = False  # Set to True for verbose logging
