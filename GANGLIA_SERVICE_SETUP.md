# GANGLIA Hardware Service Setup & Maintenance

This document describes how GANGLIA is configured to auto-start and auto-restart on the ganglia hardware.

## Overview

GANGLIA runs as a desktop application (not a systemd service) because it requires:
- Access to the user's audio session (PulseAudio)
- Visible terminal window for monitoring
- Display output (for electronics activation)

## Architecture

```
Boot → Login → Desktop Autostart → Terminator → start_ganglia_monitored.sh → ganglia.py
                                                      ↓ (on crash)
                                                   Auto-restart (5s delay)
```

## Components

### 1. Monitored Start Script

**Location**: `~/start_ganglia_monitored.sh` (also in repo as `start_ganglia_monitored.sh`)

**Purpose**: Wrapper that automatically restarts GANGLIA on any exit/crash

**Features**:
- Infinite restart loop
- Logs all starts/exits to `ganglia_monitor.log`
- 5-second delay between restarts
- Captures all stdout/stderr

**Installation**:
```bash
# Copy from repo
cd ~/dev/GANGLIA
cp start_ganglia_monitored.sh ~/
chmod +x ~/start_ganglia_monitored.sh
```

### 2. Desktop Autostart Entry

**Location**: `~/.config/autostart/ganglia.desktop`

**Purpose**: Launches GANGLIA automatically on boot/login

**Content**:
```ini
[Desktop Entry]
Type=Application
Name=GANGLIA Voice Assistant
Comment=Start GANGLIA in Terminator with auto-restart on crash
Exec=terminator -f -p LargeFont -e "bash -c '~/start_ganglia_monitored.sh; exec bash'"
Terminal=false
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
```

**Installation**:
```bash
mkdir -p ~/.config/autostart
nano ~/.config/autostart/ganglia.desktop
# Paste the above content
```

**Key Settings**:
- `-f`: Fullscreen mode
- `-p LargeFont`: Custom Terminator profile (must be configured separately)
- `exec bash`: Keeps terminal open if script exits (for debugging)

### 3. Environment Configuration

**Location**: `~/dev/GANGLIA/.envrc`

**Purpose**: Contains all required environment variables

**Critical Variables**:
```bash
export GOOGLE_APPLICATION_CREDENTIALS="/home/ganglia/ganglia-service-account.json"
export GCP_PROJECT_NAME="halloween2023"
export GCP_BUCKET_NAME="ganglia_session_logger"
export OPENAI_API_KEY="sk-..."
export FOXAI_SUNO_API_KEY="..."
export GRPC_VERBOSITY=ERROR
export GRPC_TRACE=
```

**Note**: `.envrc` is gitignored - must be configured manually on each machine

## Installation Procedure

### On a Fresh Ganglia Hardware Instance

1. **Clone Repository**:
   ```bash
   cd ~/dev
   git clone <GANGLIA_REPO_URL> GANGLIA
   cd GANGLIA
   git checkout feature/roundtrip_speed
   ```

2. **Setup Python Environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure Environment**:
   ```bash
   cp config/ganglia_config.json.template config/ganglia_config.json
   # Edit with your address, preferences, etc.
   
   cp .envrc.example .envrc  # If exists, otherwise create manually
   # Add all required API keys and credentials
   ```

4. **Setup Google Cloud Credentials**:
   ```bash
   # Download service account key from GCP console
   mv ~/Downloads/ganglia-service-account-*.json ~/ganglia-service-account.json
   
   # Verify in .envrc:
   export GOOGLE_APPLICATION_CREDENTIALS="/home/ganglia/ganglia-service-account.json"
   ```

5. **Install Monitored Start Script**:
   ```bash
   cp ~/dev/GANGLIA/start_ganglia_monitored.sh ~/
   chmod +x ~/start_ganglia_monitored.sh
   ```

6. **Configure Desktop Autostart**:
   ```bash
   mkdir -p ~/.config/autostart
   nano ~/.config/autostart/ganglia.desktop
   # Paste content from "Desktop Autostart Entry" section above
   ```

7. **Setup Terminator Profile** (if using LargeFont):
   ```bash
   # Open Terminator manually
   # Right-click → Preferences → Profiles
   # Create "LargeFont" profile with larger font size
   ```

8. **Test Manual Startup**:
   ```bash
   # Test the monitored script
   ~/start_ganglia_monitored.sh
   # Should launch GANGLIA, Ctrl+C to stop
   
   # Test in Terminator (as autostart will use)
   terminator -f -p LargeFont -e "bash -c '~/start_ganglia_monitored.sh; exec bash'"
   ```

9. **Reboot and Verify**:
   ```bash
   sudo reboot
   # After reboot, GANGLIA should auto-start in fullscreen Terminator
   ```

## Maintenance Commands

### Check if GANGLIA is Running

```bash
ps aux | grep ganglia.py
```

### View Live Logs

```bash
# Follow monitor log
tail -f ~/dev/GANGLIA/ganglia_monitor.log

# View recent session logs from GCS
cd ~/dev/GANGLIA
python ganglia.py --display-log-hours 1
```

### Manually Start GANGLIA

```bash
cd ~/dev/GANGLIA
source venv/bin/activate
source .envrc
python ganglia.py --store-logs --device-index 14 --audio-effects
```

### Stop GANGLIA

```bash
# Kill the process
pkill -f ganglia.py

# It will auto-restart in 5 seconds via monitor script
# To prevent restart, kill the monitor script too:
pkill -f start_ganglia_monitored
```

### Update Code

```bash
cd ~/dev/GANGLIA
git pull origin feature/roundtrip_speed

# GANGLIA will auto-restart with new code on next crash
# Or manually restart:
pkill -f ganglia.py  # Will auto-restart in 5s with new code
```

### Check for Crashes

```bash
# Check system logs for segfaults
sudo dmesg | grep -i "segfault\|killed"

# Check monitor log for restart patterns
grep "GANGLIA exited with code" ~/dev/GANGLIA/ganglia_monitor.log | tail -20

# Check restart count
grep "Starting GANGLIA" ~/dev/GANGLIA/ganglia_monitor.log | wc -l
```

### Troubleshooting Audio Issues

```bash
# List audio devices
python -c "import pyaudio; p = pyaudio.PyAudio(); [print(f'{i}: {p.get_device_info_by_index(i)[\"name\"]}') for i in range(p.get_device_count())]"

# Test speaker
ffplay /usr/share/sounds/alsa/Front_Center.wav

# Test microphone (requires a working device)
arecord -d 3 test.wav && aplay test.wav
```

## Known Issues & Solutions

### Issue: Segfault in libspeexdsp after 2+ hours

**Symptoms**: Python crashes with segfault in `libspeexdsp.so`

**Diagnosis**:
```bash
sudo dmesg | grep libspeexdsp
```

**Solution**:
```bash
sudo apt update
sudo apt install --reinstall libspeexdsp1 libspeexdsp-dev
sudo reboot
```

**Alternative**: Remove `--audio-effects` flag if issue persists

### Issue: 305-Second Google STT Timeout

**Symptoms**: `Error: 400 Exceeded maximum allowed stream duration`

**Solution**: Fixed in code (Oct 28, 2025 commit). Update to latest:
```bash
cd ~/dev/GANGLIA
git pull
pkill -f ganglia.py  # Auto-restarts with fix
```

### Issue: Missing Environment Variables

**Symptoms**: `Error: The following environment variables are missing: ...`

**Solution**:
```bash
# Check .envrc has all required variables
cat ~/dev/GANGLIA/.envrc

# Verify service account file exists
ls -l ~/ganglia-service-account.json

# Ensure .envrc is sourced in monitor script
grep "source .envrc" ~/start_ganglia_monitored.sh
```

## File Locations Reference

| Item | Location | Purpose |
|------|----------|---------|
| GANGLIA Code | `~/dev/GANGLIA/` | Main repository |
| Monitor Script | `~/start_ganglia_monitored.sh` | Auto-restart wrapper |
| Autostart Config | `~/.config/autostart/ganglia.desktop` | Boot configuration |
| Monitor Log | `~/dev/GANGLIA/ganglia_monitor.log` | Restart/crash log |
| Environment | `~/dev/GANGLIA/.envrc` | API keys, credentials |
| Service Account | `~/ganglia-service-account.json` | GCP credentials |
| App Config | `~/dev/GANGLIA/config/ganglia_config.json` | Personal settings |

## Monitoring Checklist

Daily/Weekly checks:
- [ ] GANGLIA is running: `ps aux | grep ganglia.py`
- [ ] No segfaults: `sudo dmesg | grep segfault`
- [ ] Restart count is low: `grep "Starting GANGLIA" ~/dev/GANGLIA/ganglia_monitor.log | tail -20`
- [ ] No 305s timeouts: `grep "305\|Exceeded maximum" ~/dev/GANGLIA/ganglia_monitor.log`

## Architecture Decisions

### Why Not Systemd Service?

We tried systemd initially but encountered:
1. **Audio session issues**: Systemd services don't have PulseAudio access
2. **No visual feedback**: Can't see terminal output for debugging
3. **Environment complexity**: Systemd requires special environment file format

Desktop autostart provides:
- ✅ User audio session access
- ✅ Visible terminal for monitoring
- ✅ Standard shell environment
- ✅ Easy debugging

### Why Monitor Script Instead of Systemd Restart?

Benefits of monitor script:
- Simpler than systemd service configuration
- More transparent logging
- Works with desktop autostart
- User can see what's happening in terminal
- Easier to debug and modify

## Support

For issues not covered here, check:
- `STATUS.md` - Current project status
- `VAD_CONFIG_README.md` - Voice activity detection tuning
- `GANGLIA_2025_SETUP.md` - Initial setup guide
- GitHub issues

