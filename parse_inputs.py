import argparse
import json
import os
import sys
from tts import TextToSpeech, GoogleTTS
from dictation.dictation import Dictation
from dictation.static_google_dictation import StaticGoogleDictation
from dictation.live_google_dictation import LiveGoogleDictation
from logger import Logger

def check_environment_variables():
    print("Checking environment variables...")

    required_vars = [
        'OPENAI_API_KEY',
        'GCP_BUCKET_NAME',
        'GCP_PROJECT_NAME',
        'FOXAI_SUNO_API_KEY',
        'GOOGLE_APPLICATION_CREDENTIALS'
    ]

    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        missing = ', '.join(missing_vars)
        sys.stderr.write(f"Error: The following environment variables are missing: {missing}\n")
        sys.exit(1)

def load_coqui_config():
    """
    Load configuration from coqui_config.json.
    Returns a tuple containing (api_url, bearer_token, voice_id) or
    exits the program in case of errors.
    """
    try:
        # Load configuration from coqui_config.json
        with open('coqui_config.json', 'r') as config_file:
            coqui_config = json.load(config_file)

        if "api_url" not in coqui_config or "bearer_token" not in coqui_config or "voice_id" not in coqui_config:
            raise ValueError("Missing one or more required keys in coqui_config.json")

        Logger.print_info("Successfully loaded coqui config")
        return coqui_config["api_url"], coqui_config["bearer_token"], coqui_config["voice_id"]

    except FileNotFoundError:
        Logger.print_error("Error: coqui_config.json file not found in the current directory.", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError:
        Logger.print_error("Error: coqui_config.json file contains invalid JSON.", file=sys.stderr)
        sys.exit(1)
    except ValueError as ve:
        Logger.print_error(f"Error: {ve}", file=sys.stderr)
        sys.exit(1)

def parse_tts_interface(tts_interface: str) -> TextToSpeech:
    if tts_interface.lower() == "google":
        return GoogleTTS()
    else:
        raise ValueError(
            "Invalid TTS interface provided. Available options: 'google'"
        )

def parse_dictation_type(dictation_type: str) -> Dictation:
    if dictation_type.lower() == "static_google":
        return StaticGoogleDictation()
    elif dictation_type.lower() == "live_google":
        return LiveGoogleDictation()
    else:
        raise ValueError(
            "Invalid dictation type provided. Available options: 'static_google'"
        )

def parse_args(args=None):
    parser = argparse.ArgumentParser(description="GANGLIA - AI Assistant")
    parser.add_argument("--device-index", type=int, default=0, help="Index of the input device to use.")
    parser.add_argument("--tts-interface", type=str, default="google", help="Text-to-speech interface to use. Available options: 'google'")
    parser.add_argument("--suppress-session-logging", action="store_true", help="Disable session logging (default: False)")
    parser.add_argument("--enable-turn-indicators", action="store_true", help="Enable turn indicators (default: False)")
    parser.add_argument("--dictation-type", type=str, default="static_google", choices=["static_google", "live_google"], help="Dictation type to use. Available options: 'static_google', 'live_google'")
    parser.add_argument("--store-logs", action="store_true", help="Enable storing logs in the cloud (default: False)")
    parser.add_argument('--text-to-video', action='store_true', help='Generate video from text input.')
    parser.add_argument('--ttv-config', type=str, help='Path to the JSON input file for video generation.')
    parser.add_argument('--skip-image-generation', type=str, help='Use previously generated images when generating text-to-video')
    parser.add_argument('--google-voice-id', type=str, help='Google voice ID to use for TTS')
    parser.add_argument('--display-log-hours', type=int, help="Display the last N hours of logs in transcript format.")
    parser.add_argument('--show-log-errors', action='store_true', help="Display SYSTEM ERROR logs.")

    parsed_args = parser.parse_args(args)

    # Check if --text-to-video is used, then --json-input must also be provided
    if parsed_args.text_to_video and not parsed_args.ttv_config:
        parser.error("--json-input is required when --text-to-video is specified.")

    return parsed_args

def load_config():
    check_environment_variables()

    return parse_args()
