# Robot Audio/TTS Implementation Specification

## Overview
Add text-to-speech (TTS) capability to announce movement commands and boot greeting.

## TTS Command via MQTT

### Command Format
```json
{
  "action": "speak",
  "text": "<message to speak>",
  "timestamp": 1234567890.123
}
```

### MQTT Topic
- **Topic**: `rider/control/movement` (same topic as move/turn commands)
- **QoS**: Same as other movement commands

### Examples
```json
{"action": "speak", "text": "Moving forward 20 centimeters"}
{"action": "speak", "text": "Turning left 90 degrees"}
{"action": "speak", "text": "Hello, I am ready"}
```

## Implementation Requirements

### 1. TTS Handler
Add handler for "speak" action in the movement command processor:

```python
def handle_movement_command(msg):
    action = msg.get('action')

    if action == 'speak':
        text = msg.get('text', '')
        tts(text)  # Use existing TTS function from demos

    elif action == 'move':
        # ... existing move handling

    elif action == 'turn':
        # ... existing turn handling
```

### 2. Boot Greeting
When robot initialization completes:

```python
# After all systems initialized and ready
tts("Hello, I am ready")
# or simply
tts("Hello")
```

### 3. TTS Function
Use existing TTS implementation from demos. Recommended sources:
- `demos/gpt_utils.py` - `tts()` function (line ~474)
- `demos/gpt_free_en.py` - `tts()` function (line ~268)

Example implementation:
```python
def tts(content):
    """Text-to-speech using system TTS"""
    import subprocess
    # Use espeak, festival, or pico2wave
    subprocess.run(['espeak', content], check=False)
```

## Behavior Notes

### Non-Blocking
- TTS should **not block** movement commands
- If new TTS command arrives while speaking, you can either:
  - **Option A**: Queue it (speak after current completes)
  - **Option B**: Interrupt current and speak new (simpler)

### Error Handling
- If TTS fails, log error but don't crash
- Movement should work even if TTS unavailable

### Volume
- Use reasonable default volume (suggest 70-80%)
- TTS volume should not interfere with other audio

## Testing

### Manual Test Commands
Via MQTT:
```bash
# Test TTS
mosquitto_pub -h localhost -t rider/control/movement -m '{"action":"speak","text":"Testing audio"}'

# Test with movement
mosquitto_pub -h localhost -t rider/control/movement -m '{"action":"speak","text":"Moving forward 10 centimeters"}'
mosquitto_pub -h localhost -t rider/control/movement -m '{"action":"move","distance":33}'
```

### Expected Behavior
1. Boot robot → Hear "Hello, I am ready" (or "Hello")
2. Send move command → Hear "Moving forward X centimeters" then robot moves
3. Send turn command → Hear "Turning left/right X degrees" then robot turns
4. Commands execute in sequence (TTS doesn't block movements)

## PC Client Sends

The PC client will automatically send TTS commands before movements:

**Move Command Flow:**
1. PC sends: `{"action": "speak", "text": "Moving forward 20 centimeters"}`
2. PC sends: `{"action": "move", "distance": 67}` (after TTS)
3. Robot speaks then moves

**Turn Command Flow:**
1. PC sends: `{"action": "speak", "text": "Turning left 90 degrees"}`
2. PC sends: `{"action": "turn", "angle": 50}` (after TTS)
3. Robot speaks then turns

## Summary for Robot Coder

**What to implement:**
1. Add `if action == 'speak':` handler in movement command processor
2. Call `tts(msg['text'])` using existing TTS function
3. Add `tts("Hello, I am ready")` at end of boot initialization
4. Make sure TTS doesn't block subsequent commands

**That's it!** The PC client handles sending the TTS commands automatically.
