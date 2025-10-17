# GANGLIA 2025 Halloween Setup Guide

**Quick Reference**: Getting GANGLIA up and running for Halloween 2025

---

## 🎃 Quick Start Checklist

- [ ] Environment setup (.envrc configured)
- [ ] Google Cloud credentials configured
- [ ] OpenAI API key set
- [ ] Config file updated for 2025
- [ ] Audio devices tested
- [ ] Wake word system configured (NEW FOR 2025)
- [ ] Test run completed

---

## 📋 What Changed in 2025

### Major Updates
1. **Cost Optimization**: Implemented wake word detection to reduce Google Speech API costs from $20/day to nearly free
2. **Model Update**: Already using `gpt-4o-mini` (most affordable model as of 2025)
3. **Context Update**: Updated for 2025 Halloween party details
4. **Simplified Quest System**: Removed complex 2024 quest mechanics for cleaner operation

### Current Status
- **AI Model**: `gpt-4o-mini` (confirmed in query_dispatch.py:66)
- **Speech Recognition**: Google Cloud Speech-to-Text with streaming
- **TTS**: OpenAI TTS with audio effects (fallback to Google)

---

## 🚀 Installation & Setup

### 1. System Prerequisites

```bash
# Install Homebrew dependencies
brew install python pyenv zinit direnv openssl readline sqlite3 xz zlib portaudio ffmpeg opencv gh wget

# Install DejaVu fonts (required for video captions)
brew install font-dejavu
```

### 2. Python Environment

```bash
# Create virtual environment (Python 3.9+)
python3.9 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements_core.txt
pip install -r requirements_large.txt  # If using ML features
```

### 3. Environment Variables (.envrc)

```bash
# Copy template
cp .envrc.template .envrc

# Edit .envrc with your credentials
# Required variables:
export OPENAI_API_KEY="sk-..."
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/google-creds.json"
export GCP_BUCKET_NAME="your-bucket"
export GCP_PROJECT_NAME="your-project"
export FOXAI_SUNO_API_KEY="your-suno-key"

# Optional:
export GANGLIA_TEMP_DIR="/tmp/GANGLIA"

# Activate direnv
direnv allow
```

### 4. Google Cloud Setup

```bash
# Install Google Cloud SDK
brew install google-cloud-sdk

# Authenticate
gcloud auth application-default login

# Set up credentials file
# Download JSON key from Google Cloud Console
# Place at path specified in GOOGLE_APPLICATION_CREDENTIALS
```

### 5. Configuration Files

```bash
# Create your config from template
cp config/ganglia_config.json.template config/ganglia_config.json

# Edit config/ganglia_config.json:
# - Update conversation_context for 2025
# - Configure hotwords
# - Set TTS preferences
```

---

## 💰 Cost Optimization Strategy (NEW FOR 2025)

### The Problem
Last year: **$20/day** in Google Speech API costs just from idle listening
- Google charges per 15-second increment of audio processed
- Continuous streaming = 24/7 charging even with no speech

### The Solution: Voice Activity Detection (VAD)

**✅ IMPLEMENTED: Simple Energy-Based VAD**
```bash
# Already included in GANGLIA - no additional dependencies!
# Uses built-in pyaudio for local speech detection
```

**How it works:**
1. Monitor audio energy locally (FREE - no API calls)
2. When sustained speech detected, activate Google Cloud streaming
3. Process full conversation with Google Speech-to-Text (PAID)
4. After 30 seconds of silence, return to idle listening mode

**Benefits:**
- ✅ No wake word needed - ANY speech activates
- ✅ Natural interaction - just start talking
- ✅ Zero cost while idle
- ✅ No additional dependencies
- ✅ Simple and reliable
- ✅ Estimated cost reduction: **$20/day → $1-2/day**

### Usage
```bash
# Run with Voice Activity Detection (RECOMMENDED FOR PARTY)
python ganglia.py --dictation-type vad

# Traditional modes still available:
python ganglia.py --dictation-type live_google  # Old expensive mode
python ganglia.py --dictation-type static_google  # Manual activation
```

### Tuning Sensitivity

If VAD doesn't trigger easily or triggers too often:

**Quick Test:**
```bash
# Test your environment and get recommendations
python utils/test_vad_sensitivity.py --duration 30
```

**Adjust Settings:**
Edit `config/vad_config.json`:
- **Too sensitive** (triggers on noise): INCREASE `energy_threshold` (try 600-800)
- **Not sensitive** (need to speak loudly): DECREASE `energy_threshold` (try 200-300)
- **Slow activation**: DECREASE `speech_confirmation_chunks` (try 2 or 1)

**Default settings** (already tuned based on testing):
- `energy_threshold: 300` (more sensitive than default 500)
- `speech_confirmation_chunks: 2` (faster than default 3)

See `VAD_TUNING_GUIDE.md` for complete tuning instructions.

---

## 🎙️ Audio Device Testing

```bash
# List available audio devices
python -c "import pyaudio; p = pyaudio.PyAudio(); \
    [print(f'{i}: {p.get_device_info_by_index(i)[\"name\"]}') \
    for i in range(p.get_device_count())]"

# Test your microphone
python -c "import pyaudio, wave; \
    p = pyaudio.PyAudio(); \
    stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=1024); \
    print('Recording for 5 seconds...'); \
    frames = [stream.read(1024) for _ in range(80)]; \
    stream.close(); p.terminate(); \
    wf = wave.open('test.wav', 'wb'); \
    wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(16000); \
    wf.writeframes(b''.join(frames)); wf.close(); \
    print('Saved to test.wav')"
```

---

## 🎃 2025 Context Update

### What to Update in config/ganglia_config.json

```json
{
  "conversation": {
    "conversation_context": [
      "You are named GANGLIA, the Fallen King of Halloween.",
      "You are an assistant engaging in a conversation with the user. Keep your responses concise and natural.",
      "You live inside the guest room at 27th Avenue in Eugene, Oregon.",
      "You live inside a coffin with a 3 DOF animatronic skull head that lip-syncs your words.",
      "Tonight is October 31st, 2025, and you are hosting your third annual Halloween party.",

      // ADD 2025-SPECIFIC DETAILS:
      "This year's theme involves the Chronic Flock of the Haunted Flamingos - [ADD LORE HERE]",
      "You've had another year to perfect your appearance and animatronics.",
      "Slayborham Lincoln is still here, the six-eyed Lincoln bust with no AI - you still mock him.",

      // UPDATE GUEST LIST FOR 2025
      "Tonight's attendees include: [UPDATE WITH 2025 GUESTS]",

      // REMOVE OR SIMPLIFY QUEST-RELATED CONTENT
      // Keep hotwords simple for general interactions
    ]
  }
}
```

---

## 🏃 Running GANGLIA

### Basic Conversation Mode
```bash
# Activate virtual environment
source venv/bin/activate

# Run GANGLIA
python ganglia.py

# With specific options
python ganglia.py \
  --tts-interface google \
  --dictation-type live \
  --device-index 0 \
  --enable-turn-indicators
```

### Text-to-Video Mode
```bash
# Create a video from a story
python ganglia.py --ttv-config config/ttv_config.json
```

### Testing Individual Components
```bash
# Test TTS
python -c "from tts import GoogleTextToSpeech; \
    tts = GoogleTextToSpeech(); \
    tts.convert_text_to_speech('Testing GANGLIA TTS')"

# Test dictation
python -m pytest tests/unit/test_audio_inputs.py -v -s
```

---

## 🐛 Troubleshooting

### "Google Speech Recognition could not understand audio"
- Check microphone levels
- Verify `GOOGLE_APPLICATION_CREDENTIALS` path
- Test with `--dictation-type static` for debugging

### "Failed to initialize Text-to-Speech interface"
- Verify OpenAI API key is set
- Check Google Cloud credentials
- Try fallback: `--tts-interface google`

### Audio device errors
- List devices: `python -c "import pyaudio; ..."`
- Try different device index: `--device-index N`
- Check system audio permissions

### High API costs
- Implement wake word detection (see Cost Optimization section)
- Monitor usage in Google Cloud Console
- Consider switching to `--dictation-type static` for manual activation

---

## 📊 Monitoring & Logs

### Log Files
```bash
# View recent logs
python ganglia.py --display-log-hours 24

# Log location
ls -lah logs/

# Monitor in real-time
tail -f logs/ganglia_session_*.log
```

### Cost Monitoring
```bash
# Google Cloud Console
# Navigation: APIs & Services → Dashboard → Speech-to-Text API
# Check: Requests, Usage, and Quotas

# Set up billing alerts!
# Billing → Budgets & alerts → Create budget
# Recommended: Alert at $5, $10, $20 monthly
```

---

## 🎬 Video Generation (Optional)

### Create Halloween Videos
```bash
# Configure story
cp config/ttv_config.template.json config/ttv_config.json
# Edit ttv_config.json with your story

# Generate video
python ganglia.py --ttv-config config/ttv_config.json

# Skip image regeneration (faster testing)
python ganglia.py --ttv-config config/ttv_config.json --skip-image-generation
```

---

## 📝 Pre-Party Testing Checklist

### One Week Before
- [ ] Update context in config file
- [ ] Test microphone and speaker
- [ ] Run full conversation test
- [ ] Verify animatronic sync
- [ ] Check API quotas and billing
- [ ] Implement wake word detection
- [ ] Test wake word activation

### Day Before
- [ ] Full system test run
- [ ] Backup config files
- [ ] Clear old logs
- [ ] Verify internet connection
- [ ] Test fallback systems
- [ ] Charge any battery backups

### Party Night
- [ ] Start GANGLIA 30 minutes before guests
- [ ] Verify audio levels
- [ ] Test with a friend
- [ ] Have backup plan ready
- [ ] Monitor logs for errors

---

## 🆘 Emergency Procedures

### If GANGLIA Crashes
```bash
# Quick restart
source venv/bin/activate
python ganglia.py

# If that fails, check logs
tail -50 logs/ganglia_session_*.log

# Nuclear option: restart everything
killall python
sleep 2
python ganglia.py
```

### If Audio Fails
1. Switch TTS: `--tts-interface google`
2. Check speaker connection
3. Verify audio output device
4. Restart audio system

### If Speech Recognition Fails
1. Try static mode: `--dictation-type static`
2. Check Google Cloud credentials
3. Verify microphone input
4. Check internet connection

---

## 📚 Additional Resources

- [README.md](README.md) - Full documentation
- [README_ARCHITECTURE.md](README_ARCHITECTURE.md) - System architecture
- [tests/README.md](tests/README.md) - Testing guide
- Google Cloud Speech-to-Text: https://cloud.google.com/speech-to-text
- OpenAI TTS API: https://platform.openai.com/docs/guides/text-to-speech

---

## 💡 Tips for Success

1. **Test Early**: Don't wait until party day
2. **Monitor Costs**: Set up billing alerts
3. **Have Backups**: Pre-record responses as fallback
4. **Keep It Simple**: Remove complex features if unstable
5. **Log Everything**: Helps with post-party debugging
6. **Wake Word First**: Implement before going live to save $$

---

## 🎃 Have a Spooky Halloween! 🎃

For questions or issues:
- Check logs first
- Review error messages
- Test components individually
- Will Martin: unique.will.martin@gmail.com
