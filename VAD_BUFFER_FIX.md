# VAD Audio Buffer Fix - No More Lost Words!

## Problem
When counting "one, two, three..." the first word ("one") was lost because:
1. Audio triggered VAD detection
2. VAD switched to Google Speech streaming
3. But the triggering audio wasn't sent to Google
4. Result: Lost ~1 second of speech at the beginning

## Solution Implemented
**Audio buffering with prepending**

### How It Works
1. **Continuous Buffering** (Idle Mode):
   - VAD constantly records audio into a rolling buffer
   - Buffer keeps last 2 seconds of audio (configurable)
   - Oldest chunks are dropped as new ones arrive

2. **Detection Trigger**:
   - When speech detected, VAD activates
   - Buffer is preserved (not discarded!)

3. **Stream Prepending** (Active Mode):
   - Buffered audio (last 2 seconds) is sent to Google FIRST
   - Then live audio stream continues normally
   - Google receives complete speech from the beginning!

### Technical Details

**Buffer Size Calculation:**
```
buffer_chunks = (buffer_seconds × sample_rate) / chunk_size
buffer_chunks = (2.0 × 16000) / 1024
buffer_chunks ≈ 31 chunks
```

**With default settings:**
- Sample rate: 16,000 Hz
- Chunk size: 1,024 samples
- Buffer time: 2.0 seconds
- Buffer storage: ~31 chunks (~64KB of audio data)

**Memory Impact:** Minimal (~64KB per GANGLIA instance)

---

## Configuration

Edit `config/vad_config.json`:

```json
{
  "detection": {
    "audio_buffer_seconds": 2.0
  }
}
```

### Adjusting Buffer Size

**Default: 2.0 seconds** - Good for most scenarios

**Increase to 3.0-4.0 if:**
- Still losing first syllables
- Very slow speech detection
- Want maximum safety margin

**Decrease to 1.0-1.5 if:**
- Memory is a concern (unlikely)
- You want less "pre-history" in transcripts
- Audio environment is very quiet (fast detection)

**Note:** There's no downside to larger buffers except slightly more memory usage.

---

## Testing

Try the counting test again:

```bash
python ganglia.py --dictation-type vad
```

Then loudly count: "ONE, TWO, THREE, FOUR, FIVE"

**Expected Result:**
```
💤 Idle mode - Listening for speech (cost-free)...
🎤 Speech detected! Activating conversation mode...
Prepending 28 buffered audio chunks
Active conversation mode - listening...
ONE TWO THREE FOUR FIVE
```

You should now see "ONE" in the transcript!

---

## How This Saves Your Speech

### Before (Lost Audio):
```
Timeline:
[silence] → ONE → TWO → THREE → FOUR
           ↑
           VAD triggers here
           Lost: "ONE"
           Google hears: "TWO THREE FOUR"
```

### After (With Buffer):
```
Timeline:
[silence] → ONE → TWO → THREE → FOUR
           ↑
           VAD triggers here

Buffer contains: [silence, O, N, E]
Google receives: [silence, O, N, E] + [TWO, THREE, FOUR]
Result: "ONE TWO THREE FOUR" ✓
```

---

## Configuration Options

### Aggressive Buffering (Maximum Safety)
```json
{
  "detection": {
    "audio_buffer_seconds": 4.0,
    "speech_confirmation_chunks": 1
  }
}
```
- 4 seconds of buffer
- Instant activation (1 chunk)
- **Best for**: Critical applications where losing ANY speech is unacceptable

### Balanced (Default)
```json
{
  "detection": {
    "audio_buffer_seconds": 2.0,
    "speech_confirmation_chunks": 2
  }
}
```
- 2 seconds of buffer
- Fast but reliable activation
- **Best for**: Most use cases, including party

### Minimal Buffering
```json
{
  "detection": {
    "audio_buffer_seconds": 1.0,
    "speech_confirmation_chunks": 3
  }
}
```
- 1 second of buffer
- More careful activation
- **Best for**: Very noisy environments where false positives are a concern

---

## Real-World Scenarios

### Scenario 1: Guest Says "Hello GANGLIA"
**Without buffer:**
- Detects on "LO"
- Loses: "HEL"
- Hears: "LO GANGLIA"

**With 2s buffer:**
- Detects on "LO"
- Buffer contains: [silence, HE, L]
- Hears: "HELLO GANGLIA" ✓

### Scenario 2: Counting Test
**Without buffer:**
- Detects on "TWO"
- Loses: "ONE"
- Result: Confused AI ("Why start at two?")

**With 2s buffer:**
- Detects on "TWO"
- Buffer contains: [ONE]
- Result: Complete count ✓

---

## Memory & Performance

**Memory Usage:**
- 2.0 seconds: ~64 KB
- 3.0 seconds: ~96 KB
- 4.0 seconds: ~128 KB

**CPU Impact:** None (buffer is just a list in memory)

**Cost Impact:** None (buffer is local, not sent to Google until activated)

**Latency:** Zero additional latency (buffer is in RAM)

---

## Advanced: Buffer Visualization

When running with debug logging, you'll see:

```
💤 Idle mode - Listening for speech (cost-free)...
[Buffer: 15 chunks] [Buffer: 16 chunks] [Buffer: 17 chunks]...
🎤 Speech detected! Activating conversation mode...
Prepending 31 buffered audio chunks  ← Your saved audio!
Active conversation mode - listening...
```

---

## Summary

✅ **Problem Solved**: No more lost first words
✅ **Zero Cost**: Buffer is local and free
✅ **Zero Latency**: Buffer is in RAM
✅ **Configurable**: Adjust `audio_buffer_seconds` to taste
✅ **Transparent**: Works automatically, no code changes needed

**The audio that triggers VAD is now captured and sent to Google!**
