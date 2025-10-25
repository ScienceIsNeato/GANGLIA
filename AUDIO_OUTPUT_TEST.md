# Audio Output Testing Guide

## What We Built

You asked for "Option B" - where the LLM returns audio directly in the response, skipping the separate TTS step entirely.

**Implementation**: Modified `ChatGPTQueryDispatcher` to optionally use `gpt-4o-audio-preview` with text input and audio output.

---

## How It Works

### With `--audio-output` flag:
```
User speech → Google STT → gpt-4o-audio-preview (text in)
  → (text + audio) out → Audio playback
```

**Key benefit**: Single API call for LLM + audio generation (no separate TTS step!)

### Without flag (current):
```
User speech → Google STT → gpt-4o-mini (text) → Google TTS → Audio
```

---

## Test Command

```bash
python ganglia.py \
  --dictation-type vad \
  --audio-output \
  --audio-voice onyx \
  --timing-analysis
```

**Options**:
- `--audio-voice`: Choose voice (alloy, echo, fable, onyx, nova, shimmer)
- Default is `onyx` (deep, authoritative - good for GANGLIA)

---

## What to Look For

### 1. Timing Comparison

**Look at these lines in the output:**

**Current (Google TTS):**
```
⏱️  [LLM] Response received in 0.93s (51 chars)
⏱️  [TTS] Audio generated in 1.77s
⏱️  TOTAL ROUNDTRIP: 2.70s
```

**With Audio Output:**
```
⏱️  [LLM+AUDIO] Response received in X.XXs (51 chars + audio)
⏱️  [TTS] Audio generated in 0.00s  ← Should be 0!
⏱️  TOTAL ROUNDTRIP: X.XXs
```

### 2. Expected Results

| Metric | Current (4o-mini + Google TTS) | With Audio Output |
|--------|-------------------------------|-------------------|
| LLM Time | 0.6-0.9s | 0.8-1.2s (maybe) |
| TTS Time | 0.3-0.5s | 0.0s ✅ |
| **Total** | **0.9-1.4s** | **0.8-1.2s** (hopefully!) |

**Speed improvement**: 0.2-0.3s faster (maybe more!)

### 3. Cost Impact

- **Current**: ~$0.01 per turn
- **With audio output**: ~$0.10-0.15 per turn
- **Per night** (50 turns): $0.50 → $6.00

**10-15x more expensive** but potentially faster!

---

## Comparison Test Protocol

### Step 1: Baseline (Current Setup)
```bash
python ganglia.py --dictation-type vad --timing-analysis
```

Note the timing breakdown for 3-5 turns.

### Step 2: Audio Output Test
```bash
python ganglia.py --dictation-type vad --audio-output --timing-analysis
```

Note the timing breakdown for 3-5 turns.

### Step 3: Compare

Fill in this table:

| Metric | Current | Audio Output | Difference |
|--------|---------|--------------|------------|
| LLM Time | ___s | ___s | ___s |
| TTS Time | ___s | ___s | ___s |
| **Total** | ___s | ___s | ___s |

**Is it faster?** Yes / No

**By how much?** ___s

**Worth 10x cost?** Yes / No / Maybe

---

## Voice Options

Try different voices to find the best GANGLIA voice:

```bash
# Deep and authoritative (default)
--audio-voice onyx

# Slightly deeper
--audio-voice echo

# British accent
--audio-voice fable

# Neutral
--audio-voice alloy

# Warm and friendly
--audio-voice nova

# Soft and gentle
--audio-voice shimmer
```

---

## Implementation Notes

### What Changed:

1. **`query_dispatch.py`**:
   - Added `audio_output` and `audio_voice` parameters to `__init__`
   - Modified `send_query()` to return `(text, audio_file)` when `audio_output=True`
   - Uses `gpt-4o-audio-preview` model with `modalities=["text", "audio"]`

2. **`conversational_interface.py`**:
   - Detects tuple response from query dispatcher
   - Skips TTS entirely when audio is included
   - Passes audio file directly to playback

3. **`parse_inputs.py`** & **`ganglia.py`**:
   - Added `--audio-output` and `--audio-voice` CLI flags
   - Pass flags to query dispatcher initialization

### What It Does:

- Text input goes to `gpt-4o-audio-preview`
- Model returns BOTH text (for logging) AND audio (base64 encoded)
- Audio is decoded and saved as WAV file
- Playback happens immediately
- TTS step is completely skipped

---

## Troubleshooting

### Error: "model does not exist"
- `gpt-4o-audio-preview` might not be available in your account yet
- Try without `--audio-output` flag

### Audio sounds weird
- Try different voices with `--audio-voice`
- Check audio file in `/tmp/GANGLIA/tts/audio_response_*.wav`

### Still slow
- Check timing breakdown - LLM+AUDIO time should include everything
- Compare to baseline without `--audio-output`

---

## Decision Point

After testing, decide:

**Option A: Keep Current Setup**
- ✅ Cheapest ($0.50/night)
- ✅ Fast enough (2-2.5s roundtrip)
- ✅ Reliable

**Option B: Use Audio Output**
- ✅ Potentially faster (0.2-0.3s savings)
- ✅ Single API call (simpler)
- ❌ 10-15x more expensive ($6/night)

**Recommendation**: Test it, measure it, then decide if the speed is worth the cost! 🎃

