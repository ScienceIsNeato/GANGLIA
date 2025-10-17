# VAD Configuration - Quick Reference

## Problem Solved
User reported: "I need to speak very loudly before it triggers"

## Solution Implemented
Created configurable VAD settings with immediate sensitivity fix.

---

## Quick Start

### Current Settings (Already Applied)
Your `config/vad_config.json` is now set to:
- `energy_threshold: 300` (40% more sensitive than default 500)
- `speech_confirmation_chunks: 2` (33% faster activation than default 3)

**Just restart GANGLIA and it should work better!**

```bash
python ganglia.py --dictation-type vad
```

---

## If Still Not Sensitive Enough

### Option 1: Try the testing tool
```bash
python utils/test_vad_sensitivity.py --duration 30
```

This will show you:
- Your actual audio energy levels
- Specific recommendations for your environment
- Real-time visualization of what VAD "sees"

### Option 2: Make it MORE sensitive
Edit `config/vad_config.json`:

```json
{
  "detection": {
    "energy_threshold": 200,  // Even more sensitive
    "speech_confirmation_chunks": 1  // Instant activation
  }
}
```

### Option 3: If it's TOO sensitive now (triggers on noise)
```json
{
  "detection": {
    "energy_threshold": 400,  // Less sensitive
    "speech_confirmation_chunks": 3  // More confirmation needed
  }
}
```

---

## Files Created

1. **`config/vad_config.json`** - Live configuration (already tuned for you)
2. **`config/vad_config.json.template`** - Backup/template with defaults
3. **`utils/test_vad_sensitivity.py`** - Testing tool to find optimal settings
4. **`VAD_TUNING_GUIDE.md`** - Complete tuning instructions and troubleshooting

---

## What Each Setting Does

### `energy_threshold` (Most Important!)
- **What**: Minimum audio volume to detect as speech
- **Default**: 500
- **Your setting**: 300 (more sensitive)
- **Lower = more sensitive** (picks up quiet speech)
- **Higher = less sensitive** (ignores background noise)

### `speech_confirmation_chunks`
- **What**: How many consecutive "loud" chunks = real speech
- **Default**: 3
- **Your setting**: 2 (faster)
- **Lower = faster activation** (but may trigger on noise spikes)
- **Higher = more reliable** (but slower)

### `chunk_size`
- **What**: Audio buffer size (technical)
- **Default**: 1024
- **Your setting**: 1024 (unchanged)
- **Rarely needs adjustment**

### `audio_buffer_seconds` (NEW!)
- **What**: How much audio to keep buffered BEFORE VAD triggers
- **Default**: 2.0 seconds
- **Your setting**: 2.0 seconds
- **Why**: Prevents losing the first word when VAD activates
- **Typical range**: 1.0-3.0 seconds
- **Note**: This audio gets prepended to the Google Speech stream, so you don't miss the beginning of speech!

---

## Testing Workflow

1. **Test current settings:**
   ```bash
   python ganglia.py --dictation-type vad
   ```

2. **If not right, run diagnostic:**
   ```bash
   python utils/test_vad_sensitivity.py
   ```

3. **Update config based on recommendations**

4. **Repeat until perfect**

---

## Common Scenarios

### Quiet Home Office
```json
"energy_threshold": 250,
"speech_confirmation_chunks": 2
```

### Normal Living Room
```json
"energy_threshold": 400,
"speech_confirmation_chunks": 3
```

### Noisy Halloween Party
```json
"energy_threshold": 800,
"speech_confirmation_chunks": 4
```

---

## Advanced: Multiple Configs

For different environments, you can save multiple configs:

```bash
# Save your quiet environment config
cp config/vad_config.json config/vad_config_quiet.json

# Create a party config
# (edit vad_config.json with higher thresholds)

# Save party config
cp config/vad_config.json config/vad_config_party.json

# Switch between them:
cp config/vad_config_quiet.json config/vad_config.json  # For testing
cp config/vad_config_party.json config/vad_config.json   # For party night
```

---

## Troubleshooting

### "Still need to speak loudly"
→ Lower `energy_threshold` to 200 or even 150

### "Triggers on every little sound"
→ Raise `energy_threshold` to 500 or 600

### "Misses the first word I say"
→ Lower `speech_confirmation_chunks` to 1

### "Activates randomly"
→ Raise `speech_confirmation_chunks` to 4 or 5

---

## No Need to Edit Code!

All tuning is done via `config/vad_config.json` - no Python coding required.

Changes take effect immediately on next GANGLIA restart.

---

## Default vs Current Settings

| Setting | Default | Your Current | Change |
|---------|---------|--------------|--------|
| energy_threshold | 500 | 300 | 40% more sensitive |
| speech_confirmation_chunks | 3 | 2 | 33% faster |
| Result | Normal | More sensitive, faster | Better for quiet speech |

---

**For detailed troubleshooting, see `VAD_TUNING_GUIDE.md`**
