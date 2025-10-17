# VAD Tuning Guide - Getting the Sensitivity Right

## Quick Fix for Your Issue: "Need to speak very loudly"

Edit `config/vad_config.json` and change:

```json
{
  "detection": {
    "energy_threshold": 300,  // Changed from 500 → MORE SENSITIVE
    "speech_confirmation_chunks": 2  // Changed from 3 → FASTER ACTIVATION
  }
}
```

Then restart GANGLIA and test. If still not sensitive enough, try `energy_threshold: 200`.

---

## Complete Tuning Process

### Step 1: Test Your Environment

```bash
cd /Users/pacey/Documents/SourceCode/GANGLIA
source venv/bin/activate
python utils/test_vad_sensitivity.py --duration 30
```

This will:
- Show real-time audio energy levels
- Test background noise levels
- Give you specific recommendations for your environment

### Step 2: Understand the Key Settings

#### `energy_threshold` (Most Important!)
**What it does**: Minimum audio energy to trigger speech detection

**Default**: 500
**Range**: 100-1000+
**Your issue**: 500 is too high for your environment

**Recommendations**:
- **Quiet room**: 200-300
- **Normal room**: 400-500 (default)
- **Noisy party**: 700-1000

#### `speech_confirmation_chunks`
**What it does**: How many consecutive loud chunks = real speech (not noise spike)

**Default**: 3
**Range**: 1-5
**Your issue**: 3 chunks might be adding delay

**Recommendations**:
- **1 chunk**: Instant activation, may trigger on noise
- **2 chunks**: Fast activation, good balance (RECOMMENDED FOR YOU)
- **3 chunks**: Default, reliable but slower
- **4-5 chunks**: Very reliable but slowest

#### `chunk_size`
**What it does**: Audio buffer size (affects responsiveness)

**Default**: 1024
**Range**: 512-2048
**Note**: Smaller = more responsive but more CPU

---

## Quick Presets

Copy one of these into your `config/vad_config.json`:

### Preset 1: Maximum Sensitivity (For You!)
```json
{
  "detection": {
    "energy_threshold": 250,
    "speech_confirmation_chunks": 2,
    "chunk_size": 1024
  },
  "timing": {
    "silence_threshold": 2.5,
    "conversation_timeout": 30
  }
}
```
**Best for**: Quiet environments, want instant activation

---

### Preset 2: Balanced (Default)
```json
{
  "detection": {
    "energy_threshold": 500,
    "speech_confirmation_chunks": 3,
    "chunk_size": 1024
  },
  "timing": {
    "silence_threshold": 2.5,
    "conversation_timeout": 30
  }
}
```
**Best for**: Normal indoor environments

---

### Preset 3: Noisy Party Mode
```json
{
  "detection": {
    "energy_threshold": 800,
    "speech_confirmation_chunks": 4,
    "chunk_size": 1024
  },
  "timing": {
    "silence_threshold": 3.0,
    "conversation_timeout": 30
  }
}
```
**Best for**: Halloween party with music and crowd noise

---

## Troubleshooting Common Issues

### "Too sensitive - triggers on background noise"
✅ **Solution**: INCREASE `energy_threshold`
- Try: 600, 700, 800, 1000
- Or INCREASE `speech_confirmation_chunks` to 4-5

### "Not sensitive enough - need to speak loudly" (YOUR ISSUE)
✅ **Solution**: DECREASE `energy_threshold`
- Try: 400, 300, 200 (in that order)
- AND DECREASE `speech_confirmation_chunks` to 2

### "Activation is slow - misses first word"
✅ **Solution**: DECREASE `speech_confirmation_chunks`
- Try: 2 or even 1
- Or DECREASE `chunk_size` to 512

### "Cuts off while I'm still talking"
✅ **Solution**: INCREASE `silence_threshold`
- Try: 3.0, 3.5, 4.0 seconds
- This controls how long silence = "done speaking"

### "Stays in conversation mode too long"
✅ **Solution**: DECREASE `conversation_timeout`
- Try: 20, 15 seconds
- This returns to idle (free) mode faster

---

## Iterative Tuning Process

1. **Start with testing script**:
   ```bash
   python utils/test_vad_sensitivity.py
   ```

2. **Note your numbers**:
   - Background noise energy: ___
   - Normal speech energy: ___
   - Quiet speech energy: ___

3. **Set threshold**:
   - Quiet room: threshold = (background + quiet_speech) / 2
   - Noisy room: threshold = (noise + normal_speech) / 2

4. **Test with GANGLIA**:
   ```bash
   python ganglia.py --dictation-type vad
   ```

5. **Adjust and repeat** until it feels right

---

## For Your Specific Issue

Based on "need to speak very loudly", I recommend:

**Step 1**: Update `config/vad_config.json`:
```json
{
  "detection": {
    "energy_threshold": 300,
    "speech_confirmation_chunks": 2,
    "chunk_size": 1024
  }
}
```

**Step 2**: Test:
```bash
python ganglia.py --dictation-type vad
```

**Step 3**: If still not sensitive enough:
- Lower `energy_threshold` to 200
- Lower `speech_confirmation_chunks` to 1

**Step 4**: If TOO sensitive (triggers on noise):
- Raise `energy_threshold` back up
- But keep `speech_confirmation_chunks` at 2

---

## Environment-Specific Recommendations

### Testing at Home (Quiet)
```
energy_threshold: 250-350
speech_confirmation_chunks: 2
```

### Halloween Party (Loud Music + Crowd)
```
energy_threshold: 800-1000
speech_confirmation_chunks: 4
```

**Pro tip**: You can swap configs before the party!

```bash
# Testing at home
cp config/vad_config_quiet.json config/vad_config.json

# Party night
cp config/vad_config_party.json config/vad_config.json
```

---

## Advanced: Real-Time Tuning

While GANGLIA is running, watch the console output:
```
VAD Settings: energy_threshold=500, confirmation_chunks=3
```

If you see in logs:
- "💤 Idle mode" constantly → Good, waiting for speech
- "🎤 Speech detected!" on background noise → Threshold too low
- No activation when you speak → Threshold too high

---

## Quick Reference Card

| Issue | Solution | Config Change |
|-------|----------|---------------|
| Too sensitive | Increase threshold | 500 → 700 |
| Not sensitive | Decrease threshold | 500 → 300 |
| Slow activation | Fewer chunks | 3 → 2 |
| False positives | More chunks | 3 → 4 |
| Misses first word | Faster detection | chunks: 1-2 |
| Cuts off mid-sentence | More silence time | silence: 3.5s |

---

## Need Help?

Run the testing script and send me the output:
```bash
python utils/test_vad_sensitivity.py > vad_test_results.txt
```

The recommendations at the end will tell you exactly what settings to use.
