#!/usr/bin/env python3
"""
VAD Sensitivity Testing Tool

Use this script to test and tune your Voice Activity Detection settings.
It will show you real-time audio energy levels to help you choose the right threshold.
"""

import pyaudio
import struct
import math
import time
import sys

# Audio configuration (matches VAD settings)
CHUNK_SIZE = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000

def calculate_energy(audio_chunk):
    """Calculate the energy (volume) of an audio chunk."""
    try:
        audio_data = struct.unpack(f'{len(audio_chunk)//2}h', audio_chunk)
        energy = math.sqrt(sum(x**2 for x in audio_data) / len(audio_data))
        return energy
    except Exception:
        return 0

def test_sensitivity(device_index=0, duration_seconds=30):
    """Test microphone and display energy levels."""
    print("=" * 80)
    print("VAD SENSITIVITY TESTING TOOL")
    print("=" * 80)
    print()
    print("This tool will show you real-time audio energy levels.")
    print("Use this information to tune your energy_threshold in config/vad_config.json")
    print()
    print(f"Testing for {duration_seconds} seconds...")
    print("Try different scenarios:")
    print("  1. Stay silent (background noise)")
    print("  2. Speak at normal volume")
    print("  3. Speak quietly")
    print("  4. Speak loudly")
    print()
    print("Recommended thresholds based on your results:")
    print("  - Quiet room: Set threshold ABOVE background noise, BELOW quiet speech")
    print("  - Noisy party: Set threshold ABOVE music/crowd noise, BELOW normal speech")
    print()
    print("-" * 80)
    print()

    # Initialize audio
    audio = pyaudio.PyAudio()

    try:
        stream = audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            input_device_index=device_index,
            frames_per_buffer=CHUNK_SIZE
        )

        print(f"{'Time (s)':<10} {'Energy':<15} {'Visual':<40} {'Status':<20}")
        print("-" * 80)

        start_time = time.time()
        max_energy = 0
        min_energy = float('inf')
        energy_samples = []

        while time.time() - start_time < duration_seconds:
            # Read audio
            chunk = stream.read(CHUNK_SIZE, exception_on_overflow=False)
            energy = calculate_energy(chunk)

            # Track stats
            max_energy = max(max_energy, energy)
            min_energy = min(min_energy, energy)
            energy_samples.append(energy)

            # Visual representation
            bar_length = int(energy / 30)  # Scale for display
            bar = "█" * min(bar_length, 40)

            # Status indicator
            if energy < 300:
                status = "Background noise"
            elif energy < 500:
                status = "Quiet speech?"
            elif energy < 800:
                status = "Normal speech"
            else:
                status = "Loud speech!"

            # Display
            elapsed = time.time() - start_time
            print(f"{elapsed:>8.1f}s  {energy:>12.0f}  {bar:<40} {status:<20}", end='\r')
            sys.stdout.flush()

            time.sleep(0.05)  # Small delay for readability

        print()  # New line after progress
        stream.close()

        # Calculate statistics
        avg_energy = sum(energy_samples) / len(energy_samples)

        print()
        print("=" * 80)
        print("RESULTS & RECOMMENDATIONS")
        print("=" * 80)
        print()
        print(f"Minimum energy detected: {min_energy:.0f}")
        print(f"Maximum energy detected: {max_energy:.0f}")
        print(f"Average energy: {avg_energy:.0f}")
        print()

        # Recommendations
        print("RECOMMENDED SETTINGS for config/vad_config.json:")
        print()

        if max_energy < 400:
            print("⚠️  Very quiet environment detected!")
            print("  energy_threshold: 200-300")
            print("  speech_confirmation_chunks: 2")
        elif max_energy < 600:
            print("✓ Normal environment")
            print(f"  energy_threshold: {int(avg_energy * 1.5)}")
            print("  speech_confirmation_chunks: 3")
        elif max_energy < 1000:
            print("✓ Active environment")
            print(f"  energy_threshold: {int(avg_energy * 1.8)}")
            print("  speech_confirmation_chunks: 3")
        else:
            print("⚠️  Very loud environment!")
            print(f"  energy_threshold: {int(avg_energy * 2.0)}")
            print("  speech_confirmation_chunks: 4")

        print()
        print("TUNING TIPS:")
        print("  - If VAD triggers on background noise: INCREASE energy_threshold")
        print("  - If you need to speak very loudly: DECREASE energy_threshold")
        print("  - If activation is slow: DECREASE speech_confirmation_chunks")
        print("  - If too many false positives: INCREASE speech_confirmation_chunks")
        print()

    except Exception as e:
        print(f"\nError: {e}")
    finally:
        audio.terminate()

def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Test VAD sensitivity and get configuration recommendations"
    )
    parser.add_argument(
        "--device-index",
        type=int,
        default=0,
        help="Audio input device index (default: 0)"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=30,
        help="Test duration in seconds (default: 30)"
    )

    args = parser.parse_args()

    # List available devices
    print("\nAvailable audio devices:")
    audio = pyaudio.PyAudio()
    for i in range(audio.get_device_count()):
        info = audio.get_device_info_by_index(i)
        if info['maxInputChannels'] > 0:
            print(f"  [{i}] {info['name']}")
    audio.terminate()
    print()

    test_sensitivity(args.device_index, args.duration)

if __name__ == "__main__":
    main()
