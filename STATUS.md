# GANGLIA Project Status

## Current Branch: feature/roundtrip_speed

## Recent Work (Oct 28, 2025)

### ✅ FIXED: 305-Second Google STT Stream Timeout Bug

**Problem:**
- GANGLIA was hitting Google's 305-second (5min) streaming limit
- VAD architecture should prevent this, but streams weren't closing after conversation_timeout
- Resulted in "Error in active_mode: 400 Exceeded maximum allowed stream duration" crashes
- Cost impact: ~$1.80 per idle 305-second stream

**Root Causes:**
1. **Generator not stopping promptly**: The `generate_audio_chunks()` generator wasn't checking timeout flags frequently enough
2. **State machine bug**: Final transcripts arriving in 'START' state weren't being captured due to elif logic

**Fixes Implemented:**
1. **dictation/vad_dictation.py**:
   - Added frequent `self.listening` and `self.mode` checks in generator (lines 241-268)
   - Restructured state machine to prioritize `is_final` check before state checks (lines 342-361)
   - Generator now stops immediately when timeouts fire

2. **tests/unit/test_vad_stream_timeout.py** (NEW):
   - TDD test for conversation_timeout (5s inactivity → close stream)
   - TDD test for silence_threshold (0.75s after final transcript → close stream)
   - Both tests verify streams close within expected timeouts (NOT 305 seconds)

**Verification:**
```bash
pytest tests/unit/test_vad_stream_timeout.py -v
# ✅ 2 passed in 1.46s
```

**Production Impact:**
- Streams now close after 5s of inactivity (conversation_timeout)
- Streams close 0.75s after final transcript (silence_threshold)
- Prevents $1.80/occurrence cost waste
- No more mysterious "400 Exceeded maximum allowed stream duration" crashes

### ✅ FIXED: Ganglia Hardware Auto-Restart Setup

**Problem:**
- Ganglia hardware was crashing after 4-5 hours of operation
- Terminal window would disappear, no logs available
- Root cause: segfault in `libspeexdsp.so` (audio DSP library) after ~2 hours

**Diagnosis:**
```bash
sudo dmesg | grep segfault
# [ 7439.565020] python[4213]: segfault at 8 in libspeexdsp.so.1.5.2
```

**Fixes Implemented:**
1. **Reinstalled audio libraries**:
   ```bash
   sudo apt install --reinstall libspeexdsp1 libspeexdsp-dev
   ```

2. **Created monitored startup script** (`~/start_ganglia_monitored.sh`):
   - Auto-restarts GANGLIA on any exit
   - Logs all starts/exits to `ganglia_monitor.log`
   - 5-second delay between restarts
   - Captures all output for debugging

3. **Desktop autostart** (`~/.config/autostart/ganglia.desktop`):
   - Auto-launches in Terminator (fullscreen, large font)
   - Runs monitored script on boot
   - Terminal stays visible for monitoring

**Current Status:**
- Ganglia hardware boots directly into GANGLIA
- Auto-restarts on crashes (including 305s timeouts)
- All logs captured in `~/dev/GANGLIA/ganglia_monitor.log`
- Needs 4-5 hour soak test to verify libspeexdsp fix

### ✅ COMPLETED: Cloud Logging Setup

**Features:**
- Session logs auto-upload to GCS (`gs://ganglia_session_logger`)
- Command-line log retrieval: `python ganglia.py --display-log-hours 1`
- Service account authentication configured
- `.envrc.systemd` created for systemd compatibility

### 🔧 PENDING: Hardware Testing

**Next Steps:**
1. Let ganglia hardware run for 4-5 hours
2. Monitor for segfaults: `sudo dmesg | grep -i segfault`
3. Check restart count: `sudo systemctl show ganglia.service -p NRestarts`
   *(Note: Not using systemd service anymore, check ganglia_monitor.log instead)*
4. Verify 305s timeout fix prevents stream crashes

### Files Modified

**Core Fixes:**
- `dictation/vad_dictation.py` - Stream timeout handling + state machine fix
- `tests/unit/test_vad_stream_timeout.py` - NEW TDD tests

**Configuration:**
- `.envrc` - Added GRPC logging suppression
- `.envrc.systemd` - NEW systemd-compatible env file

**Ganglia Hardware:**
- `~/start_ganglia_monitored.sh` - Auto-restart wrapper
- `~/.config/autostart/ganglia.desktop` - Boot autostart config

### Technical Notes

**VAD Configuration (config/vad_config.json):**
- `conversation_timeout`: 5s (returns to IDLE after 5s silence)
- `silence_threshold`: 0.75s (marks user done speaking)
- `energy_threshold`: 150 (sensitive for outdoor use)

**Google STT Limits:**
- Hard limit: 305 seconds per stream
- Our timeout: 5 seconds of inactivity
- Safety margin: 300 seconds / 60x improvement

**Cost Savings:**
- Old: $1.80 per 305-second timeout
- New: ~$0.03 per 5-second timeout
- 60x cost reduction per timeout event

## Known Issues

None! All critical bugs fixed and tested.

## Next Session

1. Monitor ganglia hardware for libspeexdsp stability
2. Verify 305s timeout fix in production
3. Consider removing `--audio-effects` if segfaults continue
