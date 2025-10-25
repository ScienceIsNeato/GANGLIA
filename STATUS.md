# GANGLIA Ganglia-MINI-S Setup Status

## Current Status: Audio Working, TTS Issues

### ✅ Completed
- Identified working microphone: Device 14 (pulse) with mono @ 16kHz
- Speakers working and verified
- VAD mode successfully activated
- Mic + Speaker roundtrip working (Ganglia can hear and respond)

### 🐛 Current Issues

**Issue 1: Parallel TTS File Overwriting**
- When generating TTS for multiple sentences in parallel, all files get the same timestamp
- Files named `processed_20251021-162339.mp3` (same name for all 3)
- They overwrite each other, so only the last one survives
- Result: Same sentence plays N times where N = number of sentences

**Root Cause**: Timestamp in filename only has second precision:
```python
# Line 303 in tts.py
timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')  # No milliseconds!
```

**Fix**: Add milliseconds or unique thread ID to filename

**Issue 2: Chipmunk Voice (Audio Effects)**
- Audio effects set to `pitch=-20.0` (maximum pitch drop)
- Should make voice deeper, but sounds like chipmunk instead
- Possible causes:
  - Pitch parameter might be inverted?
  - Sample rate issue?
  - Need to test with different pitch values

**Root Cause**: Line 264 in tts.py:
```python
pitch=-20.0,  # Maximum pitch drop
```

## Next Steps
1. Fix timestamp collision in parallel TTS (add milliseconds)
2. Fix audio effects pitch (test different values or remove)
3. Update ganglia startup script to use `--device-index 14`
