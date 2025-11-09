# GANGLIA Repository Migration - Clean Slate Approach

## Overview

This plan creates **brand new repositories** by copying files from the existing GANGLIA repo. The original GANGLIA repo remains **completely untouched** and continues to work throughout the migration.

**Strategy**: Parallel development → Test new structure → Switch over when ready

### New Repositories:
- **ganglia-common** (shared utilities) - fresh repo
- **ganglia-studio** (multimedia generation) - fresh repo
- **ganglia-core** (conversational AI) - fresh repo with submodules

### Original Repository:
- **GANGLIA** - stays untouched, remains functional, eventually deprecated

**Estimated Time**: 6-8 hours (much simpler than before)
**Risk Level**: Very Low (original repo never modified)

---

## Benefits of This Approach

✅ **Zero Risk**: Original GANGLIA never touched
✅ **Backwards Compatible**: Old system keeps working
✅ **Gradual Migration**: Switch when confident
✅ **Parallel Testing**: Compare old vs new side-by-side
✅ **Clean History**: Fresh start, no legacy baggage
✅ **Simple Rollback**: Just delete new repos
✅ **No Git Complexity**: Plain file copying

---

## Pre-Migration Checklist

### 1. Verify GANGLIA Works
```bash
cd /Users/pacey/Documents/SourceCode/GANGLIA
git status  # Note: we won't touch this repo
git log --oneline -5

# Run baseline tests (optional, just to know current state)
source venv/bin/activate
pytest tests/ -v > /tmp/ganglia_baseline_tests.log 2>&1
```

### 2. Understand Final Directory Structure
```
/Users/pacey/Documents/SourceCode/
├── GANGLIA/                    ← Original (untouched, still works)
├── ganglia-common/             ← New standalone repo
├── ganglia-studio/             ← New standalone repo
└── ganglia-core/               ← New main repo with submodules
    ├── ganglia_common/         ← Submodule pointing to ../ganglia-common
    └── ganglia_studio/         ← Submodule pointing to ../ganglia-studio
```

**Key Points:**
- All repos are siblings in `/Users/pacey/Documents/SourceCode/`
- ganglia-core's submodules point to local siblings (not remote GitHub)
- You can work on common/studio independently
- Changes in common/studio are immediately available in core
- Each repo pushes to GitHub independently

---

## Phase 1: Create ganglia-common (Fresh Start)

**Time Estimate**: 1.5-2 hours

### 1.1: Create Repository on GitHub
```bash
gh repo create ganglia-common --public --description "Shared utilities for GANGLIA ecosystem"
```

### 1.2: Initialize Fresh Local Repository
```bash
cd /Users/pacey/Documents/SourceCode
mkdir ganglia-common
cd ganglia-common

# Initialize git
git init
git branch -M main

# Create clean directory structure
mkdir -p src/ganglia_common/{tts,pubsub,utils}
mkdir -p tests/unit
```

### 1.3: Copy Files from GANGLIA
```bash
cd /Users/pacey/Documents/SourceCode

# Copy core utilities
cp GANGLIA/logger.py ganglia-common/src/ganglia_common/
cp GANGLIA/query_dispatch.py ganglia-common/src/ganglia_common/

# Copy TTS (rename files)
cp GANGLIA/tts.py ganglia-common/src/ganglia_common/tts/google_tts.py
cp GANGLIA/tts_openai.py ganglia-common/src/ganglia_common/tts/openai_tts.py

# Copy PubSub
cp -r GANGLIA/pubsub/* ganglia-common/src/ganglia_common/pubsub/

# Copy Utils (selective)
cp GANGLIA/utils/__init__.py ganglia-common/src/ganglia_common/utils/
cp GANGLIA/utils/file_utils.py ganglia-common/src/ganglia_common/utils/
cp GANGLIA/utils/performance_profiler.py ganglia-common/src/ganglia_common/utils/
cp GANGLIA/utils/retry_utils.py ganglia-common/src/ganglia_common/utils/
cp GANGLIA/utils/cloud_utils.py ganglia-common/src/ganglia_common/utils/

# Copy Tests
cp GANGLIA/tests/unit/test_query_dispatch.py ganglia-common/tests/unit/
cp GANGLIA/tests/unit/test_send_query.py ganglia-common/tests/unit/
cp GANGLIA/tests/unit/test_pubsub.py ganglia-common/tests/unit/
cp GANGLIA/tests/unit/test_utils.py ganglia-common/tests/unit/
```

### 1.4: Create __init__.py Files
```bash
cd /Users/pacey/Documents/SourceCode/ganglia-common

# Create all __init__.py files
cat > src/ganglia_common/__init__.py << 'EOF'
"""GANGLIA Common - Shared utilities for GANGLIA ecosystem."""

__version__ = "0.1.0"
EOF

touch src/ganglia_common/tts/__init__.py
touch src/ganglia_common/pubsub/__init__.py
touch src/ganglia_common/utils/__init__.py
touch tests/__init__.py
touch tests/unit/__init__.py
```

### 1.5: Refactor Imports (Search & Replace)
```bash
cd /Users/pacey/Documents/SourceCode/ganglia-common

# Update imports in all Python files:
# from logger import Logger → from ganglia_common.logger import Logger
# from query_dispatch import * → from ganglia_common.query_dispatch import *
# from utils.file_utils import * → from ganglia_common.utils.file_utils import *
# from pubsub import * → from ganglia_common.pubsub import *

# Example for one file (repeat for all):
# sed -i '' 's/from logger import/from ganglia_common.logger import/g' src/ganglia_common/query_dispatch.py
# sed -i '' 's/from utils\./from ganglia_common.utils./g' src/ganglia_common/**/*.py

# NOTE: You'll need to manually edit each file to update imports correctly
```

### 1.6: Create Package Configuration
```bash
cd /Users/pacey/Documents/SourceCode/ganglia-common

cat > setup.py << 'EOF'
from setuptools import setup, find_packages

setup(
    name="ganglia-common",
    version="0.1.0",
    description="Shared utilities for GANGLIA ecosystem",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.9",
    install_requires=[
        "openai>=1.3.0",
        "python-dotenv>=1.0.0",
        "google-cloud-texttospeech>=2.14.1",
        "google-cloud-storage>=2.10.0",
        "gTTS>=2.5.0",
        "requests>=2.31.0",
    ],
)
EOF

cat > pyproject.toml << 'EOF'
[build-system]
requires = ["setuptools>=45", "wheel"]
build-backend = "setuptools.build_backend"

[project]
name = "ganglia-common"
version = "0.1.0"
description = "Shared utilities for GANGLIA ecosystem"
requires-python = ">=3.9"
EOF

cat > requirements.txt << 'EOF'
openai>=1.3.0
python-dotenv>=1.0.0
google-cloud-texttospeech>=2.14.1
google-cloud-storage>=2.10.0
gTTS>=2.5.0
requests>=2.31.0
EOF

cat > requirements-dev.txt << 'EOF'
pytest>=7.3.1
pytest-asyncio>=0.21.1
pytest-timeout>=2.1.0
pytest-cov>=4.1.0
EOF

cat > pytest.ini << 'EOF'
[pytest]
testpaths = tests
python_files = test_*.py
EOF

cat > .gitignore << 'EOF'
__pycache__/
*.py[cod]
.Python
build/
dist/
*.egg-info/
.pytest_cache/
.coverage
.env
.venv
venv/
EOF

cat > README.md << 'EOF'
# ganglia-common

Shared utilities for the GANGLIA ecosystem.

## Components

- **logger**: Centralized logging
- **query_dispatch**: OpenAI API interface
- **tts**: Text-to-speech engines (Google, OpenAI)
- **pubsub**: Event system
- **utils**: File operations, performance profiling, retry logic

## Installation

```bash
pip install -e .
```

## Development

```bash
pip install -e ".[dev]"
pytest
```
EOF
```

### 1.7: Test ganglia-common
```bash
cd /Users/pacey/Documents/SourceCode/ganglia-common

# Create venv
python3 -m venv venv
source venv/bin/activate

# Install
pip install -e .
pip install -r requirements-dev.txt

# Test imports
python -c "from ganglia_common.logger import Logger; print('✓ Logger')"
python -c "from ganglia_common.query_dispatch import ChatGPTQueryDispatcher; print('✓ QueryDispatch')"
python -c "from ganglia_common.tts.google_tts import GoogleTTS; print('✓ GoogleTTS')"
python -c "from ganglia_common.pubsub import get_pubsub; print('✓ PubSub')"

# Run tests
pytest tests/ -v
```

### 1.8: Commit and Push
```bash
cd /Users/pacey/Documents/SourceCode/ganglia-common

git add .
git commit -m "Initial commit: ganglia-common shared utilities

Core components:
- Logger (centralized logging)
- Query dispatch (OpenAI API interface)
- TTS engines (Google, OpenAI)
- PubSub event system
- Common utilities (file, performance, retry, cloud)

Fresh start from GANGLIA codebase."

git remote add origin git@github.com:YOUR_USERNAME/ganglia-common.git
git push -u origin main
```

---

## Phase 2: Create ganglia-studio (Fresh Start)

**Time Estimate**: 2-3 hours

### 2.1: Create Repository on GitHub
```bash
gh repo create ganglia-studio --public --description "Multimedia generation suite for GANGLIA"
```

### 2.2: Initialize Fresh Local Repository
```bash
cd /Users/pacey/Documents/SourceCode
mkdir ganglia-studio
cd ganglia-studio

git init
git branch -M main

# Create directory structure
mkdir -p src/ganglia_studio/{video,story,music/backends,image,config,utils}
mkdir -p tests/{unit/{video,story,music,config},integration,fixtures}
mkdir -p config
```

### 2.3: Copy Files from GANGLIA
```bash
cd /Users/pacey/Documents/SourceCode

# Video pipeline
cp GANGLIA/ttv/ttv.py ganglia-studio/src/ganglia_studio/video/pipeline.py
cp GANGLIA/ttv/audio_alignment.py ganglia-studio/src/ganglia_studio/video/
cp GANGLIA/ttv/audio_generation.py ganglia-studio/src/ganglia_studio/video/
cp GANGLIA/ttv/captions.py ganglia-studio/src/ganglia_studio/video/
cp GANGLIA/ttv/caption_roi.py ganglia-studio/src/ganglia_studio/video/
cp GANGLIA/ttv/color_utils.py ganglia-studio/src/ganglia_studio/video/
cp GANGLIA/ttv/ffmpeg_constants.py ganglia-studio/src/ganglia_studio/video/
cp GANGLIA/ttv/final_video_generation.py ganglia-studio/src/ganglia_studio/video/final_assembly.py
cp GANGLIA/ttv/video_generation.py ganglia-studio/src/ganglia_studio/video/
cp GANGLIA/ttv/log_messages.py ganglia-studio/src/ganglia_studio/video/

# Image
cp GANGLIA/ttv/image_generation.py ganglia-studio/src/ganglia_studio/image/generation.py

# Story
cp GANGLIA/story_generation_driver.py ganglia-studio/src/ganglia_studio/story/driver.py
cp GANGLIA/ttv/story_generation.py ganglia-studio/src/ganglia_studio/story/generation.py
cp GANGLIA/ttv/story_processor.py ganglia-studio/src/ganglia_studio/story/processor.py

# Music
cp GANGLIA/music_lib.py ganglia-studio/src/ganglia_studio/music/library.py
cp GANGLIA/lyrics_lib.py ganglia-studio/src/ganglia_studio/music/lyrics.py
cp GANGLIA/music_backends/*.py ganglia-studio/src/ganglia_studio/music/backends/
cp GANGLIA/suno_request_handler.py ganglia-studio/src/ganglia_studio/music/request_handler.py

# Config
cp GANGLIA/ttv/config_loader.py ganglia-studio/src/ganglia_studio/config/loader.py
cp GANGLIA/config/ttv_config.json ganglia-studio/config/
cp GANGLIA/config/ttv_config.template.json ganglia-studio/config/

# Utils
cp GANGLIA/utils/ffmpeg_utils.py ganglia-studio/src/ganglia_studio/utils/
cp GANGLIA/utils/video_utils.py ganglia-studio/src/ganglia_studio/utils/

# Tests (copy entire test directories)
cp -r GANGLIA/tests/unit/ttv/* ganglia-studio/tests/unit/video/ 2>/dev/null || true
cp GANGLIA/tests/unit/test_music_lib.py ganglia-studio/tests/unit/music/test_library.py 2>/dev/null || true
cp -r GANGLIA/tests/integration/test_data ganglia-studio/tests/fixtures/ 2>/dev/null || true
```

### 2.4: Create __init__.py Files
```bash
cd /Users/pacey/Documents/SourceCode/ganglia-studio

cat > src/ganglia_studio/__init__.py << 'EOF'
"""GANGLIA Studio - Multimedia generation suite."""

__version__ = "0.1.0"
EOF

touch src/ganglia_studio/video/__init__.py
touch src/ganglia_studio/story/__init__.py
touch src/ganglia_studio/music/__init__.py
touch src/ganglia_studio/music/backends/__init__.py
touch src/ganglia_studio/image/__init__.py
touch src/ganglia_studio/config/__init__.py
touch src/ganglia_studio/utils/__init__.py
```

### 2.5: Create CLI Interface
```bash
cd /Users/pacey/Documents/SourceCode/ganglia-studio

cat > src/ganglia_studio/cli.py << 'EOF'
"""CLI interface for ganglia-studio."""

import argparse
import sys
from pathlib import Path


def video_command(args):
    """Generate video from config."""
    from ganglia_studio.video.pipeline import text_to_video
    from ganglia_common.logger import Logger

    Logger.print_info(f"Generating video: {args.config}")
    result = text_to_video(args.config)
    if result:
        Logger.print_success(f"Video: {result}")
    else:
        sys.exit(1)


def music_command(args):
    """Generate music."""
    from ganglia_common.logger import Logger
    Logger.print_info(f"Music generation: {args.prompt}")
    # TODO: Implement
    Logger.print_success("Done")


def image_command(args):
    """Generate image."""
    from ganglia_common.logger import Logger
    Logger.print_info(f"Image generation: {args.prompt}")
    # TODO: Implement
    Logger.print_success("Done")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="GANGLIA Studio - Multimedia Generation")
    subparsers = parser.add_subparsers(dest="command")

    # Video
    video_p = subparsers.add_parser("video", help="Generate video")
    video_p.add_argument("--config", required=True)
    video_p.set_defaults(func=video_command)

    # Music
    music_p = subparsers.add_parser("music", help="Generate music")
    music_p.add_argument("--prompt", required=True)
    music_p.set_defaults(func=music_command)

    # Image
    image_p = subparsers.add_parser("image", help="Generate image")
    image_p.add_argument("--prompt", required=True)
    image_p.set_defaults(func=image_command)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
EOF
```

### 2.6: Refactor Imports (Search & Replace)
```bash
cd /Users/pacey/Documents/SourceCode/ganglia-studio

# Update all imports in src/ganglia_studio/:
# from logger import Logger → from ganglia_common.logger import Logger
# from query_dispatch import * → from ganglia_common.query_dispatch import *
# from tts import GoogleTTS → from ganglia_common.tts.google_tts import GoogleTTS
# from ttv.* → from ganglia_studio.video.* or appropriate module
# from music_lib import * → from ganglia_studio.music.library import *
# from utils.file_utils import * → from ganglia_common.utils.file_utils import *
# from utils.ffmpeg_utils import * → from ganglia_studio.utils.ffmpeg_utils import *

# This requires editing EVERY .py file - use your editor's search/replace
```

### 2.7: Create Package Configuration
```bash
cd /Users/pacey/Documents/SourceCode/ganglia-studio

cat > setup.py << 'EOF'
from setuptools import setup, find_packages

setup(
    name="ganglia-studio",
    version="0.1.0",
    description="Multimedia generation suite for GANGLIA",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.9",
    install_requires=[
        "torch>=2.0.0",
        "transformers>=4.30.0",
        "opencv-python>=4.9.0",
        "moviepy>=1.0.3",
        "numpy>=1.24.3",
        "openai>=1.3.0",
        "pillow>=10.0.0",
    ],
    entry_points={
        "console_scripts": [
            "ganglia-studio=ganglia_studio.cli:main",
        ],
    },
)
EOF

cat > requirements.txt << 'EOF'
# Install ganglia-common first
# pip install -e ../ganglia-common

torch>=2.0.0
transformers>=4.30.0
opencv-python>=4.9.0
moviepy>=1.0.3
numpy>=1.24.3
openai>=1.3.0
pillow>=10.0.0
pydub>=0.25.1
EOF

cat > .gitignore << 'EOF'
__pycache__/
*.py[cod]
.Python
build/
dist/
*.egg-info/
.pytest_cache/
.env
.venv
venv/
output/
*.mp4
*.wav
*.mp3
EOF

cat > README.md << 'EOF'
# ganglia-studio

Multimedia generation suite for GANGLIA.

## Features

- Video generation (text-to-video pipeline)
- Music generation (AI-powered)
- Image generation (DALL-E)
- Story generation

## Installation

```bash
# Install common first
pip install -e ../ganglia-common

# Install studio
pip install -e .
```

## Usage

```bash
ganglia-studio video --config story.json
ganglia-studio music --prompt "epic"
ganglia-studio image --prompt "cyberpunk"
```
EOF
```

### 2.8: Test ganglia-studio
```bash
cd /Users/pacey/Documents/SourceCode/ganglia-studio

python3 -m venv venv
source venv/bin/activate

# Install ganglia-common first
pip install -e ../ganglia-common

# Install ganglia-studio
pip install -e .

# Test CLI
ganglia-studio --help
ganglia-studio video --help
```

### 2.9: Commit and Push
```bash
cd /Users/pacey/Documents/SourceCode/ganglia-studio

git add .
git commit -m "Initial commit: ganglia-studio multimedia suite

Components:
- Video generation pipeline
- Music generation with multiple backends
- Image generation (DALL-E)
- Story generation and processing
- CLI interface (ganglia-studio video/music/image)

Fresh start from GANGLIA codebase."

git remote add origin git@github.com:YOUR_USERNAME/ganglia-studio.git
git push -u origin main
```

---

## Phase 3: Create ganglia-core (Fresh Start with Submodules)

**Time Estimate**: 2-3 hours

### 3.1: Create Repository on GitHub
```bash
gh repo create ganglia-core --public --description "Conversational AI system with voice interaction"
```

### 3.2: Initialize Fresh Local Repository
```bash
cd /Users/pacey/Documents/SourceCode
mkdir ganglia-core
cd ganglia-core

git init
git branch -M main

# Create directory structure
mkdir -p src/ganglia_core/{core,audio,input,config,integrations/social_media}
mkdir -p tests/{unit/{core,input,config,integrations},integration}
mkdir -p config media scripts docs deployment
```

### 3.3: Add Submodules FIRST (Using Local Paths)
```bash
cd /Users/pacey/Documents/SourceCode/ganglia-core

# Add ganglia-common as submodule (using local path)
git submodule add ../ganglia-common ganglia_common

# Add ganglia-studio as submodule (using local path)
git submodule add ../ganglia-studio ganglia_studio

# Verify submodules point to local repos
cat .gitmodules
# Should show:
# [submodule "ganglia_common"]
#   path = ganglia_common
#   url = ../ganglia-common
# [submodule "ganglia_studio"]
#   path = ganglia_studio
#   url = ../ganglia-studio

# Commit submodules
git add .gitmodules ganglia_common ganglia_studio
git commit -m "Add ganglia-common and ganglia-studio submodules (local paths)"
```

**Note:** Using relative paths (`../ganglia-common`) means:
- Submodules point to sibling directories locally
- When pushed to GitHub, relative paths still work
- You can develop in common/studio and see changes immediately in core
- No need to push common/studio to test in core

### 3.4: Copy Files from GANGLIA
```bash
cd /Users/pacey/Documents/SourceCode

# Core application
cp GANGLIA/ganglia.py ganglia-core/src/ganglia_core/main.py
cp GANGLIA/conversational_interface.py ganglia-core/src/ganglia_core/core/conversation.py
cp GANGLIA/conversation_context.py ganglia-core/src/ganglia_core/core/context.py
cp GANGLIA/session_logger.py ganglia-core/src/ganglia_core/core/session_logger.py

# Audio
cp GANGLIA/audio_turn_indicator.py ganglia-core/src/ganglia_core/audio/turn_indicators.py

# Input
cp -r GANGLIA/dictation/* ganglia-core/src/ganglia_core/input/
cp GANGLIA/hotwords.py ganglia-core/src/ganglia_core/input/

# Config
cp GANGLIA/parse_inputs.py ganglia-core/src/ganglia_core/config/parser.py
cp -r GANGLIA/config/* ganglia-core/config/

# Integrations
cp -r GANGLIA/social_media/* ganglia-core/src/ganglia_core/integrations/social_media/ 2>/dev/null || true

# Media assets
cp GANGLIA/media/* ganglia-core/media/ 2>/dev/null || true

# Scripts
cp GANGLIA/fetch_and_display_logs.py ganglia-core/scripts/ 2>/dev/null || true
cp GANGLIA/*.sh ganglia-core/scripts/ 2>/dev/null || true

# Docs
cp GANGLIA/*.md ganglia-core/docs/ 2>/dev/null || true

# Tests (selective)
cp GANGLIA/tests/conftest.py ganglia-core/tests/
cp GANGLIA/tests/test_helpers.py ganglia-core/tests/
cp GANGLIA/tests/unit/test_session_logger.py ganglia-core/tests/unit/core/ 2>/dev/null || true
cp GANGLIA/tests/unit/test_*dictation*.py ganglia-core/tests/unit/input/ 2>/dev/null || true
cp GANGLIA/tests/unit/test_hotword*.py ganglia-core/tests/unit/input/ 2>/dev/null || true
```

### 3.5: Create __init__.py Files
```bash
cd /Users/pacey/Documents/SourceCode/ganglia-core

cat > src/ganglia_core/__init__.py << 'EOF'
"""GANGLIA Core - Conversational AI system."""

__version__ = "0.1.0"
EOF

touch src/ganglia_core/core/__init__.py
touch src/ganglia_core/audio/__init__.py
touch src/ganglia_core/input/__init__.py
touch src/ganglia_core/config/__init__.py
touch src/ganglia_core/integrations/__init__.py
touch src/ganglia_core/integrations/social_media/__init__.py
```

### 3.6: Create Studio Integration Client
```bash
cd /Users/pacey/Documents/SourceCode/ganglia-core

cat > src/ganglia_core/integrations/studio_client.py << 'EOF'
"""Optional ganglia-studio integration."""

import subprocess
from pathlib import Path
from ganglia_common.logger import Logger


class StudioClient:
    """Client for ganglia-studio integration."""

    def __init__(self):
        studio_path = Path(__file__).parent.parent.parent.parent / "ganglia_studio"
        self.available = studio_path.exists()

        if self.available:
            Logger.print_info("ganglia-studio available")
        else:
            Logger.print_warning("ganglia-studio not available (optional)")

    def generate_video(self, config_path: str) -> bool:
        """Generate video using ganglia-studio."""
        if not self.available:
            Logger.print_error("ganglia-studio not available")
            return False

        try:
            result = subprocess.run(
                ["ganglia-studio", "video", "--config", config_path],
                check=True,
                capture_output=True,
                text=True
            )
            Logger.print_info(result.stdout)
            return True
        except Exception as e:
            Logger.print_error(f"Studio generation failed: {e}")
            return False

    def is_available(self) -> bool:
        """Check if studio is available."""
        return self.available
EOF
```

### 3.7: Refactor Imports
```bash
cd /Users/pacey/Documents/SourceCode/ganglia-core

# Update all imports in src/ganglia_core/:
# from logger import Logger → from ganglia_common.logger import Logger
# from query_dispatch import * → from ganglia_common.query_dispatch import *
# from tts import GoogleTTS → from ganglia_common.tts.google_tts import GoogleTTS
# from conversational_interface import * → from ganglia_core.core.conversation import *
# from parse_inputs import * → from ganglia_core.config.parser import *
# from dictation.* → from ganglia_core.input.*

# This requires editing EVERY .py file
```

### 3.8: Create Package Configuration
```bash
cd /Users/pacey/Documents/SourceCode/ganglia-core

cat > setup.py << 'EOF'
from setuptools import setup, find_packages

setup(
    name="ganglia-core",
    version="0.1.0",
    description="Conversational AI system",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.9",
    install_requires=[
        "SpeechRecognition>=3.10.0",
        "sounddevice>=0.4.6",
        "pyaudio>=0.2.13",
        "blessed>=1.20.0",
        "pandas>=2.0.0",
        "google-cloud-speech>=2.21.0",
    ],
    entry_points={
        "console_scripts": [
            "ganglia=ganglia_core.main:main",
        ],
    },
)
EOF

cat > requirements.txt << 'EOF'
# Submodules (install in dev mode)
-e ./ganglia_common
# -e ./ganglia_studio  # Optional

# Core dependencies
SpeechRecognition>=3.10.0
sounddevice>=0.4.6
pyaudio>=0.2.13
blessed>=1.20.0
pandas>=2.0.0
google-cloud-speech>=2.21.0
google-api-python-client>=2.108.0
EOF

cat > .gitignore << 'EOF'
__pycache__/
*.py[cod]
.Python
build/
dist/
*.egg-info/
.pytest_cache/
.env
.venv
venv/
logs/
output/
*.mp3
*.wav
EOF

cat > README.md << 'EOF'
# ganglia-core

Conversational AI system with voice interaction.

## Architecture

- **ganglia-core**: Main conversational AI (this repo)
- **ganglia-common**: Shared utilities (submodule)
- **ganglia-studio**: Multimedia generation (optional submodule)

## Installation

```bash
# Clone with submodules
git clone --recursive git@github.com:YOUR_USERNAME/ganglia-core.git
cd ganglia-core

# Or initialize submodules
git submodule update --init --recursive

# Install
pip install -r requirements.txt
```

## Usage

```bash
python src/ganglia_core/main.py
```

Fresh start from GANGLIA codebase with modular architecture.
EOF
```

### 3.9: Test ganglia-core
```bash
cd /Users/pacey/Documents/SourceCode/ganglia-core

# Initialize submodules
git submodule update --init --recursive

# Create venv
python3 -m venv venv
source venv/bin/activate

# Install
pip install -r requirements.txt

# Test imports
python -c "from ganglia_core.main import main; print('✓ Main')"
python -c "from ganglia_core.core.conversation import Conversation; print('✓ Conversation')"
python -c "from ganglia_common.logger import Logger; print('✓ Logger from common')"
```

### 3.10: Commit and Push
```bash
cd /Users/pacey/Documents/SourceCode/ganglia-core

git add .
git commit -m "Initial commit: ganglia-core conversational AI

Components:
- Core conversation management
- Voice input (VAD, wake word, dictation)
- Audio turn indicators
- Session logging
- Optional studio integration

Submodules:
- ganglia-common (shared utilities)
- ganglia-studio (multimedia generation)

Fresh start from GANGLIA codebase with modular architecture."

git remote add origin git@github.com:YOUR_USERNAME/ganglia-core.git
git push -u origin main
```

---

## Phase 4: Testing & Validation

**Time Estimate**: 1-2 hours

### 4.1: Test Each Repository Independently
```bash
# Test ganglia-common
cd /Users/pacey/Documents/SourceCode/ganglia-common
source venv/bin/activate
pytest tests/ -v
python -c "from ganglia_common.logger import Logger; print('✓')"

# Test ganglia-studio
cd /Users/pacey/Documents/SourceCode/ganglia-studio
source venv/bin/activate
ganglia-studio --help
python -c "from ganglia_studio.video.pipeline import text_to_video; print('✓')"

# Test ganglia-core
cd /Users/pacey/Documents/SourceCode/ganglia-core
source venv/bin/activate
python -c "from ganglia_core.main import main; print('✓')"
python -c "from ganglia_core.integrations.studio_client import StudioClient; print('✓')"
```

### 4.2: Test Submodule Integration
```bash
cd /Users/pacey/Documents/SourceCode/ganglia-core

# Update submodules
git submodule update --remote

# Test that common imports work
python -c "
from ganglia_common.logger import Logger
from ganglia_common.query_dispatch import ChatGPTQueryDispatcher
print('✓ Common imports work')
"

# Test studio availability
python -c "
from ganglia_core.integrations.studio_client import StudioClient
client = StudioClient()
print(f'Studio available: {client.is_available()}')
"
```

### 4.3: Verify Original GANGLIA Still Works
```bash
# Most important: verify we didn't break anything
cd /Users/pacey/Documents/SourceCode/GANGLIA
source venv/bin/activate
python ganglia.py --help  # Should still work!
```

---

## Parallel Development Workflow

Now you have both systems side-by-side:

```
/Users/pacey/Documents/SourceCode/
├── GANGLIA/                    ← Original (still works, untouched)
├── ganglia-common/             ← New standalone repo
├── ganglia-studio/             ← New standalone repo
└── ganglia-core/               ← New main repo
    ├── ganglia_common/         ← Submodule → ../ganglia-common
    └── ganglia_studio/         ← Submodule → ../ganglia-studio
```

**Local Development Benefits:**
- Edit code in `/Users/pacey/Documents/SourceCode/ganglia-common/`
- Changes immediately reflected in `/Users/pacey/Documents/SourceCode/ganglia-core/ganglia_common/`
- No need to push/pull to test integration
- Can work on all three repos simultaneously

### Development Patterns

**Working on shared utilities:**
```bash
# Edit in standalone repo
cd /Users/pacey/Documents/SourceCode/ganglia-common
# Make changes to src/ganglia_common/logger.py
git add .
git commit -m "feat: improve logging"
git push

# Changes are immediately available in ganglia-core
cd /Users/pacey/Documents/SourceCode/ganglia-core
# The submodule at ganglia_common/ already has your changes!
# Just update the submodule pointer when ready:
cd ganglia_common && git pull origin main && cd ..
git add ganglia_common
git commit -m "Update ganglia-common to latest"
git push
```

**Working on multimedia:**
```bash
# Edit in standalone repo
cd /Users/pacey/Documents/SourceCode/ganglia-studio
# Make changes to src/ganglia_studio/video/pipeline.py
git add .
git commit -m "feat: improve video generation"
git push

# Update in ganglia-core if needed
cd /Users/pacey/Documents/SourceCode/ganglia-core
cd ganglia_studio && git pull origin main && cd ..
git add ganglia_studio
git commit -m "Update ganglia-studio to latest"
git push
```

**Working on chatbot core:**
```bash
cd /Users/pacey/Documents/SourceCode/ganglia-core
# Make changes to src/ganglia_core/core/conversation.py
git add .
git commit -m "feat: improve conversation handling"
git push
```

**Testing integration locally:**
```bash
cd /Users/pacey/Documents/SourceCode/ganglia-core
source venv/bin/activate

# All changes in sibling repos are immediately visible
python src/ganglia_core/main.py

# No need to reinstall or update submodules during development
# Submodules point to local working directories
```

**Testing against old GANGLIA:**
```bash
# Terminal 1: Run old GANGLIA
cd /Users/pacey/Documents/SourceCode/GANGLIA
source venv/bin/activate
python ganglia.py

# Terminal 2: Run new ganglia-core
cd /Users/pacey/Documents/SourceCode/ganglia-core
source venv/bin/activate
python src/ganglia_core/main.py

# Compare behavior side-by-side
```

**Quick navigation aliases (add to ~/.zshrc):**
```bash
alias cdg='cd /Users/pacey/Documents/SourceCode/GANGLIA'
alias cdgc='cd /Users/pacey/Documents/SourceCode/ganglia-common'
alias cdgs='cd /Users/pacey/Documents/SourceCode/ganglia-studio'
alias cdgcore='cd /Users/pacey/Documents/SourceCode/ganglia-core'
```

---

## When Ready to Switch Over

When you're confident in the new structure:

### 1. Archive Original GANGLIA
```bash
cd /Users/pacey/Documents/SourceCode/GANGLIA
# Add deprecation notice to README
echo "⚠️ DEPRECATED: This repo has been superseded by ganglia-core" >> README.md
git add README.md
git commit -m "Deprecate: Superseded by ganglia-core"
git push

# Archive on GitHub (Settings → Archive this repository)
```

### 2. Update Documentation
- Point all docs to new repos
- Update any CI/CD references
- Update installation instructions

### 3. Cleanup (Optional)
```bash
# Move original GANGLIA to archive directory
cd /Users/pacey/Documents/SourceCode
mkdir archive
mv GANGLIA archive/GANGLIA_deprecated
```

---

## Rollback Strategy

If anything goes wrong with new repos:

```bash
# Simply delete them
cd /Users/pacey/Documents/SourceCode
rm -rf ganglia-common ganglia-studio ganglia-core

# Original GANGLIA is completely untouched - just keep using it
cd GANGLIA
# business as usual
```

---

## Success Criteria

✅ All three new repos created and pushed to GitHub
✅ ganglia-common installs and imports work
✅ ganglia-studio CLI works
✅ ganglia-core can import from submodules
✅ **Original GANGLIA still works unchanged**
✅ Can develop in both old and new repos simultaneously

---

## Timeline Summary

- **Phase 1 (ganglia-common)**: 1.5-2 hours
- **Phase 2 (ganglia-studio)**: 2-3 hours
- **Phase 3 (ganglia-core)**: 2-3 hours
- **Phase 4 (Testing)**: 1-2 hours

**Total**: 6.5-10 hours

Much simpler than the original plan because:
- No git history preservation needed
- No complex repo surgery
- Original repo untouched
- Simple file copying
- Low risk

---

## Key Benefits Recap

1. ✅ **Zero Risk**: Original GANGLIA never touched
2. ✅ **Always Working**: Can fall back to GANGLIA anytime
3. ✅ **Parallel Testing**: Compare old vs new side-by-side
4. ✅ **Gradual Migration**: Switch when confident
5. ✅ **Simple Rollback**: Just delete new repos
6. ✅ **Clean History**: Fresh start, no legacy baggage
7. ✅ **Flexible Timeline**: No rush to complete migration
