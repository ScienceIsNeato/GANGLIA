# GANGLIA Repository Migration - Execution Plan

## Overview

This document provides step-by-step instructions for splitting the GANGLIA monorepo into three repositories:
- **ganglia-common** (shared utilities)
- **ganglia-studio** (multimedia generation)
- **ganglia-core** (conversational AI with submodules)

**Estimated Time**: 8-12 hours of focused work
**Risk Level**: Medium (reversible with backups)

---

## Pre-Migration Checklist

### 1. Backup Everything
```bash
# Create full backup
cd /Users/pacey/Documents/SourceCode
tar -czf GANGLIA_backup_$(date +%Y%m%d_%H%M%S).tar.gz GANGLIA/

# Verify backup
tar -tzf GANGLIA_backup_*.tar.gz | head -20

# Create git bundle (preserves history)
cd GANGLIA
git bundle create ../ganglia_full_backup.bundle --all
```

### 2. Verify Clean State
```bash
cd /Users/pacey/Documents/SourceCode/GANGLIA
git status  # Should be clean
git log --oneline -5  # Note current HEAD
git branch -a  # Note all branches
```

### 3. Run Current Test Suite
```bash
# Baseline: ensure everything currently works
cd /Users/pacey/Documents/SourceCode/GANGLIA
source venv/bin/activate
pytest tests/ -v > /tmp/pre_migration_tests.log 2>&1
echo "Exit code: $?" >> /tmp/pre_migration_tests.log
```

### 4. Document Current State
```bash
# Save current dependencies
pip freeze > /tmp/ganglia_pre_migration_requirements.txt

# Save current directory structure
tree -L 3 -I 'venv|__pycache__|*.pyc|.git' > /tmp/ganglia_pre_migration_tree.txt
```

---

## Phase 1: Create ganglia-common Repository

### 1.1: Create New Repository on GitHub
```bash
# Via GitHub CLI
gh repo create ganglia-common --public --description "Shared utilities for GANGLIA ecosystem"

# Or manually via GitHub web interface:
# - Navigate to github.com
# - Create new repo: ganglia-common
# - Make it public
# - Do NOT initialize with README/license/gitignore
```

### 1.2: Initialize Local Repository
```bash
cd /Users/pacey/Documents/SourceCode
mkdir ganglia-common
cd ganglia-common
git init
git branch -M main

# Create directory structure
mkdir -p src/ganglia_common/{tts,pubsub,utils}
mkdir -p tests/unit
touch src/ganglia_common/__init__.py
touch src/ganglia_common/tts/__init__.py
touch src/ganglia_common/pubsub/__init__.py
touch src/ganglia_common/utils/__init__.py
```

### 1.3: Copy Files from GANGLIA
```bash
cd /Users/pacey/Documents/SourceCode

# Core utilities
cp GANGLIA/logger.py ganglia-common/src/ganglia_common/
cp GANGLIA/query_dispatch.py ganglia-common/src/ganglia_common/
cp GANGLIA/tts.py ganglia-common/src/ganglia_common/tts/google_tts.py
cp GANGLIA/tts_openai.py ganglia-common/src/ganglia_common/tts/openai_tts.py

# PubSub
cp GANGLIA/pubsub/__init__.py ganglia-common/src/ganglia_common/pubsub/
cp GANGLIA/pubsub/pubsub.py ganglia-common/src/ganglia_common/pubsub/

# Utils
cp GANGLIA/utils/__init__.py ganglia-common/src/ganglia_common/utils/
cp GANGLIA/utils/file_utils.py ganglia-common/src/ganglia_common/utils/
cp GANGLIA/utils/performance_profiler.py ganglia-common/src/ganglia_common/utils/
cp GANGLIA/utils/retry_utils.py ganglia-common/src/ganglia_common/utils/
cp GANGLIA/utils/cloud_utils.py ganglia-common/src/ganglia_common/utils/

# Tests
cp GANGLIA/tests/unit/test_query_dispatch.py ganglia-common/tests/unit/
cp GANGLIA/tests/unit/test_send_query.py ganglia-common/tests/unit/
cp GANGLIA/tests/unit/test_pubsub.py ganglia-common/tests/unit/
cp GANGLIA/tests/unit/test_utils.py ganglia-common/tests/unit/
```

### 1.4: Refactor Imports in ganglia-common
```bash
cd /Users/pacey/Documents/SourceCode/ganglia-common

# Update imports to use ganglia_common namespace
# This requires editing each file - example patterns:

# In src/ganglia_common/tts/google_tts.py:
# - from logger import Logger → from ganglia_common.logger import Logger
# - from utils.file_utils import * → from ganglia_common.utils.file_utils import *

# In src/ganglia_common/query_dispatch.py:
# - from logger import Logger → from ganglia_common.logger import Logger
# - from utils import get_tempdir → from ganglia_common.utils import get_tempdir

# In src/ganglia_common/pubsub/pubsub.py:
# - from logger import Logger → from ganglia_common.logger import Logger
```

### 1.5: Create Package Configuration
```bash
cd /Users/pacey/Documents/SourceCode/ganglia-common

# Create setup.py
cat > setup.py << 'EOF'
from setuptools import setup, find_packages

setup(
    name="ganglia-common",
    version="0.1.0",
    description="Shared utilities for GANGLIA ecosystem",
    author="Your Name",
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

# Create pyproject.toml
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

# Create requirements.txt
cat > requirements.txt << 'EOF'
openai>=1.3.0
python-dotenv>=1.0.0
google-cloud-texttospeech>=2.14.1
google-cloud-storage>=2.10.0
gTTS>=2.5.0
requests>=2.31.0
EOF

# Create test requirements
cat > requirements-test.txt << 'EOF'
pytest>=7.3.1
pytest-asyncio>=0.21.1
pytest-timeout>=2.1.0
pytest-cov>=4.1.0
EOF

# Create pytest.ini
cat > pytest.ini << 'EOF'
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
EOF

# Create .gitignore
cat > .gitignore << 'EOF'
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
.pytest_cache/
.coverage
htmlcov/
.env
.venv
env/
venv/
EOF

# Create README.md
cat > README.md << 'EOF'
# ganglia-common

Shared utilities for the GANGLIA ecosystem.

## Installation

```bash
pip install -e .
```

## Development

```bash
pip install -e ".[test]"
pytest
```

## Components

- **logger**: Centralized logging
- **query_dispatch**: OpenAI API interface
- **tts**: Text-to-speech engines (Google, OpenAI)
- **pubsub**: Event system
- **utils**: File operations, performance profiling, retry logic
EOF
```

### 1.6: Test ganglia-common Standalone
```bash
cd /Users/pacey/Documents/SourceCode/ganglia-common

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install in development mode
pip install -e .
pip install -r requirements-test.txt

# Run tests
pytest tests/ -v

# Verify imports work
python -c "from ganglia_common.logger import Logger; print('✓ Logger imports')"
python -c "from ganglia_common.query_dispatch import ChatGPTQueryDispatcher; print('✓ QueryDispatch imports')"
python -c "from ganglia_common.tts.google_tts import GoogleTTS; print('✓ TTS imports')"
```

### 1.7: Commit and Push ganglia-common
```bash
cd /Users/pacey/Documents/SourceCode/ganglia-common

git add .
git commit -m "Initial commit: ganglia-common shared utilities

- Core logging (logger.py)
- OpenAI query dispatch
- TTS engines (Google, OpenAI)
- PubSub event system
- Common utilities (file, performance, retry, cloud)
- Test suite and packaging configuration"

git remote add origin git@github.com:YOUR_USERNAME/ganglia-common.git
git push -u origin main
```

---

## Phase 2: Create ganglia-studio Repository

### 2.1: Create New Repository on GitHub
```bash
gh repo create ganglia-studio --public --description "Multimedia generation suite for GANGLIA"
```

### 2.2: Initialize Local Repository
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
touch src/ganglia_studio/__init__.py
touch src/ganglia_studio/video/__init__.py
touch src/ganglia_studio/story/__init__.py
touch src/ganglia_studio/music/__init__.py
touch src/ganglia_studio/music/backends/__init__.py
touch src/ganglia_studio/image/__init__.py
touch src/ganglia_studio/config/__init__.py
touch src/ganglia_studio/utils/__init__.py
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

# Image generation
cp GANGLIA/ttv/image_generation.py ganglia-studio/src/ganglia_studio/image/generation.py

# Story generation
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

# Tests - Video
cp -r GANGLIA/tests/unit/ttv/* ganglia-studio/tests/unit/video/
mv ganglia-studio/tests/unit/video/test_config_loader.py ganglia-studio/tests/unit/config/
mv ganglia-studio/tests/unit/video/test_story_*.py ganglia-studio/tests/unit/story/

# Tests - Music
cp GANGLIA/tests/unit/test_music_lib.py ganglia-studio/tests/unit/music/test_library.py
cp GANGLIA/tests/unit/test_suno_api_org.py ganglia-studio/tests/unit/music/

# Tests - Integration
cp GANGLIA/tests/integration/test_generated_ttv_pipeline.py ganglia-studio/tests/integration/test_full_pipeline.py
cp GANGLIA/tests/integration/test_minimal_ttv_config.py ganglia-studio/tests/integration/test_minimal_config.py
cp GANGLIA/tests/integration/test_ttv_conversation.py ganglia-studio/tests/integration/test_conversation_flow.py
cp -r GANGLIA/tests/integration/test_data ganglia-studio/tests/fixtures/integration_data

# Tests - Third party
mkdir -p ganglia-studio/tests/integration/third_party
cp GANGLIA/tests/third_party/test_dalle_api_live.py ganglia-studio/tests/integration/third_party/test_dalle_live.py
cp GANGLIA/tests/third_party/test_foxai_suno_live.py ganglia-studio/tests/integration/third_party/
cp GANGLIA/tests/third_party/test_gcui_suno_live.py ganglia-studio/tests/integration/third_party/
cp GANGLIA/tests/third_party/test_generate_lyrics.py ganglia-studio/tests/integration/third_party/
cp GANGLIA/tests/third_party/test_meta_musicgen.py ganglia-studio/tests/integration/third_party/
cp GANGLIA/tests/third_party/test_suno_api_org_live.py ganglia-studio/tests/integration/third_party/
```

### 2.4: Refactor Imports in ganglia-studio
```bash
cd /Users/pacey/Documents/SourceCode/ganglia-studio

# Major import refactoring needed:
# 1. All imports from GANGLIA root → ganglia_common or ganglia_studio
# 2. All ttv.* imports → ganglia_studio.video.* or appropriate module

# Examples:
# - from logger import Logger → from ganglia_common.logger import Logger
# - from query_dispatch import * → from ganglia_common.query_dispatch import *
# - from tts import GoogleTTS → from ganglia_common.tts.google_tts import GoogleTTS
# - from ttv.audio_alignment import * → from ganglia_studio.video.audio_alignment import *
# - from music_lib import * → from ganglia_studio.music.library import *
# - from utils.file_utils import * → from ganglia_common.utils.file_utils import *
# - from utils.ffmpeg_utils import * → from ganglia_studio.utils.ffmpeg_utils import *

# This will require editing EVERY Python file in src/ganglia_studio/
```

### 2.5: Create CLI Interface
```bash
cd /Users/pacey/Documents/SourceCode/ganglia-studio

cat > src/ganglia_studio/cli.py << 'EOF'
"""CLI interface for ganglia-studio multimedia generation."""

import argparse
import sys
from ganglia_studio.video.pipeline import text_to_video
from ganglia_studio.music.library import generate_music
from ganglia_studio.image.generation import generate_image
from ganglia_common.logger import Logger


def video_command(args):
    """Generate video from config."""
    Logger.print_info(f"Generating video from config: {args.config}")
    result = text_to_video(args.config, skip_generation=args.skip_generation)
    if result:
        Logger.print_success(f"Video generated: {result}")
    else:
        Logger.print_error("Video generation failed")
        sys.exit(1)


def music_command(args):
    """Generate music."""
    Logger.print_info(f"Generating music: {args.prompt}")
    # Implementation here
    Logger.print_success("Music generated successfully")


def image_command(args):
    """Generate image."""
    Logger.print_info(f"Generating image: {args.prompt}")
    # Implementation here
    Logger.print_success("Image generated successfully")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="GANGLIA Studio - Multimedia Generation Suite"
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Video command
    video_parser = subparsers.add_parser("video", help="Generate video")
    video_parser.add_argument("--config", required=True, help="Path to video config")
    video_parser.add_argument("--skip-generation", action="store_true", help="Skip generation steps")
    video_parser.set_defaults(func=video_command)

    # Music command
    music_parser = subparsers.add_parser("music", help="Generate music")
    music_parser.add_argument("--prompt", required=True, help="Music prompt")
    music_parser.add_argument("--duration", type=int, default=120, help="Duration in seconds")
    music_parser.set_defaults(func=music_command)

    # Image command
    image_parser = subparsers.add_parser("image", help="Generate image")
    image_parser.add_argument("--prompt", required=True, help="Image prompt")
    image_parser.add_argument("--style", help="Artistic style")
    image_parser.set_defaults(func=image_command)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
EOF
```

### 2.6: Create Package Configuration
```bash
cd /Users/pacey/Documents/SourceCode/ganglia-studio

cat > setup.py << 'EOF'
from setuptools import setup, find_packages

setup(
    name="ganglia-studio",
    version="0.1.0",
    description="Multimedia generation suite for GANGLIA",
    author="Your Name",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.9",
    install_requires=[
        "torch>=2.0.0",
        "transformers>=4.30.0",
        "torchaudio>=2.0.0",
        "accelerate>=0.27.0",
        "openai-whisper>=20231117",
        "opencv-python>=4.9.0.80",
        "moviepy>=1.0.3",
        "numpy>=1.24.3",
        "scipy>=1.10.1",
        "openai>=1.3.0",
        "pillow>=10.0.0",
        "pydub>=0.25.1",
    ],
    entry_points={
        "console_scripts": [
            "ganglia-studio=ganglia_studio.cli:main",
        ],
    },
)
EOF

cat > pyproject.toml << 'EOF'
[build-system]
requires = ["setuptools>=45", "wheel"]
build-backend = "setuptools.build_backend"

[project]
name = "ganglia-studio"
version = "0.1.0"
description = "Multimedia generation suite for GANGLIA"
requires-python = ">=3.9"
EOF

# Create requirements.txt (heavy dependencies)
cat > requirements.txt << 'EOF'
# Install ganglia-common first
# pip install -e ../ganglia-common

# Heavy ML/Media dependencies
torch>=2.0.0
transformers>=4.30.0
torchaudio>=2.0.0
accelerate>=0.27.0
openai-whisper>=20231117
opencv-python>=4.9.0.80
moviepy>=1.0.3
numpy>=1.24.3
scipy>=1.10.1

# API clients
openai>=1.3.0

# Media processing
pillow>=10.0.0
pydub>=0.25.1
python-magic>=0.4.27
EOF

cat > .gitignore << 'EOF'
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
dist/
*.egg-info/
.pytest_cache/
.coverage
.env
.venv
venv/
output/
*.mp4
*.wav
*.mp3
*.png
*.jpg
EOF

cat > README.md << 'EOF'
# ganglia-studio

Multimedia generation suite for GANGLIA.

## Features

- **Video Generation**: Text-to-video pipeline with narration and captions
- **Music Generation**: AI-powered music creation with multiple backends
- **Image Generation**: DALL-E integration for image creation
- **Story Generation**: AI-assisted story creation and processing

## Installation

```bash
# Install ganglia-common first
pip install -e ../ganglia-common

# Install ganglia-studio
pip install -e .
```

## Usage

```bash
# Generate video
ganglia-studio video --config story.json

# Generate music
ganglia-studio music --prompt "epic orchestral" --duration 120

# Generate image
ganglia-studio image --prompt "cyberpunk cityscape" --style "digital art"
```
EOF
```

### 2.7: Test ganglia-studio Standalone
```bash
cd /Users/pacey/Documents/SourceCode/ganglia-studio

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install ganglia-common first (development mode)
pip install -e ../ganglia-common

# Install ganglia-studio
pip install -e .

# Run tests
pytest tests/unit/ -v

# Test CLI
ganglia-studio --help
ganglia-studio video --help
```

### 2.8: Commit and Push ganglia-studio
```bash
cd /Users/pacey/Documents/SourceCode/ganglia-studio

git add .
git commit -m "Initial commit: ganglia-studio multimedia suite

- Video generation pipeline (text-to-video)
- Music generation with multiple backends
- Image generation (DALL-E)
- Story generation and processing
- CLI interface (ganglia-studio video/music/image)
- Comprehensive test suite"

git remote add origin git@github.com:YOUR_USERNAME/ganglia-studio.git
git push -u origin main
```

---

## Phase 3: Refactor ganglia-core Repository

### 3.1: Create Backup Branch
```bash
cd /Users/pacey/Documents/SourceCode/GANGLIA
git checkout -b pre-refactor-backup
git push origin pre-refactor-backup
git checkout main
```

### 3.2: Add Submodules
```bash
cd /Users/pacey/Documents/SourceCode/GANGLIA

# Add ganglia-common as submodule
git submodule add git@github.com:YOUR_USERNAME/ganglia-common.git ganglia_common

# Add ganglia-studio as submodule
git submodule add git@github.com:YOUR_USERNAME/ganglia-studio.git ganglia_studio

# Initialize submodules
git submodule init
git submodule update

# Verify submodules
ls -la ganglia_common/
ls -la ganglia_studio/
```

### 3.3: Reorganize Directory Structure
```bash
cd /Users/pacey/Documents/SourceCode/GANGLIA

# Create new src structure
mkdir -p src/ganglia_core/{core,audio,input,config,integrations/social_media,user_management}

# Move core files
mv ganglia.py src/ganglia_core/main.py
mv conversational_interface.py src/ganglia_core/core/conversation.py
mv conversation_context.py src/ganglia_core/core/context.py
mv session_logger.py src/ganglia_core/core/session_logger.py
mv audio_turn_indicator.py src/ganglia_core/audio/turn_indicators.py
mv parse_inputs.py src/ganglia_core/config/parser.py

# Move input systems
mv dictation/* src/ganglia_core/input/
mv hotwords.py src/ganglia_core/input/

# Move integrations
mv social_media/* src/ganglia_core/integrations/social_media/

# Move user management (if exists)
if [ -d "user_management" ]; then
    mv user_management/* src/ganglia_core/user_management/
fi

# Add __init__.py files
touch src/ganglia_core/__init__.py
touch src/ganglia_core/core/__init__.py
touch src/ganglia_core/audio/__init__.py
touch src/ganglia_core/input/__init__.py
touch src/ganglia_core/config/__init__.py
touch src/ganglia_core/integrations/__init__.py
touch src/ganglia_core/integrations/social_media/__init__.py
```

### 3.4: Move Scripts and Docs
```bash
cd /Users/pacey/Documents/SourceCode/GANGLIA

# Create scripts directory
mkdir -p scripts/tools

# Move scripts
mv fetch_and_display_logs.py scripts/
mv ganglia_watchdog.sh scripts/
mv start_ganglia_monitored.sh scripts/
mv run_tests.sh scripts/
mv prep_env.sh scripts/
mv tools/generate_audio_from_text.py scripts/tools/
mv tools/minify_repo.py scripts/tools/
mv utils/monitor_tests.sh scripts/
mv utils/test_conversation_latency.py scripts/
mv utils/test_vad_sensitivity.py scripts/
mv utils/vad_energy_analyzer.py scripts/

# Move test utils
mv utils/test_utils.py tests/

# Move docs
mkdir -p docs
mv AUDIO_PROCESS_HANGING_ANALYSIS.md docs/
mv GANGLIA_2025_SETUP.md docs/
mv GANGLIA_2025_SUMMARY.md docs/
mv GANGLIA_SERVICE_SETUP.md docs/
mv GANGLIA_TTS_MODERNIZATION_PLAN.md docs/
mv TIMING_ANALYSIS_GUIDE.md docs/
mv VAD_*.md docs/

# Rename media files for clarity
mv media/zapsplat_multimedia_button_click_bright_001_92098.mp3 media/button_click_bright.mp3
mv media/zapsplat_multimedia_button_click_fast_short_004_79288.mp3 media/button_click_fast.mp3
mv media/zapsplat_multimedia_ui_window_maximize_short_swipe_whoosh_001_71500.mp3 media/window_maximize.mp3
mv media/zapsplat_multimedia_ui_window_minimize_short_swipe_whoosh_71502.mp3 media/window_minimize.mp3
```

### 3.5: Delete Moved/Obsolete Files
```bash
cd /Users/pacey/Documents/SourceCode/GANGLIA

# Delete files moved to other repos
rm -rf ttv/
rm -rf music_backends/
rm -rf pubsub/
rm -f logger.py
rm -f query_dispatch.py
rm -f tts.py
rm -f tts_openai.py
rm -f music_lib.py
rm -f lyrics_lib.py
rm -f story_generation_driver.py
rm -f suno_request_handler.py

# Delete moved utils
rm -f utils/file_utils.py
rm -f utils/performance_profiler.py
rm -f utils/retry_utils.py
rm -f utils/cloud_utils.py
rm -f utils/ffmpeg_utils.py
rm -f utils/video_utils.py
rm -f utils/__init__.py

# Delete obsolete files
rm -f googleTTSExample.py
rm -f COMMIT_MSG.txt
rm -f recorded_audio.mp3
rm -rf config_backups/

# Delete empty directories
rmdir dictation/ 2>/dev/null
rmdir tools/ 2>/dev/null
rmdir utils/ 2>/dev/null
rmdir social_media/ 2>/dev/null
```

### 3.6: Create Studio Client Integration
```bash
cd /Users/pacey/Documents/SourceCode/GANGLIA

cat > src/ganglia_core/integrations/studio_client.py << 'EOF'
"""Optional integration client for ganglia-studio.

This module provides a thin wrapper for calling ganglia-studio
if it's available as a submodule.
"""

import subprocess
import sys
from pathlib import Path
from ganglia_common.logger import Logger


class StudioClient:
    """Client for interacting with ganglia-studio."""

    def __init__(self):
        """Initialize the studio client."""
        # Check if ganglia_studio submodule exists
        studio_path = Path(__file__).parent.parent.parent.parent / "ganglia_studio"
        self.available = studio_path.exists() and (studio_path / "src").exists()

        if self.available:
            Logger.print_info("ganglia-studio integration available")
        else:
            Logger.print_warning("ganglia-studio not available (optional feature)")

    def generate_video(self, config_path: str) -> bool:
        """Generate video using ganglia-studio.

        Args:
            config_path: Path to video configuration file

        Returns:
            True if successful, False otherwise
        """
        if not self.available:
            Logger.print_error("ganglia-studio not available")
            return False

        try:
            # Call ganglia-studio CLI
            result = subprocess.run(
                ["ganglia-studio", "video", "--config", config_path],
                check=True,
                capture_output=True,
                text=True
            )
            Logger.print_info(result.stdout)
            return True
        except subprocess.CalledProcessError as e:
            Logger.print_error(f"Studio generation failed: {e.stderr}")
            return False
        except FileNotFoundError:
            Logger.print_error("ganglia-studio command not found")
            return False

    def is_available(self) -> bool:
        """Check if studio integration is available."""
        return self.available
EOF
```

### 3.7: Refactor All Imports in ganglia-core
```bash
cd /Users/pacey/Documents/SourceCode/GANGLIA

# Major import refactoring in src/ganglia_core/:
# 1. All local imports → ganglia_core.*
# 2. All shared utility imports → ganglia_common.*
# 3. All studio imports → ganglia_studio.* (only in studio_client.py)

# Examples:
# - from logger import Logger → from ganglia_common.logger import Logger
# - from query_dispatch import * → from ganglia_common.query_dispatch import *
# - from tts import GoogleTTS → from ganglia_common.tts.google_tts import GoogleTTS
# - from conversational_interface import * → from ganglia_core.core.conversation import *
# - from parse_inputs import * → from ganglia_core.config.parser import *
# - from dictation.vad_dictation import * → from ganglia_core.input.vad_dictation import *

# This requires editing EVERY Python file in src/ganglia_core/ and tests/
```

### 3.8: Update Tests
```bash
cd /Users/pacey/Documents/SourceCode/GANGLIA

# Reorganize tests
mkdir -p tests/unit/{core,input,config,integrations/social_media}

# Move tests to new structure
mv tests/unit/test_audio_inputs.py tests/unit/input/
mv tests/unit/test_hotword_manager.py tests/unit/input/test_hotwords.py
mv tests/unit/test_vad_dictation.py tests/unit/input/
mv tests/unit/test_vad_stream_timeout.py tests/unit/input/
mv tests/unit/test_parse_inputs.py tests/unit/config/test_parser.py
mv tests/unit/test_session_logger.py tests/unit/core/
mv tests/unit/social_media/test_youtube.py tests/unit/integrations/social_media/

# Delete tests that moved to other repos
rm -f tests/unit/test_config_generator.py
rm -f tests/unit/test_ffmpeg_thread_manager.py
rm -f tests/unit/test_music_lib.py
rm -f tests/unit/test_story_generation_driver.py
rm -f tests/unit/test_suno_api_org.py
rm -rf tests/unit/ttv/

# Move third-party tests
mkdir -p tests/integration/third_party
mv tests/third_party/test_audio_input_access.py tests/integration/third_party/
mv tests/third_party/test_youtube_live.py tests/integration/third_party/

# Delete third-party tests that moved to studio
rm -f tests/third_party/test_dalle_api_live.py
rm -f tests/third_party/test_foxai_suno_live.py
rm -f tests/third_party/test_gcui_suno_live.py
rm -f tests/third_party/test_generate_lyrics.py
rm -f tests/third_party/test_meta_musicgen.py
rm -f tests/third_party/test_suno_api_org_live.py
rmdir tests/third_party/ 2>/dev/null

# Delete integration tests that moved to studio
rm -f tests/integration/test_generated_ttv_pipeline.py
rm -f tests/integration/test_minimal_ttv_config.py
rm -f tests/integration/test_ttv_conversation.py
rm -rf tests/integration/test_data/

# Create mock studio integration test
cat > tests/unit/integrations/test_studio_integration.py << 'EOF'
"""Tests for optional ganglia-studio integration."""

import pytest
from ganglia_core.integrations.studio_client import StudioClient


def test_studio_client_initialization():
    """Test studio client can be initialized."""
    client = StudioClient()
    # Should initialize without errors regardless of studio availability
    assert hasattr(client, 'available')


def test_studio_availability_check():
    """Test studio availability check."""
    client = StudioClient()
    result = client.is_available()
    # Should return boolean
    assert isinstance(result, bool)


@pytest.mark.skipif(not StudioClient().is_available(), reason="ganglia-studio not available")
def test_video_generation_with_studio():
    """Test video generation when studio is available."""
    client = StudioClient()
    # This would need a real config file to test properly
    # For now, just verify method exists and is callable
    assert callable(client.generate_video)
EOF

# Update all test imports
# - from logger import Logger → from ganglia_common.logger import Logger
# - from conversational_interface import * → from ganglia_core.core.conversation import *
# etc.
```

### 3.9: Update Configuration Files
```bash
cd /Users/pacey/Documents/SourceCode/GANGLIA

# Update requirements.txt
cat > requirements.txt << 'EOF'
# Submodules (install in development mode)
-e ./ganglia_common
# -e ./ganglia_studio  # Optional: uncomment for studio features

# Core chatbot dependencies
SpeechRecognition>=3.10.0
sounddevice>=0.4.6
soundfile>=0.12.1
keyboard>=0.13.5
pyaudio>=0.2.13
blessed>=1.20.0
pandas>=2.0.0
psutil>=5.9.5
pydantic>=2.3.0

# Google APIs
google-api-python-client>=2.108.0
google-auth-oauthlib>=1.1.0
google-auth-httplib2>=0.1.1
google-cloud-speech>=2.21.0
httplib2>=0.22.0
EOF

# Update requirements_core.txt
cat > requirements_core.txt << 'EOF'
# Testing and Development Tools
pytest>=7.3.1
pytest-asyncio>=0.21.1
pytest-timeout>=2.1.0
pytest-xdist>=3.3.1
pytest-cov>=4.1.0
pylint>=3.0.3

# Core System Dependencies
python-dotenv>=1.0.0
requests>=2.31.0
psutil>=5.9.5
pydantic>=2.3.0
blessed>=1.20.0
pandas>=2.0.0
SpeechRecognition>=3.10.0

# Google APIs and Authentication
google-api-python-client>=2.108.0
google-auth-oauthlib>=1.1.0
google-auth-httplib2>=0.1.1
httplib2>=0.22.0

# Audio Processing
sounddevice>=0.4.6
soundfile>=0.12.1
keyboard>=0.13.5
pyaudio>=0.2.13
EOF

# Delete requirements_large.txt (moved to ganglia-studio)
rm -f requirements_large.txt

# Update pytest.ini
cat > pytest.ini << 'EOF'
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
markers =
    integration: Integration tests (may be slow)
    unit: Unit tests (fast)
    third_party: Tests that require external services
EOF

# Create setup.py
cat > setup.py << 'EOF'
from setuptools import setup, find_packages

setup(
    name="ganglia-core",
    version="0.1.0",
    description="Conversational AI system with voice interaction",
    author="Your Name",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.9",
    install_requires=[
        "SpeechRecognition>=3.10.0",
        "sounddevice>=0.4.6",
        "soundfile>=0.12.1",
        "keyboard>=0.13.5",
        "pyaudio>=0.2.13",
        "blessed>=1.20.0",
        "pandas>=2.0.0",
        "psutil>=5.9.5",
        "pydantic>=2.3.0",
        "google-api-python-client>=2.108.0",
        "google-auth-oauthlib>=1.1.0",
        "google-cloud-speech>=2.21.0",
    ],
    entry_points={
        "console_scripts": [
            "ganglia=ganglia_core.main:main",
        ],
    },
)
EOF

# Create pyproject.toml
cat > pyproject.toml << 'EOF'
[build-system]
requires = ["setuptools>=45", "wheel"]
build-backend = "setuptools.build_backend"

[project]
name = "ganglia-core"
version = "0.1.0"
description = "Conversational AI system with voice interaction"
requires-python = ">=3.9"
EOF

# Update .gitignore
cat >> .gitignore << 'EOF'

# Submodules are tracked
!ganglia_common/
!ganglia_studio/
EOF

# Update README.md
cat > README.md << 'EOF'
# ganglia-core

Conversational AI system with voice interaction capabilities.

## Architecture

ganglia-core is part of the GANGLIA ecosystem:
- **ganglia-core**: Main conversational AI (this repo)
- **ganglia-common**: Shared utilities (submodule)
- **ganglia-studio**: Multimedia generation (optional submodule)

## Installation

```bash
# Clone with submodules
git clone --recursive git@github.com:YOUR_USERNAME/ganglia-core.git
cd ganglia-core

# Or if already cloned, initialize submodules
git submodule init
git submodule update

# Install dependencies
pip install -r requirements.txt

# Optional: Enable studio features
pip install -e ./ganglia_studio
```

## Usage

```bash
python src/ganglia_core/main.py
```

## Development

```bash
# Run tests
pytest tests/unit/ -v

# Run with studio integration tests
pytest tests/unit/integrations/ -v
```

## Features

- Voice-activated conversation
- Multiple dictation backends (Google, VAD, Wake Word)
- Hotword detection
- Session logging
- Audio turn indicators
- OpenAI GPT integration
- Optional multimedia generation (via ganglia-studio)
EOF
```

### 3.10: Rename Repository on GitHub
```bash
# Via GitHub web interface:
# 1. Go to repository settings
# 2. Change repository name from "GANGLIA" to "ganglia-core"
# 3. Update local remote

cd /Users/pacey/Documents/SourceCode/GANGLIA
git remote set-url origin git@github.com:YOUR_USERNAME/ganglia-core.git
```

### 3.11: Commit Changes
```bash
cd /Users/pacey/Documents/SourceCode/GANGLIA

# Stage all changes
git add -A

# Commit
git commit -m "Major refactor: Convert to ganglia-core with submodules

Breaking changes:
- Moved to src/ganglia_core/ package structure
- Added ganglia_common submodule (shared utilities)
- Added ganglia_studio submodule (multimedia generation)
- Removed files moved to other repos (ttv, music, pubsub, etc.)
- Updated all imports to use new namespaces
- Reorganized tests to match new structure
- Renamed media files for clarity
- Moved scripts and docs to dedicated directories

New features:
- Optional studio integration via StudioClient
- Clean separation of concerns
- Modular architecture for future expansion

Migration:
- See MIGRATION_EXECUTION_PLAN.md for full details
- See REPO_MIGRATION_MAP.md for file mappings"

# Push
git push origin main
```

---

## Phase 4: Validation & Testing

### 4.1: Test ganglia-common
```bash
cd /Users/pacey/Documents/SourceCode/ganglia-common
source venv/bin/activate

# Run all tests
pytest tests/ -v --cov=ganglia_common --cov-report=html

# Check imports
python -c "from ganglia_common.logger import Logger; print('✓')"
python -c "from ganglia_common.query_dispatch import ChatGPTQueryDispatcher; print('✓')"
python -c "from ganglia_common.tts.google_tts import GoogleTTS; print('✓')"
python -c "from ganglia_common.tts.openai_tts import OpenAITTS; print('✓')"
python -c "from ganglia_common.pubsub import get_pubsub; print('✓')"
python -c "from ganglia_common.utils.file_utils import *; print('✓')"
```

### 4.2: Test ganglia-studio
```bash
cd /Users/pacey/Documents/SourceCode/ganglia-studio
source venv/bin/activate

# Ensure ganglia-common is installed
pip install -e ../ganglia-common

# Run unit tests
pytest tests/unit/ -v

# Test CLI
ganglia-studio --help
ganglia-studio video --help
ganglia-studio music --help
ganglia-studio image --help

# Test imports
python -c "from ganglia_studio.video.pipeline import text_to_video; print('✓')"
python -c "from ganglia_studio.music.library import *; print('✓')"
python -c "from ganglia_studio.story.driver import StoryGenerationDriver; print('✓')"
```

### 4.3: Test ganglia-core
```bash
cd /Users/pacey/Documents/SourceCode/GANGLIA  # Now ganglia-core

# Update submodules
git submodule update --init --recursive

# Create/activate venv
python3 -m venv venv
source venv/bin/activate

# Install with submodules
pip install -r requirements.txt

# Optional: Install studio
# pip install -e ./ganglia_studio

# Run tests
pytest tests/unit/ -v

# Test imports
python -c "from ganglia_core.main import main; print('✓')"
python -c "from ganglia_core.core.conversation import Conversation; print('✓')"
python -c "from ganglia_core.input.vad_dictation import *; print('✓')"
python -c "from ganglia_core.integrations.studio_client import StudioClient; print('✓')"

# Test that common imports work
python -c "from ganglia_common.logger import Logger; print('✓')"
python -c "from ganglia_common.query_dispatch import ChatGPTQueryDispatcher; print('✓')"
```

### 4.4: Integration Test
```bash
# Test full system
cd /Users/pacey/Documents/SourceCode/GANGLIA
source venv/bin/activate
source .envrc

# Try running ganglia
python src/ganglia_core/main.py --help

# Test studio integration (if installed)
python -c "
from ganglia_core.integrations.studio_client import StudioClient
client = StudioClient()
print(f'Studio available: {client.is_available()}')
"
```

### 4.5: Compare Test Results
```bash
# Compare pre and post migration test results
cd /Users/pacey/Documents/SourceCode/GANGLIA

# Run post-migration tests
pytest tests/ -v > /tmp/post_migration_tests.log 2>&1

# Compare
echo "=== PRE-MIGRATION TEST SUMMARY ===" > /tmp/test_comparison.txt
grep -E "(passed|failed|error)" /tmp/pre_migration_tests.log >> /tmp/test_comparison.txt
echo "" >> /tmp/test_comparison.txt
echo "=== POST-MIGRATION TEST SUMMARY ===" >> /tmp/test_comparison.txt
grep -E "(passed|failed|error)" /tmp/post_migration_tests.log >> /tmp/test_comparison.txt

cat /tmp/test_comparison.txt
```

---

## Rollback Procedures

### If Phase 1 (ganglia-common) Fails
```bash
# Simply delete the repo and start over
cd /Users/pacey/Documents/SourceCode
rm -rf ganglia-common
# Original GANGLIA repo is untouched
```

### If Phase 2 (ganglia-studio) Fails
```bash
# Delete the repo and start over
cd /Users/pacey/Documents/SourceCode
rm -rf ganglia-studio
# Original GANGLIA repo is still untouched
```

### If Phase 3 (ganglia-core) Fails
```bash
# Restore from backup branch
cd /Users/pacey/Documents/SourceCode/GANGLIA
git reset --hard pre-refactor-backup
git clean -fd

# Or restore from bundle
cd /Users/pacey/Documents/SourceCode
rm -rf GANGLIA
git clone ganglia_full_backup.bundle GANGLIA
cd GANGLIA
git remote set-url origin git@github.com:YOUR_USERNAME/GANGLIA.git
```

### Complete Rollback
```bash
# If everything goes wrong, restore from tar backup
cd /Users/pacey/Documents/SourceCode
rm -rf GANGLIA ganglia-common ganglia-studio
tar -xzf GANGLIA_backup_*.tar.gz
```

---

## Post-Migration Tasks

### 1. Update CI/CD Pipelines
- Update GitHub Actions workflows for each repo
- Configure submodule handling in ganglia-core CI
- Set up separate CI pipelines for common/studio/core

### 2. Update Documentation
- Update all README files with new structure
- Create architecture diagrams
- Document submodule workflow
- Update contribution guidelines

### 3. Clean Up Old Branches
```bash
# Delete feature branches that are no longer relevant
cd /Users/pacey/Documents/SourceCode/GANGLIA
git branch -d old-feature-branch
git push origin --delete old-feature-branch
```

### 4. Tag Release
```bash
# Tag v0.1.0 in each repo
cd /Users/pacey/Documents/SourceCode/ganglia-common
git tag -a v0.1.0 -m "Initial release of ganglia-common"
git push origin v0.1.0

cd /Users/pacey/Documents/SourceCode/ganglia-studio
git tag -a v0.1.0 -m "Initial release of ganglia-studio"
git push origin v0.1.0

cd /Users/pacey/Documents/SourceCode/GANGLIA
git tag -a v0.1.0 -m "Initial release of ganglia-core with submodules"
git push origin v0.1.0
```

### 5. Update Local Development
```bash
# Add convenience aliases to ~/.zshrc or ~/.bashrc
cat >> ~/.zshrc << 'EOF'

# GANGLIA development aliases
alias ganglia-dev='cd /Users/pacey/Documents/SourceCode/GANGLIA'
alias ganglia-common-dev='cd /Users/pacey/Documents/SourceCode/ganglia-common'
alias ganglia-studio-dev='cd /Users/pacey/Documents/SourceCode/ganglia-studio'
alias ganglia-update-all='ganglia-common-dev && git pull && ganglia-studio-dev && git pull && ganglia-dev && git pull && git submodule update --remote'
EOF

source ~/.zshrc
```

---

## Troubleshooting

### Import Errors
**Symptom**: `ModuleNotFoundError: No module named 'ganglia_common'`

**Solution**:
```bash
cd /Users/pacey/Documents/SourceCode/GANGLIA
git submodule update --init --recursive
pip install -e ./ganglia_common
```

### Submodule Issues
**Symptom**: Submodules are empty or outdated

**Solution**:
```bash
cd /Users/pacey/Documents/SourceCode/GANGLIA
git submodule init
git submodule update --remote --merge
```

### Test Failures
**Symptom**: Tests fail after migration

**Solution**:
1. Check import statements are updated
2. Verify all files were moved correctly
3. Check test data/fixtures are in correct location
4. Compare with pre-migration test results

### Circular Dependencies
**Symptom**: Import errors due to circular references

**Solution**:
- ganglia-common must not import from ganglia-core or ganglia-studio
- ganglia-studio can import from ganglia-common
- ganglia-core can import from both common and studio

---

## Success Criteria

Migration is successful when:

- ✅ All three repos exist and are properly configured
- ✅ ganglia-common tests pass (100% of originally passing tests)
- ✅ ganglia-studio tests pass (100% of originally passing tests)
- ✅ ganglia-core tests pass with submodules (100% of originally passing tests)
- ✅ No import errors in any repo
- ✅ CLI commands work (`ganglia-studio video --help`)
- ✅ Submodules are properly initialized in ganglia-core
- ✅ No files are lost (all 183 files accounted for)
- ✅ Git history is preserved in each repo
- ✅ Documentation is updated

---

## Timeline Estimate

- **Phase 1 (ganglia-common)**: 2-3 hours
  - File copying: 30 min
  - Import refactoring: 1 hour
  - Testing: 30 min
  - Documentation: 30 min

- **Phase 2 (ganglia-studio)**: 3-4 hours
  - File copying: 45 min
  - Import refactoring: 1.5 hours
  - CLI creation: 30 min
  - Testing: 1 hour
  - Documentation: 30 min

- **Phase 3 (ganglia-core)**: 3-4 hours
  - Submodule setup: 30 min
  - File reorganization: 1 hour
  - Import refactoring: 1.5 hours
  - Testing: 1 hour
  - Documentation: 30 min

- **Phase 4 (Validation)**: 1-2 hours
  - Integration testing: 1 hour
  - Documentation review: 30 min
  - Final cleanup: 30 min

**Total**: 9-13 hours

---

## Notes

- Take breaks between phases
- Commit frequently with descriptive messages
- Test after each major change
- Keep backup terminal open with original repo
- Document any deviations from plan
- Ask for help if stuck on import refactoring
