# Rider Robot Image Capture System

This document explains how to use the image capture functionality to request images from the Rider robot's camera via MQTT.

## Overview

The image capture system allows PC clients to request images from the robot's camera through MQTT messaging. Images are captured at configurable resolutions and transmitted as base64-encoded JPEG data.

## Architecture

```
PC Client  --(MQTT Request)-->  Robot Controller  --(Camera API)-->  Camera Hardware
PC Client  <--(MQTT Response)-- Robot Controller  <--(JPEG Data)---  Camera Hardware
```

### Components

1. **RiderVideo** (`app/rider_video.py`): Handles camera operations and image capture
2. **RiderMQTT** (`app/rider_mqtt.py`): Manages MQTT communication and image requests
3. **RiderController** (`app/rider_controller.py`): Coordinates between MQTT and camera systems
4. **PC Client**: External application that requests images via MQTT

## MQTT Topics

### Request Topic
- **Topic**: `rider/control/image_capture`
- **Purpose**: PC client sends image capture requests

### Response Topic  
- **Topic**: `rider/response/image_capture`
- **Purpose**: Robot sends image data or error responses

## Message Formats

### Image Capture Request
```json
{
    "request_id": "img_abc12345",
    "resolution": "high",
    "timestamp": 1638360000.123,
    "client_id": "rider_image_client_1638360000"
}
```

**Fields:**
- `request_id`: Unique identifier for the request
- `resolution`: "high" (640x480), "low" (320x240), or "tiny" (160x120)
- `timestamp`: Unix timestamp when request was sent
- `client_id`: Identifier of the requesting client

### Image Capture Response (Success)
```json
{
    "request_id": "img_abc12345",
    "timestamp": 1638360000.456,
    "success": true,
    "image_data": "base64_encoded_jpeg_data_here...",
    "resolution": "high",
    "client_id": "rider_image_client_1638360000",
    "image_size": "45.2KB",
    "capture_timestamp": 1638360000.234
}
```

### Image Capture Response (Error)
```json
{
    "request_id": "img_abc12345",
    "timestamp": 1638360000.456,
    "success": false,
    "error": "Camera is disabled - enable camera first",
    "client_id": "rider_image_client_1638360000"
}
```

## Usage Examples

### Python Client Example

```python
#!/usr/bin/env python3
import json
import time
import base64
import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion

class ImageCaptureClient:
    def __init__(self, broker_host="192.168.1.173"):
        self.broker_host = broker_host
        self.client = mqtt.Client(
            callback_api_version=CallbackAPIVersion.VERSION2,
            protocol=mqtt.MQTTv5
        )
        self.connected = False
        self.received_images = {}
        
    def connect(self):
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.connect(self.broker_host, 1883, 60)
        self.client.loop_start()
        
        # Wait for connection
        timeout = 10
        start_time = time.time()
        while not self.connected and (time.time() - start_time) < timeout:
            time.sleep(0.1)
        return self.connected
    
    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            self.connected = True
            client.subscribe("rider/response/image_capture")
    
    def _on_message(self, client, userdata, msg):
        if msg.topic == "rider/response/image_capture":
            payload = json.loads(msg.payload.decode())
            request_id = payload.get('request_id')
            self.received_images[request_id] = payload
    
    def capture_image(self, resolution="high", timeout=15):
        request_id = f"img_{int(time.time())}"
        
        # Send request
        request = {
            "request_id": request_id,
            "resolution": resolution,
            "timestamp": time.time(),
            "client_id": "my_client"
        }
        
        self.client.publish("rider/control/image_capture", json.dumps(request))
        
        # Wait for response
        start_time = time.time()
        while (time.time() - start_time) < timeout:
            if request_id in self.received_images:
                return self.received_images.pop(request_id)
            time.sleep(0.1)
        
        return {"success": False, "error": "Timeout"}
    
    def save_image(self, image_data, filename):
        """Save base64 image data to file"""
        img_bytes = base64.b64decode(image_data)
        with open(filename, 'wb') as f:
            f.write(img_bytes)

# Usage
client = ImageCaptureClient()
if client.connect():
    result = client.capture_image("high")
    if result.get('success'):
        client.save_image(result['image_data'], 'captured_image.jpg')
        print(f"Image saved: {result['image_size']}")
    else:
        print(f"Error: {result.get('error')}")
```

### JavaScript/Node.js Client Example

```javascript
const mqtt = require('mqtt');
const fs = require('fs');

class ImageCaptureClient {
    constructor(brokerHost = '192.168.1.173') {
        this.brokerHost = brokerHost;
        this.client = null;
        this.receivedImages = {};
    }
    
    connect() {
        return new Promise((resolve) => {
            this.client = mqtt.connect(`mqtt://${this.brokerHost}:1883`);
            
            this.client.on('connect', () => {
                console.log('Connected to MQTT broker');
                this.client.subscribe('rider/response/image_capture');
                resolve(true);
            });
            
            this.client.on('message', (topic, message) => {
                if (topic === 'rider/response/image_capture') {
                    const payload = JSON.parse(message.toString());
                    this.receivedImages[payload.request_id] = payload;
                }
            });
        });
    }
    
    async captureImage(resolution = 'high', timeout = 15000) {
        const requestId = `img_${Date.now()}`;
        
        const request = {
            request_id: requestId,
            resolution: resolution,
            timestamp: Date.now() / 1000,
            client_id: 'nodejs_client'
        };
        
        // Send request
        this.client.publish('rider/control/image_capture', JSON.stringify(request));
        
        // Wait for response
        return new Promise((resolve) => {
            const startTime = Date.now();
            
            const checkResponse = () => {
                if (this.receivedImages[requestId]) {
                    const response = this.receivedImages[requestId];
                    delete this.receivedImages[requestId];
                    resolve(response);
                } else if (Date.now() - startTime > timeout) {
                    resolve({ success: false, error: 'Timeout' });
                } else {
                    setTimeout(checkResponse, 100);
                }
            };
            
            checkResponse();
        });
    }
    
    saveImage(imageData, filename) {
        const buffer = Buffer.from(imageData, 'base64');
        fs.writeFileSync(filename, buffer);
    }
}

// Usage
async function main() {
    const client = new ImageCaptureClient();
    await client.connect();
    
    const result = await client.captureImage('high');
    if (result.success) {
        client.saveImage(result.image_data, 'captured_image.jpg');
        console.log(`Image saved: ${result.image_size}`);
    } else {
        console.log(`Error: ${result.error}`);
    }
}

main();
```

## Testing

### Running the Test Client

1. Ensure the robot controller is running with camera enabled
2. Run the test client:
   ```bash
   python3 test_image_capture_client.py
   ```

### Expected Output

```
🤖 Rider Robot Image Capture Client Test
==================================================
RiderImageCaptureClient initialized - Broker: 192.168.1.173:1883
Connecting to MQTT broker at 192.168.1.173:1883
✅ MQTT connected successfully
MQTT broker connected
Subscribed to: rider/response/image_capture

📸 Testing image capture...

1. Testing HIGH resolution capture...
📸 Requesting image capture: ID=img_a1b2c3d4, resolution=high
MQTT message received - Topic: rider/response/image_capture
📸 Image response received for request: img_a1b2c3d4
✅ Image capture successful: 45.2KB
✅ High resolution image received: 45.2KB
💾 Image saved to captured_image_high_1638360123.jpg (45.2KB)
💾 Image saved as: captured_image_high_1638360123.jpg

2. Testing LOW resolution capture...
📸 Requesting image capture: ID=img_e5f6g7h8, resolution=low
MQTT message received - Topic: rider/response/image_capture
📸 Image response received for request: img_e5f6g7h8
✅ Image capture successful: 12.1KB
✅ Low resolution image received: 12.1KB
💾 Image saved to captured_image_low_1638360125.jpg (12.1KB)
💾 Image saved as: captured_image_low_1638360125.jpg

✅ Image capture test completed!
```

## Error Conditions

### Common Errors

1. **Camera not available**: "Camera not available"
2. **Camera disabled**: "Camera is disabled - enable camera first"
3. **Capture failed**: "Failed to capture image from camera" 
4. **Timeout**: "Request timed out after 15 seconds"
5. **MQTT disconnected**: "Cannot capture image - not connected to MQTT"

### Troubleshooting

1. **Check camera status**: Ensure the robot's camera is enabled via controller or MQTT
2. **Verify MQTT connection**: Confirm MQTT broker is accessible
3. **Check network**: Ensure PC client can reach the robot's network
4. **Monitor logs**: Check robot controller debug output for errors

## Image Specifications

### High Resolution ("high")
- **Resolution**: 640x480 pixels
- **Format**: JPEG
- **Quality**: 85%
- **Typical size**: 30-60KB

### Low Resolution ("low")  
- **Resolution**: 320x240 pixels
- **Format**: JPEG
- **Quality**: 85%
- **Typical size**: 8-20KB

### Tiny Resolution ("tiny")
- **Resolution**: 160x120 pixels
- **Format**: JPEG
- **Quality**: 85%
- **Typical size**: 2-6KB

## Performance Considerations

1. **Network bandwidth**: High resolution images require more bandwidth
2. **Capture time**: Temporary resolution changes may add ~100ms delay
3. **Concurrent requests**: System handles one image request at a time
4. **Memory usage**: Base64 encoding increases data size by ~33%

## Integration with Existing PC Client

To integrate image capture into your existing PC client:

1. **Add MQTT subscription** to `rider/response/image_capture`
2. **Send image requests** to `rider/control/image_capture` 
3. **Handle responses** with base64 image data
4. **Decode and save** images as needed

The image capture system is fully compatible with the existing MQTT infrastructure and doesn't interfere with other robot control functionality. 