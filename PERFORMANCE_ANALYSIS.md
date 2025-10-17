# GANGLIA Performance Analysis & Optimization Report

**Date**: October 17, 2025  
**Branch**: `feature/roundtrip_speed`  
**Goal**: Reduce conversation roundtrip latency by 30-50% while maintaining or reducing costs

---

## Executive Summary

Current end-to-end roundtrip latency (user stops speaking → AI starts speaking): **~3.5-5s estimated**

Breakdown (baseline measurements):
- **STT (Speech-to-Text)**: ~0.5-1s (VAD + Google Cloud Speech)
- **LLM (Language Model)**: ~1.2s average (gpt-4o-mini)
- **TTS (Text-to-Speech)**: ~0.1-0.3s (Google Cloud TTS)
- **Silence Detection**: 2.5s (configurable)
- **Total Processing**: ~1.5-2s (LLM + TTS)

**Key Insight**: The largest single bottleneck is the **silence threshold (2.5s)** which waits for the user to stop speaking. The second largest is **LLM response time (~1.2s)**.

---

## Baseline Performance Metrics

### Test Environment
- Model: gpt-4o-mini
- TTS: Google Cloud Text-to-Speech
- STT: Google Cloud Speech-to-Text with VAD
- Date: October 17, 2025

### Results

#### LLM Query Latency
| Metric | Value |
|--------|-------|
| Mean | 1.17s |
| Median | 1.16s |
| Min | 0.71s |
| Max | 1.61s |

**Observation**: GPT-4o-mini shows consistent sub-second to 1.5s response times for short queries. Longer, more complex queries trend toward 1.5-2s.

#### TTS Generation Latency
| Metric | Value |
|--------|-------|
| Mean | 0.13s |
| Median | 0.09s |
| Min | 0.07s |
| Max | 0.31s |

**Observation**: Google Cloud TTS is very fast (< 0.3s for most requests). First request shows higher latency (~0.3s) likely due to connection setup.

#### End-to-End Latency (LLM + TTS)
| Metric | Value |
|--------|-------|
| Mean | 1.58s |
| Median | 1.77s |
| Min | 0.91s |
| Max | 2.06s |

**Observation**: Combined LLM + TTS processing averages ~1.6s. With VAD silence threshold (2.5s) + STT (~0.5s), total roundtrip is approximately **4.5-5s**.

---

## API Research & Comparison

### Language Models (LLM)

#### Option 1: GPT-4o-mini (Current) ✅
- **Speed**: 0.7-1.6s per query
- **Cost**: $0.150 per 1M input tokens, $0.600 per 1M output tokens
- **Pros**: Already integrated, good speed, very affordable
- **Cons**: Slightly slower than GPT-4o for some queries

#### Option 2: GPT-4o
- **Speed**: 0.5-1.2s per query (estimated 20-30% faster)
- **Cost**: $2.50 per 1M input tokens, $10.00 per 1M output tokens
- **Pros**: Faster response times, better quality
- **Cons**: **⚠️ 16-20x more expensive** than 4o-mini

**Cost Analysis for GPT-4o**:
- Current: ~$0.01 per 100 queries (4o-mini)
- With GPT-4o: ~$0.17 per 100 queries
- **Cost increase**: ~17x
- **Speed gain**: ~0.3-0.5s per query

**Recommendation**: ❌ **Stick with GPT-4o-mini**. The 17x cost increase is not justified for a 0.3-0.5s speed improvement when we can achieve 2-3s improvements through other optimizations (streaming, parallelization, tuning).

#### Option 3: GPT-4o-mini with Streaming ⭐ RECOMMENDED
- **Speed**: Start TTS generation after first sentence (~0.5-1s earlier)
- **Cost**: Same as current (no cost increase)
- **Pros**: Perceived latency reduction of 1-3s, zero cost impact
- **Cons**: Requires code changes to handle streaming

**Estimated Improvement**: **1-3 seconds** reduction in perceived latency

---

### Text-to-Speech (TTS)

#### Option 1: Google Cloud TTS (Current) ✅
- **Speed**: 0.07-0.31s
- **Cost**: $16 per 1M characters
- **Pros**: Very fast, reliable, good quality
- **Cons**: None significant

#### Option 2: OpenAI TTS (`tts-1`)
- **Speed**: 0.2-0.8s (estimated, varies by text length)
- **Cost**: $15 per 1M characters
- **Pros**: Slightly cheaper, integrated with OpenAI ecosystem
- **Cons**: Potentially slower than Google, requires integration

**Cost Comparison**:
- 1000 conversations averaging 100 chars each = 100,000 chars
- Google: $1.60
- OpenAI: $1.50
- **Savings**: $0.10 per 1000 conversations (negligible)

**Recommendation**: ⚠️ **Keep Google Cloud TTS as primary**. OpenAI TTS may be slightly slower and the cost savings are negligible. Consider OpenAI TTS as a secondary option only if integration is trivial or for voice variety.

#### Option 3: OpenAI TTS (`tts-1-hd`)
- **Speed**: 0.3-1.0s (estimated)
- **Cost**: $30 per 1M characters
- **Pros**: Higher quality audio
- **Cons**: **2x more expensive** than current, slower

**Recommendation**: ❌ **Not recommended** for conversation pipeline where speed is critical.

---

### Speech-to-Text (STT)

#### Option 1: Google Cloud Speech + VAD (Current) ✅
- **Speed**: ~0.5-1s after silence detection
- **Cost**: Optimized with VAD (~$1-2/day vs $20/day without VAD)
- **Pros**: Already optimized for cost, good quality
- **Cons**: None

#### Option 2: OpenAI Whisper API
- **Speed**: 0.5-2s (file-based, not streaming)
- **Cost**: $0.006 per minute
- **Pros**: Good quality
- **Cons**: Not suitable for real-time streaming, no streaming API

**Recommendation**: ✅ **Keep current Google Cloud Speech + VAD**. Already optimized for cost and performance. Whisper API is not designed for real-time streaming conversations.

---

## Recommended Optimizations (Prioritized)

### 🥇 Priority 1: Quick Wins (No Cost Impact)

#### 1.1 Reduce Silence Threshold ⭐
**Current**: 2.5s  
**Proposed**: 1.5-2.0s  
**Estimated Improvement**: 0.5-1.0s  
**Cost Impact**: None  
**Effort**: Trivial (config change)

**Action**: Update `config/vad_config.json`:
```json
"silence_threshold": 1.5
```

**Risk**: May cut off users who speak slowly. Test and adjust.

---

#### 1.2 Enable Streaming LLM Responses ⭐⭐⭐
**Estimated Improvement**: 1-3s reduction in perceived latency  
**Cost Impact**: None  
**Effort**: Medium (code changes in `query_dispatch.py` and `conversational_interface.py`)

**How it works**:
```
Current (Serial):
LLM Query (1.2s) → [wait] → Full Response → TTS (0.1s) → Playback
Total: 1.3s before audio starts

Optimized (Streaming):
LLM Query Start → Stream first sentence (0.5s) → Start TTS → Playback
Total: 0.6s before audio starts
SAVINGS: 0.7s, plus user hears response while AI is still generating
```

**Implementation**:
```python
# query_dispatch.py
def send_query_streaming(self, current_input):
    """Stream LLM response and yield sentences as they complete."""
    stream = self.client.chat.completions.create(
        model="gpt-4o-mini",
        messages=self.messages,
        stream=True
    )
    
    current_sentence = ""
    for chunk in stream:
        if chunk.choices[0].delta.content:
            current_sentence += chunk.choices[0].delta.content
            
            # Yield complete sentences
            if current_sentence.endswith(('.', '!', '?')):
                yield current_sentence.strip()
                current_sentence = ""
    
    # Yield any remaining text
    if current_sentence.strip():
        yield current_sentence.strip()
```

---

#### 1.3 Parallelize TTS for Multi-Sentence Responses ⭐⭐
**Estimated Improvement**: 0.5-2.0s for responses with 3+ sentences  
**Cost Impact**: None  
**Effort**: Medium (code changes in `tts.py`)

**How it works**:
```
Current (Serial):
Sentence 1 TTS (0.2s) → Sentence 2 TTS (0.2s) → Sentence 3 TTS (0.2s)
Total: 0.6s

Optimized (Parallel):
All 3 sentences TTS concurrently (max 0.2s)
Total: 0.2s
SAVINGS: 0.4s
```

**Implementation**:
```python
from concurrent.futures import ThreadPoolExecutor

def convert_text_to_speech_parallel(self, sentences, voice_id=None):
    """Generate TTS for multiple sentences in parallel."""
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [
            executor.submit(self.convert_text_to_speech, s, voice_id)
            for s in sentences
        ]
        results = [f.result() for f in futures]
    
    # Concatenate audio files
    return self.concatenate_audio_files([r[1] for r in results if r[0]])
```

---

### 🥈 Priority 2: Advanced Optimizations (Optional)

#### 2.1 Pre-generate Common Responses
Cache audio for frequent responses:
- Greetings ("Hello!", "Hi there!")
- Acknowledgments ("Got it", "Okay", "Sure")
- Error messages

**Estimated Improvement**: 0.1-0.3s for cached responses  
**Effort**: Low

---

#### 2.2 Response Caching
Cache AI responses for repeated queries.

**Estimated Improvement**: 1.2s for cached queries  
**Effort**: Medium  
**Complexity**: Requires cache invalidation strategy

---

## Cost Summary

### Current Costs (Estimated)
- **LLM**: gpt-4o-mini @ ~$0.01 per 100 queries
- **TTS**: Google Cloud @ ~$0.16 per 100 queries (100 chars avg)
- **STT**: Google Cloud + VAD @ ~$1-2/day
- **Total**: ~$2-3/day for continuous operation

### Optimized Costs (Recommended Changes)
- **LLM**: Same (gpt-4o-mini with streaming)
- **TTS**: Same (Google Cloud)
- **STT**: Same (Google Cloud + VAD)
- **Total**: **~$2-3/day** (NO COST INCREASE)

### NOT Recommended (Cost Warnings)
- ❌ GPT-4o: +$0.16 per 100 queries (17x increase)
- ❌ OpenAI TTS HD: +$0.16 per 100 queries (2x increase)

---

## Implementation Roadmap

### Phase 1: Zero-Cost Quick Wins
1. ✅ Add performance instrumentation (DONE)
2. ✅ Run baseline tests (DONE)
3. ⏳ Reduce silence threshold (1.5s)
4. ⏳ Implement streaming LLM responses
5. ⏳ Parallelize TTS generation

**Expected Total Improvement**: **2-4 seconds**

### Phase 2: Testing & Validation
1. Re-run performance tests
2. Compare before/after metrics
3. Test in real conversation scenarios
4. Adjust silence threshold based on user feedback

### Phase 3: Optional Enhancements
1. Implement response caching
2. Pre-generate common phrases
3. Monitor and optimize further

---

## Success Metrics

### Target Goals
- **Baseline**: ~4.5-5s roundtrip (current)
- **Target**: ~2.5-3s roundtrip (40-50% improvement)
- **Cost**: Maintain current $2-3/day

### Breakdown of Expected Improvements
| Optimization | Improvement | Cumulative |
|-------------|-------------|------------|
| Baseline | - | 4.5s |
| Reduce silence threshold (-1s) | -1.0s | 3.5s |
| Streaming LLM (perceived -2s) | -2.0s | 1.5s perceived |
| Parallel TTS (-0.5s) | -0.5s | 1.0s perceived |

**Final Expected Latency**: **1-2s perceived** (after first sentence starts playing)

---

## Conclusion

The recommended approach achieves **significant performance improvements (2-4s reduction) with ZERO cost increase** by focusing on:

1. **Quick configuration tuning** (silence threshold)
2. **Streaming optimizations** (LLM streaming, parallel TTS)
3. **Maintaining current providers** (Google TTS, GPT-4o-mini)

The analysis shows that more expensive options (GPT-4o, OpenAI TTS HD) provide minimal benefit relative to their cost increase and should be avoided.

---

## Next Steps

1. ✅ Performance instrumentation (COMPLETED)
2. ✅ Baseline measurements (COMPLETED)
3. ⏳ Implement streaming LLM responses
4. ⏳ Implement parallel TTS generation
5. ⏳ Reduce silence threshold and test
6. ⏳ Re-measure and validate improvements
7. ⏳ Document final results

