# Timing Analysis Guide

This guide explains how to use the `--timing-analysis` flag to measure and optimize conversation pipeline performance.

## Enabling Timing Analysis

Run GANGLIA with the `--timing-analysis` flag:

```bash
python ganglia.py --dictation-type vad --timing-analysis
```

## What Gets Measured

The timing analysis tracks every step from when you stop speaking to when the AI starts playing audio:

### 1. **Speech-to-Text (STT) Phase**
```
⏱️  [STT] Final transcript received, waiting 1.5s for silence...
⏱️  [STT] Silence detected! User finished speaking.
```

**What this measures**: 
- How long Google Cloud Speech waits after your last word to confirm you're done speaking
- This is controlled by `silence_threshold` in `config/vad_config.json` (currently 1.5s)
- **Tradeoff**: Lower = faster response but might cut you off; Higher = waits longer but won't interrupt

### 2. **LLM Query Phase**
```
⏱️  [LLM] Sending query to OpenAI API (gpt-4o-mini)...
⏱️  [LLM] Response received in 1.23s (142 chars)
```

**What this measures**:
- Network round-trip to OpenAI
- Time for GPT-4o-mini to generate the response
- **Typical Range**: 0.7-2.0s depending on response complexity

**Streaming version** (default for regular conversation):
```
⏱️  [LLM] Starting streaming query to OpenAI API...
⏱️  [LLM] First chunk received (TTFB: 0.42s)
⏱️  [LLM] Streaming sentence: Hello! How can I help you?
⏱️  [LLM] Complete response streamed in 1.15s (142 chars)
```

**TTFB** (Time To First Byte) is critical - this is how fast we can start generating audio!

### 3. **Text-to-Speech (TTS) Phase**
```
⏱️  [TTS] Converting text to speech (142 chars)...
⏱️  [TTS] Audio generated in 0.23s
```

**What this measures**:
- Time for Google Cloud TTS to generate audio
- **Typical Range**: 0.07-0.3s (very fast!)

**Parallel version** (for multi-sentence responses):
```
⏱️  [TTS] Generating TTS for 3 sentences in parallel...
⏱️  [TTS] Audio generated in 0.15s
```

### 4. **Playback Start**
```
⏱️  [PLAYBACK] Starting audio playback NOW! (duration: 3.2s)
```

**This is THE moment** - when you first hear the AI's voice!

### 5. **Overall Summary**
```
============================================================
CONVERSATION TURN TIMING BREAKDOWN
============================================================
User Speaking: 3.42s
Speech-to-Text: 2.13s
LLM Query: 1.23s
Text-to-Speech: 0.23s

⏱️  TOTAL ROUNDTRIP (user stops → AI speaks): 3.59s
============================================================
```

## Understanding the Roundtrip

**Total Roundtrip** = Time from when you stop speaking to when AI audio starts playing

Breakdown:
1. **Silence Detection** (~1.5s) - Waiting to confirm you're done
2. **LLM Processing** (~1.2s) - Generating the response
3. **TTS Generation** (~0.2s) - Converting text to audio
4. **Overhead** (~0.2s) - Python processing, audio buffering, etc.

**Total**: ~3.1s typical

## Tuning for Your Needs

### If Responses Feel Too Slow

**Problem**: 3+ second delay feels sluggish

**Solutions**:
1. **Reduce silence threshold** (fastest, but risky):
   - Edit `config/vad_config.json`
   - Change `silence_threshold` from 1.5s to 1.0s
   - **Warning**: May cut you off if you pause mid-sentence

2. **Already optimized**:
   - ✅ Streaming LLM (starts audio before full response)
   - ✅ Parallel TTS (for multi-sentence responses)
   - ✅ Local VAD (free speech detection)

### If Getting Cut Off Mid-Sentence

**Problem**: AI starts responding before you finish

**Solution**:
- Increase `silence_threshold` in `config/vad_config.json`
- Try 2.0s or 2.5s
- **Trade-off**: Slower response, but won't interrupt you

### If LLM is Slow (>2s consistently)

**Check**:
- Network connection quality
- Query complexity (very long context?)
- Model load (OpenAI service status)

**Already using the fastest affordable option** (gpt-4o-mini)

## Detailed Timing Log Example

```
🎤  [User speaks: "What's the weather like today?"]

⏱️  [STT] Final transcript received, waiting 1.5s for silence...
⏱️  [STT] Silence detected! User finished speaking.
⏱️  [LLM] Starting streaming query to OpenAI API...
⏱️  [LLM] First chunk received (TTFB: 0.38s)
⏱️  [LLM] Streaming sentence: I don't have access to real-time weather data.
⏱️  [TTS] Converting text to speech (48 chars)...
⏱️  [TTS] Audio generated in 0.15s
⏱️  [PLAYBACK] Starting audio playback NOW!

============================================================
TOTAL ROUNDTRIP: 2.03s
============================================================
```

**Analysis**: 
- Silence wait: 1.5s (configurable)
- LLM TTFB: 0.38s (good!)
- TTS: 0.15s (excellent!)
- Total: 2.03s (very responsive!)

## Comparison: Before vs After Optimizations

### Before Optimizations
```
Silence: 2.5s
LLM (wait for full): 1.5s
TTS (serial): 0.4s
───────────────────
Total: 4.4s
```

### After Optimizations
```
Silence: 1.5s (-1.0s)
LLM (streaming TTFB): 0.4s (-1.1s perceived)
TTS (parallel): 0.15s (-0.25s)
───────────────────
Total: 2.05s (-2.35s improvement!)
```

## FAQ

**Q: Why is silence_threshold so important?**  
A: It's literally how long the system waits after you stop talking before processing begins. It's the single largest component of the roundtrip delay.

**Q: Can I set silence_threshold to 0?**  
A: No. Google Cloud Speech needs some silence to finalize the transcript. Minimum practical value is ~0.5s, but you'll likely get cut off. 1.5s is a good balance.

**Q: What's TTFB?**  
A: "Time To First Byte" - how quickly the LLM starts responding. With streaming, we can start TTS generation after the first sentence, not waiting for the full response.

**Q: Why not use a faster model?**  
A: GPT-4o is only 20-30% faster but costs 17x more. Not worth it when we've already achieved 2-3s roundtrip times with gpt-4o-mini.

**Q: Can we pre-generate audio?**  
A: For common phrases like "Hello!", yes. For dynamic conversation, no - we don't know what the AI will say until it says it.

## Recommended Settings

**For Normal Conversation** (current):
```json
{
  "silence_threshold": 1.5,
  "conversation_timeout": 5
}
```

**For Thoughtful/Slow Speakers**:
```json
{
  "silence_threshold": 2.5,
  "conversation_timeout": 10
}
```

**For Quick Back-and-Forth**:
```json
{
  "silence_threshold": 1.0,
  "conversation_timeout": 5
}
```
**Warning**: May cut you off!

---

## Summary

Enable timing analysis to see **exactly** where time is spent in your conversation pipeline. The biggest factor you can control is `silence_threshold` - tune it to balance response speed vs being cut off mid-sentence.

Current setup achieves **~2-3s roundtrip** with zero cost increase!

