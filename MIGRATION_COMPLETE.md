# GANGLIA Repository Migration - COMPLETE ✅

**Date:** November 4, 2025
**Strategy:** Parallel development (original GANGLIA untouched)

## New Repository Structure

### 📦 ganglia-common (Shared Utilities)
- **GitHub:** https://github.com/ScienceIsNeato/ganglia-common
- **Local:** `/Users/pacey/Documents/SourceCode/ganglia-common`
- **Contents:** 11 source files
  - Logger, query_dispatch, TTS (OpenAI + Google)
  - PubSub system
  - Cloud, file, performance, retry utilities

### 🎬 ganglia-studio (Multimedia Generation)
- **GitHub:** https://github.com/ScienceIsNeato/ganglia-studio
- **Local:** `/Users/pacey/Documents/SourceCode/ganglia-studio`
- **Contents:** 32 source files
  - Video generation (TTV pipeline)
  - Music backends (Suno, Meta MusicGen)
  - Story generation
  - Image generation
  - CLI: `ganglia-studio video --config config.json`

### 🤖 ganglia-core (Chatbot Interface)
- **GitHub:** https://github.com/ScienceIsNeato/ganglia-core
- **Local:** `/Users/pacey/Documents/SourceCode/ganglia-core`
- **Contents:** 13 source files
  - Conversational interface, hotwords, audio indicators
  - Context management (conversation, file)
  - Dictation/speech-to-text
  - Studio client (optional integration)
- **Submodules:** ganglia-common, ganglia-studio

## Installation

### Core Only (Chatbot)
```bash
git clone --recursive git@github.com:ScienceIsNeato/ganglia-core.git
cd ganglia-core
pip install -e ./ganglia-common
pip install -e .
python ganglia.py
```

### Full Stack (Chatbot + Multimedia)
```bash
git clone --recursive git@github.com:ScienceIsNeato/ganglia-core.git
cd ganglia-core
pip install -e ./ganglia-common
pip install -e ./ganglia-studio
pip install -e .[studio]
python ganglia.py
```

## Original GANGLIA Status

**Status:** ✅ UNTOUCHED and FULLY FUNCTIONAL
**Location:** `/Users/pacey/Documents/SourceCode/GANGLIA`

- All source files intact
- Git history preserved
- Can continue using for existing work
- Ready for gradual transition when new repos are production-ready

## Next Steps

1. **Develop in parallel:** Use new repos for new features, GANGLIA for stability
2. **Test independently:** Each repo has its own test suite
3. **Gradual transition:** Move workflows to new repos as they mature
4. **No rush:** Original GANGLIA remains fully supported

## Architecture Benefits

- **Separation of concerns:** Chatbot vs multimedia generation
- **Modular dependencies:** Install only what you need
- **Lighter testing:** Chatbot tests don't require heavy multimedia tests
- **Independent evolution:** Each component can evolve at its own pace
- **Scalability:** Easy to add new repos (ganglia-web, ganglia-analytics, etc.)

---

**Migration Strategy Credit:** Parallel development approach preserved original system while building new architecture from scratch. No git history migration = clean slate, no risk.
