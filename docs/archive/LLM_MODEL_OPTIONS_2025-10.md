# LLM and TTS Options for GANGLIA

## Current Setup (October 2024)

**LLM Model**: `gpt-4o-mini` (text-based)
**TTS**: Google Cloud TTS (default) or OpenAI TTS (optional)
**Flow**: User speech → Google STT → GPT-4o-mini → TTS → Audio playback

---

## Option 1: Keep GPT-4o-mini (RECOMMENDED for October)

**Current model in use**

### Pros:
- ✅ **Cheapest** option (~$0.15/1M input tokens, $0.60/1M output)
- ✅ Already optimized with streaming + parallel TTS
- ✅ Very fast response times for short queries (0.6-0.9s TTFB)
- ✅ Known quantity - stable and reliable

### Cons:
- ❌ Not the absolute fastest available model
- ❌ Requires separate TTS step

### Cost per conversation turn:
- **~$0.005-0.01** (very cheap!)

---

## Option 2: Upgrade to GPT-4o (Text)

**Model**: `gpt-4o-2024-11-20` (latest text-based model)

### Pros:
- ✅ 20-30% faster response times
- ✅ Better reasoning for complex queries
- ✅ Same API, just change model parameter

### Cons:
- ❌ **17x more expensive** ($2.50 in / $10.00 out per 1M tokens)
- ❌ Still requires separate TTS step
- ❌ Marginal latency improvement for cost

### Cost per conversation turn:
- **~$0.08-0.15** (17x more than current!)

### To enable:
```python
# In query_dispatch.py, change:
model="gpt-4o-mini"
# to:
model="gpt-4o-2024-11-20"
```

---

## Option 3: OpenAI Realtime API with Audio (EXPERIMENTAL)

**Model**: `gpt-4o-audio-preview` (native audio I/O)
**Flow**: User speech → Audio to Realtime API → Audio response directly (NO TTS!)

### What's Different:
This is what you were asking about! The model **outputs audio directly** instead of text.

### Pros:
- ✅ **No TTS step needed** (~0.3-0.5s latency savings)
- ✅ More natural prosody and emotional intonation
- ✅ Single API call instead of LLM + TTS pipeline
- ✅ Potentially lowest total latency

### Cons:
- ❌ **3-4x more expensive** than current setup (~$0.06/min input, $0.24/min output)
- ❌ WebSocket-based architecture (requires major refactor)
- ❌ No text transcript for logging/debugging
- ❌ Still in preview (may have breaking changes)
- ❌ You already have `realtime_api_working.py` experimenting with this

### Cost per conversation turn:
- **~$0.02-0.04** (3-4x more than current)

### Current status:
You have experimental implementations:
- `realtime_api_working.py`
- `realtime_api_debug.py`

These would replace the entire conversation pipeline.

---

## Recommendation Summary

### For Halloween 2024 Party (Immediate):
**KEEP `gpt-4o-mini`** ✅

Why:
- Already very fast with streaming (0.6-0.9s TTFB)
- 0.5s silence threshold will bring roundtrip to ~2.0-2.5s
- Cheapest option by far
- Stable and reliable

### For November Experimentation:
**TRY Realtime API** 🧪

Why:
- Native audio I/O eliminates TTS latency
- Most natural-sounding responses
- Truly cutting-edge technology
- Worth the cost for experimentation

### If You Need Fastest Text Model:
**GPT-4o-2024-11-20** ⚡ (but $$$)

Only if:
- Cost doesn't matter
- Need absolute fastest text responses
- Want better reasoning for complex queries

---

## Expected Latency Comparison

Based on your timing analysis:

| Setup | TTFB | Total Roundtrip | Cost/Turn |
|-------|------|-----------------|-----------|
| **Current (4o-mini)** | 0.6-0.9s | 2.8-3.4s | $0.01 |
| **With 0.5s silence** | 0.6-0.9s | **2.0-2.5s** ✅ | $0.01 |
| **GPT-4o text** | 0.4-0.7s | 1.8-2.3s | $0.15 |
| **Realtime Audio** | 0.3-0.5s | **1.5-2.0s** ⚡ | $0.03 |

---

## How to Change Models

### Switch to GPT-4o (text):
```bash
# Edit query_dispatch.py lines 70 and 113:
model="gpt-4o-mini"  # Change to:
model="gpt-4o-2024-11-20"
```

### Switch to Realtime API (audio):
```bash
# This requires architectural changes - use your existing:
python realtime_api_working.py
```

---

---

## TTS Options

### Current: Google Cloud TTS
- **Cost**: ~$16/1M characters
- **Latency**: ~0.3-0.5s for short responses
- **Quality**: Excellent, many voices available
- **Current voice**: `en-US-Casual-K`

### Alternative: OpenAI TTS (NEW!)
- **Cost**: $15/1M characters (slightly cheaper!)
- **Latency**: Potentially faster (same provider as LLM)
- **Quality**: Excellent, 6 voices available
- **Recommended voice**: `onyx` (deep, authoritative - matches GANGLIA)

**To use OpenAI TTS:**
```bash
python ganglia.py --dictation-type vad --tts-interface openai --timing-analysis
```

**Voices available:**
- `alloy` - Neutral and balanced
- `echo` - Slightly deeper
- `fable` - British accent
- `onyx` - Deep and authoritative ⭐ (default for GANGLIA)
- `nova` - Warm and friendly
- `shimmer` - Soft and gentle

---

## Bottom Line

**For Halloween 2024:**
- ✅ **Keep `gpt-4o-mini`** for LLM (best cost/performance)
- ⚡ **Try OpenAI TTS** (`--tts-interface openai`) - potentially faster since same provider as LLM
- ✅ **0.5s silence threshold** should get you to ~2-2.5s roundtrip

**Expected improvements with OpenAI TTS:**
- Potential 0.1-0.2s latency reduction (API locality)
- Slightly cheaper ($15 vs $16 per 1M chars)
- Simpler infrastructure (one provider for LLM + TTS)

The Realtime API is the "future" with native audio, but save it for post-Halloween experimentation when you have time to refactor the architecture.
