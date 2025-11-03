#!/usr/bin/env python3
"""
VAD Energy Analyzer - Diagnostic tool for calibrating energy_threshold

Usage:
    python utils/vad_energy_analyzer.py [--duration 30] [--device-index 0]

This will:
1. Sample ambient noise for specified duration
2. Calculate energy levels for each audio chunk
3. Display real-time energy readings
4. Show statistics and recommend energy_threshold values
"""

import pyaudio
import struct
import math
import argparse
import time
from collections import defaultdict


class EnergyAnalyzer:
    """Analyze audio energy levels to help calibrate VAD threshold."""
    
    # Audio configuration (match vad_dictation.py)
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000
    CHUNK_SIZE = 1024
    
    def __init__(self, duration=30, device_index=None):
        self.duration = duration
        self.device_index = device_index
        self.energy_readings = []
        
    def calculate_energy(self, audio_chunk):
        """Calculate the energy (volume) of an audio chunk."""
        try:
            audio_data = struct.unpack(f'{len(audio_chunk)//2}h', audio_chunk)
            energy = math.sqrt(sum(x**2 for x in audio_data) / len(audio_data))
            return energy
        except Exception:
            return 0
    
    def run_analysis(self):
        """Run the energy analysis for the specified duration."""
        audio = pyaudio.PyAudio()
        
        # List available devices
        print("\n📡 Available Audio Devices:")
        for i in range(audio.get_device_count()):
            info = audio.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:
                print(f"  [{i}] {info['name']}")
        print()
        
        # Open audio stream
        print(f"🎤 Opening audio device {self.device_index if self.device_index else 'default'}...")
        stream = audio.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            input=True,
            input_device_index=self.device_index,
            frames_per_buffer=self.CHUNK_SIZE
        )
        
        print(f"📊 Analyzing ambient noise for {self.duration} seconds...")
        print("   (Try to capture typical background noise levels)")
        print("   Energy readings will appear below:\n")
        
        start_time = time.time()
        chunk_count = 0
        energy_histogram = defaultdict(int)
        
        try:
            while time.time() - start_time < self.duration:
                # Read audio chunk
                chunk = stream.read(self.CHUNK_SIZE, exception_on_overflow=False)
                energy = self.calculate_energy(chunk)
                
                self.energy_readings.append(energy)
                chunk_count += 1
                
                # Update histogram (buckets of 50)
                bucket = int(energy / 50) * 50
                energy_histogram[bucket] += 1
                
                # Display real-time reading every 10 chunks (~0.64s)
                if chunk_count % 10 == 0:
                    elapsed = time.time() - start_time
                    bar = '█' * min(int(energy / 50), 40)
                    print(f"  [{elapsed:5.1f}s] Energy: {energy:7.1f} {bar}", end='\r')
            
            print("\n")  # New line after progress
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Analysis interrupted by user")
        finally:
            stream.close()
            audio.terminate()
        
        # Calculate statistics
        self.display_results(energy_histogram)
    
    def display_results(self, histogram):
        """Display analysis results and recommendations."""
        if not self.energy_readings:
            print("❌ No energy readings collected")
            return
        
        readings = sorted(self.energy_readings)
        n = len(readings)
        
        # Calculate percentiles
        min_energy = readings[0]
        p25 = readings[int(n * 0.25)]
        p50 = readings[int(n * 0.50)]  # median
        p75 = readings[int(n * 0.75)]
        p90 = readings[int(n * 0.90)]
        p95 = readings[int(n * 0.95)]
        p99 = readings[int(n * 0.99)]
        max_energy = readings[-1]
        avg_energy = sum(readings) / n
        
        print("=" * 70)
        print("📊 ENERGY ANALYSIS RESULTS")
        print("=" * 70)
        print(f"\n📈 Statistics from {n} samples:")
        print(f"   Minimum:     {min_energy:7.1f}")
        print(f"   25th pctl:   {p25:7.1f}")
        print(f"   Median:      {p50:7.1f}")
        print(f"   75th pctl:   {p75:7.1f}")
        print(f"   90th pctl:   {p90:7.1f}")
        print(f"   95th pctl:   {p95:7.1f}")
        print(f"   99th pctl:   {p99:7.1f}")
        print(f"   Maximum:     {max_energy:7.1f}")
        print(f"   Average:     {avg_energy:7.1f}")
        
        # Display histogram
        print(f"\n📊 Energy Distribution:")
        max_bucket_count = max(histogram.values()) if histogram else 1
        for bucket in sorted(histogram.keys()):
            count = histogram[bucket]
            bar_width = int((count / max_bucket_count) * 40)
            bar = '█' * bar_width
            percentage = (count / n) * 100
            print(f"   {bucket:4d}-{bucket+49:4d}: {bar:40s} {percentage:5.1f}%")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        print(f"   Current vad_config.json setting: 150")
        print()
        
        # Conservative threshold (above 95th percentile)
        conservative = int(p95 * 1.2)  # 20% above 95th percentile
        print(f"   🟢 Conservative (low false positives): {conservative}")
        print(f"      - Sets threshold above 95th percentile of ambient noise")
        print(f"      - Best if you want to avoid accidental activation")
        
        # Balanced threshold (above 75th percentile)
        balanced = int(p75 * 1.3)  # 30% above 75th percentile
        print(f"   🟡 Balanced (recommended): {balanced}")
        print(f"      - Sets threshold above 75th percentile with margin")
        print(f"      - Good balance between sensitivity and false positives")
        
        # Aggressive threshold (above median)
        aggressive = int(p50 * 1.5)  # 50% above median
        print(f"   🟠 Aggressive (high sensitivity): {aggressive}")
        print(f"      - Sets threshold above median ambient noise")
        print(f"      - Use if you want to catch quiet speech")
        
        print(f"\n📝 To update config:")
        print(f'   Edit config/vad_config.json:')
        print(f'   "detection": {{"energy_threshold": {balanced}}}')
        print()
        
        # Warn if current setting is problematic
        current_threshold = 150
        if current_threshold < p75:
            print(f"   ⚠️  WARNING: Current threshold ({current_threshold}) is below")
            print(f"               75th percentile ({p75:.1f}) of ambient noise!")
            print(f"               This will cause frequent false activations.")
        elif current_threshold < p50:
            print(f"   🚨 CRITICAL: Current threshold ({current_threshold}) is below")
            print(f"                the MEDIAN ({p50:.1f}) ambient noise level!")
            print(f"                System will activate almost constantly.")
        else:
            print(f"   ✅ Current threshold ({current_threshold}) looks reasonable")
        
        print("\n" + "=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description='Analyze audio energy levels to calibrate VAD threshold'
    )
    parser.add_argument(
        '--duration',
        type=int,
        default=30,
        help='Analysis duration in seconds (default: 30)'
    )
    parser.add_argument(
        '--device-index',
        type=int,
        default=None,
        help='Audio input device index (default: system default)'
    )
    
    args = parser.parse_args()
    
    analyzer = EnergyAnalyzer(
        duration=args.duration,
        device_index=args.device_index
    )
    analyzer.run_analysis()


if __name__ == '__main__':
    main()

