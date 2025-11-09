# GANGLIA Repository Migration Map

This document maps every file in the current GANGLIA repository to its destination in the new three-repository structure.

## Legend
- ✅ MOVE - File moves to new location
- 🔄 REFACTOR - File moves and requires significant refactoring
- 📋 COPY - File duplicates to multiple repos
- 🗑️ DELETE - File should be removed
- 📝 KEEP - File stays in ganglia with same/similar location

## Repository Structure Overview

```
ganglia-core/              (Main chatbot repo)
├── ganglia_common/        (Submodule: shared utilities)
└── ganglia_studio/        (Submodule: multimedia generation)
```

**Future expansion possibilities**: ganglia-web, ganglia-analytics, ganglia-cloud, etc.

---

## GANGLIA-COMMON (New Shared Library Repo)

### Core Utilities
| Current Path | New Path | Action | Notes |
|-------------|----------|--------|-------|
| `logger.py` | `src/ganglia_common/logger.py` | ✅ MOVE | Core logging used everywhere |
| `query_dispatch.py` | `src/ganglia_common/query_dispatch.py` | ✅ MOVE | OpenAI API interface |
| `tts.py` | `src/ganglia_common/tts/google_tts.py` | 🔄 REFACTOR | Rename class, update imports |
| `tts_openai.py` | `src/ganglia_common/tts/openai_tts.py` | 🔄 REFACTOR | Rename class, update imports |
| `pubsub/__init__.py` | `src/ganglia_common/pubsub/__init__.py` | ✅ MOVE | Event system |
| `pubsub/pubsub.py` | `src/ganglia_common/pubsub/pubsub.py` | ✅ MOVE | Event system |
| `utils/__init__.py` | `src/ganglia_common/utils/__init__.py` | ✅ MOVE | Shared utilities |
| `utils/file_utils.py` | `src/ganglia_common/utils/file_utils.py` | ✅ MOVE | File operations |
| `utils/performance_profiler.py` | `src/ganglia_common/utils/performance_profiler.py` | ✅ MOVE | Performance tracking |
| `utils/retry_utils.py` | `src/ganglia_common/utils/retry_utils.py` | ✅ MOVE | Retry logic |
| `utils/cloud_utils.py` | `src/ganglia_common/utils/cloud_utils.py` | ✅ MOVE | Cloud storage operations |

### Configuration & Setup
| Current Path | New Path | Action | Notes |
|-------------|----------|--------|-------|
| N/A | `setup.py` | ✅ CREATE | Make package installable |
| N/A | `pyproject.toml` | ✅ CREATE | Modern Python packaging |
| N/A | `requirements.txt` | ✅ CREATE | Core dependencies only |
| N/A | `README.md` | ✅ CREATE | Library documentation |

### Tests
| Current Path | New Path | Action | Notes |
|-------------|----------|--------|-------|
| `tests/unit/test_query_dispatch.py` | `tests/unit/test_query_dispatch.py` | ✅ MOVE | Query dispatch tests |
| `tests/unit/test_send_query.py` | `tests/unit/test_send_query.py` | ✅ MOVE | Query sending tests |
| `tests/unit/test_pubsub.py` | `tests/unit/test_pubsub.py` | ✅ MOVE | PubSub tests |
| `tests/unit/test_utils.py` | `tests/unit/test_utils.py` | ✅ MOVE | Utility tests |

---

## GANGLIA-STUDIO (New Multimedia Generation Repo)

### Video Pipeline Core
| Current Path | New Path | Action | Notes |
|-------------|----------|--------|-------|
| `ttv/__init__.py` | `src/ganglia_studio/__init__.py` | ✅ MOVE | Package init |
| `ttv/ttv.py` | `src/ganglia_studio/video/pipeline.py` | 🔄 REFACTOR | Main video pipeline |
| `ttv/audio_alignment.py` | `src/ganglia_studio/video/audio_alignment.py` | ✅ MOVE | Audio sync |
| `ttv/audio_generation.py` | `src/ganglia_studio/video/audio_generation.py` | ✅ MOVE | Audio creation |
| `ttv/captions.py` | `src/ganglia_studio/video/captions.py` | ✅ MOVE | Caption generation |
| `ttv/caption_roi.py` | `src/ganglia_studio/video/caption_roi.py` | ✅ MOVE | Caption positioning |
| `ttv/color_utils.py` | `src/ganglia_studio/video/color_utils.py` | ✅ MOVE | Color calculations |
| `ttv/config_loader.py` | `src/ganglia_studio/config/loader.py` | 🔄 REFACTOR | Config loading |
| `ttv/ffmpeg_constants.py` | `src/ganglia_studio/video/ffmpeg_constants.py` | ✅ MOVE | FFmpeg constants |
| `ttv/final_video_generation.py` | `src/ganglia_studio/video/final_assembly.py` | 🔄 REFACTOR | Video assembly |
| `ttv/image_generation.py` | `src/ganglia_studio/image/generation.py` | ✅ MOVE | Image generation |
| `ttv/log_messages.py` | `src/ganglia_studio/video/log_messages.py` | ✅ MOVE | Video-specific logging |
| `ttv/story_generation.py` | `src/ganglia_studio/story/generation.py` | 🔄 REFACTOR | Story generation |
| `ttv/story_processor.py` | `src/ganglia_studio/story/processor.py` | 🔄 REFACTOR | Story processing |
| `ttv/video_generation.py` | `src/ganglia_studio/video/video_generation.py` | ✅ MOVE | Video segment creation |

### Story & Music
| Current Path | New Path | Action | Notes |
|-------------|----------|--------|-------|
| `story_generation_driver.py` | `src/ganglia_studio/story/driver.py` | 🔄 REFACTOR | Story state machine |
| `music_lib.py` | `src/ganglia_studio/music/library.py` | 🔄 REFACTOR | Music generation |
| `lyrics_lib.py` | `src/ganglia_studio/music/lyrics.py` | 🔄 REFACTOR | Lyrics generation |
| `music_backends/__init__.py` | `src/ganglia_studio/music/backends/__init__.py` | ✅ MOVE | Music backend package |
| `music_backends/base.py` | `src/ganglia_studio/music/backends/base.py` | ✅ MOVE | Base backend interface |
| `music_backends/foxai_suno.py` | `src/ganglia_studio/music/backends/foxai_suno.py` | ✅ MOVE | FoxAI Suno backend |
| `music_backends/gcui_suno.py` | `src/ganglia_studio/music/backends/gcui_suno.py` | ✅ MOVE | GCUI Suno backend |
| `music_backends/meta.py` | `src/ganglia_studio/music/backends/meta.py` | ✅ MOVE | Meta MusicGen backend |
| `music_backends/suno_api_org.py` | `src/ganglia_studio/music/backends/suno_api_org.py` | ✅ MOVE | Suno API org backend |
| `music_backends/suno_interface.py` | `src/ganglia_studio/music/backends/suno_interface.py` | ✅ MOVE | Suno interface |
| `suno_request_handler.py` | `src/ganglia_studio/music/request_handler.py` | 🔄 REFACTOR | Suno request handling |

### Configuration & Setup
| Current Path | New Path | Action | Notes |
|-------------|----------|--------|-------|
| `config/ttv_config.json` | `config/ttv_config.json` | ✅ MOVE | TTV config example |
| `config/ttv_config.template.json` | `config/ttv_config.template.json` | ✅ MOVE | TTV config template |
| `config_backups/ttv_config.json` | N/A | 🗑️ DELETE | Old backup |
| N/A | `src/ganglia_studio/cli.py` | ✅ CREATE | CLI interface (ganglia-studio video/music/image) |
| N/A | `setup.py` | ✅ CREATE | Make package installable |
| N/A | `pyproject.toml` | ✅ CREATE | Modern Python packaging |
| `requirements_large.txt` | `requirements.txt` | 🔄 REFACTOR | Heavy dependencies + ganglia_common |
| N/A | `README.md` | ✅ CREATE | Multimedia studio documentation |

### Utils (Studio-specific)
| Current Path | New Path | Action | Notes |
|-------------|----------|--------|-------|
| `utils/ffmpeg_utils.py` | `src/ganglia_studio/utils/ffmpeg_utils.py` | ✅ MOVE | FFmpeg operations |
| `utils/video_utils.py` | `src/ganglia_studio/utils/video_utils.py` | ✅ MOVE | Video utilities |

### Tests
| Current Path | New Path | Action | Notes |
|-------------|----------|--------|-------|
| `tests/unit/test_music_lib.py` | `tests/unit/music/test_library.py` | 🔄 REFACTOR | Music lib tests |
| `tests/unit/test_suno_api_org.py` | `tests/unit/music/test_suno_api_org.py` | ✅ MOVE | Suno tests |
| `tests/unit/ttv/` | `tests/unit/video/` | 🔄 REFACTOR | All TTV unit tests |
| `tests/unit/ttv/conftest.py` | `tests/unit/conftest.py` | ✅ MOVE | Test fixtures |
| `tests/unit/ttv/test_audio_alignment.py` | `tests/unit/video/test_audio_alignment.py` | ✅ MOVE | Audio alignment tests |
| `tests/unit/ttv/test_caption_roi.py` | `tests/unit/video/test_caption_roi.py` | ✅ MOVE | Caption ROI tests |
| `tests/unit/ttv/test_captions.py` | `tests/unit/video/test_captions.py` | ✅ MOVE | Caption tests |
| `tests/unit/ttv/test_config_loader.py` | `tests/unit/config/test_loader.py` | 🔄 REFACTOR | Config loader tests |
| `tests/unit/ttv/test_generate_poster.py` | `tests/unit/video/test_generate_poster.py` | ✅ MOVE | Poster generation tests |
| `tests/unit/ttv/test_story_generation.py` | `tests/unit/story_generation/test_generation.py` | 🔄 REFACTOR | Story gen tests |
| `tests/unit/ttv/test_story_processor.py` | `tests/unit/story_generation/test_processor.py` | 🔄 REFACTOR | Story processor tests |
| `tests/unit/ttv/test_data/` | `tests/fixtures/` | 🔄 REFACTOR | Test data/fixtures |
| `tests/integration/test_generated_ttv_pipeline.py` | `tests/integration/test_full_pipeline.py` | 🔄 REFACTOR | Full pipeline test |
| `tests/integration/test_minimal_ttv_config.py` | `tests/integration/test_minimal_config.py` | 🔄 REFACTOR | Minimal config test |
| `tests/integration/test_ttv_conversation.py` | `tests/integration/test_conversation_flow.py` | 🔄 REFACTOR | Conversation flow test |
| `tests/integration/test_data/` | `tests/fixtures/` | 🔄 REFACTOR | Integration test data |
| `tests/smoke/test_simulated_ttv_pipeline.py` | `tests/smoke/test_pipeline.py` | 🔄 REFACTOR | Smoke test |
| `tests/third_party/test_dalle_api_live.py` | `tests/integration/third_party/test_dalle_live.py` | 🔄 REFACTOR | DALL-E integration |
| `tests/third_party/test_foxai_suno_live.py` | `tests/integration/third_party/test_foxai_suno_live.py` | ✅ MOVE | FoxAI Suno test |
| `tests/third_party/test_gcui_suno_live.py` | `tests/integration/third_party/test_gcui_suno_live.py` | ✅ MOVE | GCUI Suno test |
| `tests/third_party/test_generate_lyrics.py` | `tests/integration/third_party/test_generate_lyrics.py` | ✅ MOVE | Lyrics generation test |
| `tests/third_party/test_meta_musicgen.py` | `tests/integration/third_party/test_meta_musicgen.py` | ✅ MOVE | MusicGen test |
| `tests/third_party/test_suno_api_org_live.py` | `tests/integration/third_party/test_suno_api_org_live.py` | ✅ MOVE | Suno API test |

---

## GANGLIA-CORE (Main Chatbot Repo)

### Core Application
| Current Path | New Path | Action | Notes |
|-------------|----------|--------|-------|
| `ganglia.py` | `src/ganglia_core/main.py` | 🔄 REFACTOR | Main entry point, import updates |
| `conversational_interface.py` | `src/ganglia_core/core/conversation.py` | 🔄 REFACTOR | Conversation management |
| `conversation_context.py` | `src/ganglia_core/core/context.py` | 🔄 REFACTOR | Context management |
| `session_logger.py` | `src/ganglia_core/core/session_logger.py` | 🔄 REFACTOR | Session logging |
| `audio_turn_indicator.py` | `src/ganglia_core/audio/turn_indicators.py` | 🔄 REFACTOR | Audio turn indicators |
| `parse_inputs.py` | `src/ganglia_core/config/parser.py` | 🔄 REFACTOR | Config parsing |

### Input Systems
| Current Path | New Path | Action | Notes |
|-------------|----------|--------|-------|
| `dictation/__init__.py` | `src/ganglia_core/input/__init__.py` | ✅ MOVE | Package init |
| `dictation/dictation.py` | `src/ganglia_core/input/dictation.py` | ✅ MOVE | Base dictation |
| `dictation/live_google_dictation.py` | `src/ganglia_core/input/live_google_dictation.py` | ✅ MOVE | Live Google STT |
| `dictation/static_google_dictation.py` | `src/ganglia_core/input/static_google_dictation.py` | ✅ MOVE | Static Google STT |
| `dictation/stt_provider.py` | `src/ganglia_core/input/stt_provider.py` | ✅ MOVE | STT provider interface |
| `dictation/vad_dictation.py` | `src/ganglia_core/input/vad_dictation.py` | ✅ MOVE | VAD-based dictation |
| `dictation/wake_word_dictation.py` | `src/ganglia_core/input/wake_word_dictation.py` | ✅ MOVE | Wake word detection |
| `hotwords.py` | `src/ganglia_core/input/hotwords.py` | 🔄 REFACTOR | Hotword management |

### Integrations
| Current Path | New Path | Action | Notes |
|-------------|----------|--------|-------|
| N/A | `src/ganglia_core/integrations/studio_client.py` | ✅ CREATE | Optional studio integration |
| `social_media/__init__.py` | `src/ganglia_core/integrations/social_media/__init__.py` | ✅ MOVE | Social media package |
| `social_media/youtube_client.py` | `src/ganglia_core/integrations/social_media/youtube_client.py` | ✅ MOVE | YouTube integration |

### User Management
| Current Path | New Path | Action | Notes |
|-------------|----------|--------|-------|
| `user_management/` | `src/ganglia_core/user_management/` | ✅ MOVE | User management (if exists) |

### Configuration
| Current Path | New Path | Action | Notes |
|-------------|----------|--------|-------|
| `config/ganglia_config.json` | `config/ganglia_config.json` | 📝 KEEP | Chatbot config |
| `config/ganglia_config.json.template` | `config/ganglia_config.json.template` | 📝 KEEP | Config template |
| `config/vad_config.json` | `config/vad_config.json` | 📝 KEEP | VAD config |
| `config/vad_config.json.template` | `config/vad_config.json.template` | 📝 KEEP | VAD template |
| `config_backups/taylors_9_28_2024_ganglia_config.json` | N/A | 🗑️ DELETE | Old backup |

### Media Assets
| Current Path | New Path | Action | Notes |
|-------------|----------|--------|-------|
| `media/zapsplat_multimedia_button_click_bright_001_92098.mp3` | `media/button_click_bright.mp3` | 🔄 REFACTOR | Rename for clarity |
| `media/zapsplat_multimedia_button_click_fast_short_004_79288.mp3` | `media/button_click_fast.mp3` | 🔄 REFACTOR | Rename for clarity |
| `media/zapsplat_multimedia_ui_window_maximize_short_swipe_whoosh_001_71500.mp3` | `media/window_maximize.mp3` | 🔄 REFACTOR | Rename for clarity |
| `media/zapsplat_multimedia_ui_window_minimize_short_swipe_whoosh_71502.mp3` | `media/window_minimize.mp3` | 🔄 REFACTOR | Rename for clarity |

### Scripts & Tools
| Current Path | New Path | Action | Notes |
|-------------|----------|--------|-------|
| `fetch_and_display_logs.py` | `scripts/fetch_and_display_logs.py` | ✅ MOVE | Log viewer |
| `ganglia_watchdog.sh` | `scripts/ganglia_watchdog.sh` | ✅ MOVE | Watchdog script |
| `start_ganglia_monitored.sh` | `scripts/start_ganglia_monitored.sh` | ✅ MOVE | Monitored start script |
| `run_tests.sh` | `scripts/run_tests.sh` | ✅ MOVE | Test runner |
| `prep_env.sh` | `scripts/prep_env.sh` | ✅ MOVE | Environment prep |
| `tools/generate_audio_from_text.py` | `scripts/tools/generate_audio_from_text.py` | ✅ MOVE | Audio generation tool |
| `tools/minify_repo.py` | `scripts/tools/minify_repo.py` | ✅ MOVE | Repo minifier |
| `utils/monitor_tests.sh` | `scripts/monitor_tests.sh` | ✅ MOVE | Test monitor |
| `utils/test_conversation_latency.py` | `scripts/test_conversation_latency.py` | ✅ MOVE | Latency tester |
| `utils/test_utils.py` | `tests/test_utils.py` | ✅ MOVE | Test utilities |
| `utils/test_vad_sensitivity.py` | `scripts/test_vad_sensitivity.py` | ✅ MOVE | VAD sensitivity tester |
| `utils/vad_energy_analyzer.py` | `scripts/vad_energy_analyzer.py` | ✅ MOVE | VAD energy analyzer |

### Documentation
| Current Path | New Path | Action | Notes |
|-------------|----------|--------|-------|
| `README.md` | `README.md` | 🔄 REFACTOR | Update for new structure |
| `STATUS.md` | `STATUS.md` | 📝 KEEP | Current status |
| `todo.md` | `todo.md` | 📝 KEEP | Todo list |
| `AUDIO_PROCESS_HANGING_ANALYSIS.md` | `docs/AUDIO_PROCESS_HANGING_ANALYSIS.md` | ✅ MOVE | Analysis doc |
| `GANGLIA_2025_SETUP.md` | `docs/GANGLIA_2025_SETUP.md` | ✅ MOVE | Setup guide |
| `GANGLIA_2025_SUMMARY.md` | `docs/GANGLIA_2025_SUMMARY.md` | ✅ MOVE | Summary doc |
| `GANGLIA_SERVICE_SETUP.md` | `docs/GANGLIA_SERVICE_SETUP.md` | ✅ MOVE | Service setup |
| `GANGLIA_TTS_MODERNIZATION_PLAN.md` | `docs/GANGLIA_TTS_MODERNIZATION_PLAN.md` | ✅ MOVE | TTS modernization |
| `TIMING_ANALYSIS_GUIDE.md` | `docs/TIMING_ANALYSIS_GUIDE.md` | ✅ MOVE | Timing analysis |
| `docs/archive/` | `docs/archive/` | 📝 KEEP | Archived docs |

### Deployment
| Current Path | New Path | Action | Notes |
|-------------|----------|--------|-------|
| `deployment/ganglia.desktop` | `deployment/ganglia.desktop` | 📝 KEEP | Desktop entry |
| `Dockerfile` | `Dockerfile` | 🔄 REFACTOR | Update for new structure |

### Project Configuration
| Current Path | New Path | Action | Notes |
|-------------|----------|--------|-------|
| `requirements.txt` | `requirements.txt` | 🔄 REFACTOR | Include ganglia_common submodule |
| `requirements_core.txt` | `requirements_core.txt` | 🔄 REFACTOR | Core dependencies only |
| `requirements_test.txt` | `requirements_test.txt` | 📝 KEEP | Test dependencies |
| `pytest.ini` | `pytest.ini` | 🔄 REFACTOR | Update for new structure |
| N/A | `setup.py` | ✅ CREATE | Make package installable |
| N/A | `pyproject.toml` | ✅ CREATE | Modern Python packaging |
| N/A | `.gitmodules` | ✅ CREATE | Submodule configuration (ganglia_common, ganglia_studio) |

### Tests
| Current Path | New Path | Action | Notes |
|-------------|----------|--------|-------|
| `tests/__init__.py` | `tests/__init__.py` | 📝 KEEP | Test package init |
| `tests/README.md` | `tests/README.md` | 🔄 REFACTOR | Update test docs |
| `tests/conftest.py` | `tests/conftest.py` | 🔄 REFACTOR | Update fixtures |
| `tests/test_helpers.py` | `tests/test_helpers.py` | 🔄 REFACTOR | Test helpers |
| `tests/unit/test_audio_inputs.py` | `tests/unit/input/test_audio_inputs.py` | 🔄 REFACTOR | Audio input tests |
| `tests/unit/test_config_generator.py` | N/A | 🗑️ DELETE | Studio-specific, moved to studio repo |
| `tests/unit/test_conversation_ttv_integration.py` | `tests/unit/integrations/test_studio_integration.py` | 🔄 REFACTOR | Mock studio integration test |
| `tests/unit/test_ffmpeg_thread_manager.py` | N/A | 🗑️ DELETE | Studio-specific, moved to studio repo |
| `tests/unit/test_hotword_manager.py` | `tests/unit/input/test_hotwords.py` | 🔄 REFACTOR | Hotword tests |
| `tests/unit/test_parse_inputs.py` | `tests/unit/config/test_parser.py` | 🔄 REFACTOR | Config parser tests |
| `tests/unit/test_session_logger.py` | `tests/unit/core/test_session_logger.py` | 🔄 REFACTOR | Session logger tests |
| `tests/unit/test_story_generation_driver.py` | N/A | 🗑️ DELETE | Studio-specific, moved to studio repo |
| `tests/unit/test_vad_dictation.py` | `tests/unit/input/test_vad_dictation.py` | 🔄 REFACTOR | VAD dictation tests |
| `tests/unit/test_vad_stream_timeout.py` | `tests/unit/input/test_vad_stream_timeout.py` | 🔄 REFACTOR | VAD timeout tests |
| `tests/unit/social_media/test_youtube.py` | `tests/unit/integrations/social_media/test_youtube.py` | 🔄 REFACTOR | YouTube tests |
| `tests/third_party/test_audio_input_access.py` | `tests/integration/third_party/test_audio_input_access.py` | 🔄 REFACTOR | Audio input test |
| `tests/third_party/test_youtube_live.py` | `tests/integration/third_party/test_youtube_live.py` | 🔄 REFACTOR | YouTube live test |

### Temporary/Generated Files
| Current Path | New Path | Action | Notes |
|-------------|----------|--------|-------|
| `COMMIT_MSG.txt` | N/A | 🗑️ DELETE | Temporary commit message |
| `recorded_audio.mp3` | N/A | 🗑️ DELETE | Temporary audio file |
| `googleTTSExample.py` | N/A | 🗑️ DELETE | Old example/test file |
| `output/` | N/A | 🗑️ DELETE | Generated output (add to .gitignore) |
| `downloaded_songs/` | N/A | 🗑️ DELETE | Generated content (add to .gitignore) |
| `logs/` | N/A | 🗑️ DELETE | Runtime logs (add to .gitignore) |

### Submodules
| Current Path | New Path | Action | Notes |
|-------------|----------|--------|-------|
| N/A | `ganglia_common/` | ✅ CREATE | Git submodule → ganglia-common repo |
| N/A | `ganglia_studio/` | ✅ CREATE | Git submodule → ganglia-studio repo |

---

## Summary Statistics

### File Counts by Destination

- **ganglia-common**: 15 core files + 4 test files = 19 files
- **ganglia-studio**: 42 source files + 35 test files = 77 files
- **ganglia-core**: 32 source files + 18 test files + 15 docs/scripts = 65 files
- **DELETE**: 8 files (temporary/generated/obsolete)

### Actions Required

- ✅ MOVE: 112 files (direct move, no changes)
- 🔄 REFACTOR: 48 files (move + import updates)
- 📋 COPY: 0 files
- 🗑️ DELETE: 8 files
- ✅ CREATE: 15 new files (setup.py, pyproject.toml, CLI, etc.)

**Total**: 183 files to process

---

## Migration Phases

### Phase 1: Create ganglia-common repo
- Extract shared utilities
- Add packaging (setup.py, pyproject.toml)
- Move common tests
- Verify standalone functionality

### Phase 2: Create ganglia-studio repo
- Extract video pipeline
- Extract music/image/story generation
- Add CLI interface (ganglia-studio video/music/image)
- Move studio tests
- Add packaging
- Reference ganglia-common as dependency

### Phase 3: Refactor ganglia-core repo
- Remove moved files
- Update all imports (ganglia_core package)
- Add ganglia-common and ganglia-studio as submodules
- Update tests to mock studio
- Reorganize into src/ganglia_core/ structure
- Update documentation
- Rename repo: ganglia → ganglia-core

### Phase 4: Validation
- Run all test suites in each repo
- Verify submodule integration in ganglia-core
- Test optional studio client
- Update CI/CD pipelines for all three repos
