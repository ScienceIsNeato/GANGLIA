# OpenAI TTS Quick Start

## What Is It?

OpenAI has a **dedicated Text-to-Speech API** that's separate from their chat completions. You were asking about models that "just return speech" - this is it!

## Three Ways to Get Audio from OpenAI:

### 1. **OpenAI TTS API** (What We Just Implemented!) ⚡
```
Text → OpenAI TTS API → Audio
```
- **Endpoint**: `client.audio.speech.create()`
- **Cost**: $15/1M characters (same as Google!)
- **Speed**: `tts-1` model optimized for low latency
- **Voices**: 6 options (we're using `onyx` - deep voice)
- **Benefit**: Potentially faster than Google since same provider as LLM

### 2. **Chat Completions with Audio Output** (Not Implemented)
```
Text → GPT-4o-audio-preview → Text + Audio
```
- **Endpoint**: `client.chat.completions.create()` with `modalities=["text", "audio"]`
- **Model**: `gpt-4o-audio-preview`
- **Benefit**: Single API call for LLM + TTS
- **Drawback**: More expensive, requires model change

### 3. **Realtime API** (Your Experiments)
```
Audio → GPT-4o-audio → Audio
```
- **Your files**: `realtime_api_working.py`, `realtime_api_debug.py`
- **Most complex, highest cost, lowest latency**
- **Save for November!**

---

## How to Use OpenAI TTS (NOW!)

### Command:
```bash
python ganglia.py \
  --dictation-type vad \
  --tts-interface openai \
  --timing-analysis
```

### What Changes:
- ❌ Google TTS (was using this)
- ✅ OpenAI TTS (now using this)
- Everything else stays the same!

### Expected Results:
- Potentially 0.1-0.2s faster TTS generation
- Same cost as Google
- One less provider to manage

---

## Voice Options

The default is `onyx` (deep, authoritative), but you can change it in `parse_inputs.py`:

```python
return OpenAITTS(voice="onyx")  # Change to any of these:
```

- `alloy` - Neutral and balanced
- `echo` - Slightly deeper
- `fable` - British accent
- `onyx` - Deep and authoritative ⭐ (current)
- `nova` - Warm and friendly
- `shimmer` - Soft and gentle

---

## Testing Strategy

### Test 1: With Google TTS (baseline)
```bash
python ganglia.py --dictation-type vad --timing-analysis
```
Note the TTS timings.

### Test 2: With OpenAI TTS
```bash
python ganglia.py --dictation-type vad --tts-interface openai --timing-analysis
```
Compare TTS timings.

Look for lines like:
```
⏱️  [TTS] Audio generated in X.XXs
```

### Expected Improvement:
- 0.1-0.2s faster (maybe more if network locality helps)
- Same or better quality
- Simpler infrastructure

---

## Implementation Details

### What We Added:
1. **`tts_openai.py`** - New TTS implementation
   - Extends `TextToSpeech` base class
   - Supports parallel sentence generation
   - Same interface as GoogleTTS

2. **`parse_inputs.py`** - Added `--tts-interface openai` option

3. **`LLM_MODEL_OPTIONS.md`** - Documentation

### Features Supported:
- ✅ Parallel TTS for multiple sentences
- ✅ Audio concatenation (ffmpeg)
- ✅ Long text chunking (>4000 chars)
- ✅ Error handling and retries
- ✅ Timing instrumentation

---

## Summary

**You asked**: "Does OpenAI have an API that returns speech?"
**Answer**: YES! Three ways actually:

1. **TTS API** (we just implemented this) ✅
2. **Audio modality in chat** (possible future option)
3. **Realtime API** (your experiments)

**Recommendation**: Try option 1 (TTS API) for Halloween. It's a drop-in replacement with potential speed gains and no downside!

