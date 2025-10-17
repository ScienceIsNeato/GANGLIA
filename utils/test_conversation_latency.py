#!/usr/bin/env python3
"""Performance test script for measuring conversation pipeline latency.

This script simulates conversation turns to measure and analyze performance
bottlenecks in the speech-to-text, LLM query, and text-to-speech pipeline.
"""

import sys
import os
import time
from typing import List, Dict

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logger import Logger
from query_dispatch import ChatGPTQueryDispatcher
from tts import GoogleTTS
from utils.performance_profiler import get_global_stats, Timer


def test_llm_latency(query_dispatcher: ChatGPTQueryDispatcher, queries: List[str]) -> Dict[str, float]:
    """Test LLM query latency.
    
    Args:
        query_dispatcher: The query dispatcher to test
        queries: List of test queries to send
        
    Returns:
        Dictionary with timing statistics
    """
    Logger.print_info("\n" + "=" * 60)
    Logger.print_info("Testing LLM Latency")
    Logger.print_info("=" * 60)
    
    timings = []
    for i, query in enumerate(queries, 1):
        Logger.print_info(f"\nQuery {i}/{len(queries)}: {query[:50]}...")
        
        with Timer(f"LLM Query {i}", log=True, collect_stats=True):
            response = query_dispatcher.send_query(query)
        
        Logger.print_info(f"Response length: {len(response)} chars")
    
    stats = get_global_stats().get_stats("LLM Query 1")
    return stats


def test_tts_latency(tts: GoogleTTS, texts: List[str]) -> Dict[str, float]:
    """Test TTS generation latency.
    
    Args:
        tts: The TTS interface to test
        texts: List of test texts to synthesize
        
    Returns:
        Dictionary with timing statistics
    """
    Logger.print_info("\n" + "=" * 60)
    Logger.print_info("Testing TTS Latency")
    Logger.print_info("=" * 60)
    
    for i, text in enumerate(texts, 1):
        Logger.print_info(f"\nText {i}/{len(texts)}: {text[:50]}...")
        
        with Timer(f"TTS Generation {i}", log=True, collect_stats=True):
            success, file_path = tts.convert_text_to_speech(text)
        
        if success:
            Logger.print_info(f"Generated: {file_path}")
        else:
            Logger.print_error("TTS generation failed")
    
    stats = get_global_stats().get_stats("TTS Generation 1")
    return stats


def test_end_to_end_latency(query_dispatcher: ChatGPTQueryDispatcher, 
                            tts: GoogleTTS,
                            queries: List[str]) -> Dict[str, float]:
    """Test end-to-end latency (LLM + TTS).
    
    Args:
        query_dispatcher: The query dispatcher to test
        tts: The TTS interface to test
        queries: List of test queries
        
    Returns:
        Dictionary with timing statistics
    """
    Logger.print_info("\n" + "=" * 60)
    Logger.print_info("Testing End-to-End Latency (LLM + TTS)")
    Logger.print_info("=" * 60)
    
    for i, query in enumerate(queries, 1):
        Logger.print_info(f"\nQuery {i}/{len(queries)}: {query[:50]}...")
        
        with Timer(f"End-to-End {i}", log=True, collect_stats=True):
            # LLM Query
            response = query_dispatcher.send_query(query)
            
            # TTS Generation
            success, file_path = tts.convert_text_to_speech(response)
        
        Logger.print_info(f"Response: {len(response)} chars → Audio: {file_path if success else 'FAILED'}")
    
    stats = get_global_stats().get_stats("End-to-End 1")
    return stats


def main():
    """Run performance tests."""
    Logger.print_info("=" * 60)
    Logger.print_info("GANGLIA Performance Test Suite")
    Logger.print_info("=" * 60)
    Logger.print_info("This script measures conversation pipeline latency")
    Logger.print_info("")
    
    # Initialize components
    Logger.print_info("Initializing components...")
    
    try:
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'config',
            'ganglia_config.json'
        )
        query_dispatcher = ChatGPTQueryDispatcher(config_file_path=config_path)
        tts = GoogleTTS()
        Logger.print_info("✓ Components initialized successfully")
    except Exception as e:
        Logger.print_error(f"Failed to initialize components: {e}")
        return 1
    
    # Test queries - mix of short and long responses
    test_queries = [
        "What is 2+2?",
        "Tell me a short joke.",
        "Explain what Halloween is in one sentence.",
        "What's the weather like today?",
        "Give me a brief greeting.",
    ]
    
    # Test texts for TTS - various lengths
    test_texts = [
        "Hello there!",
        "The quick brown fox jumps over the lazy dog.",
        "Happy Halloween! I hope you're having a spooky and fun evening filled with treats and tricks.",
        "Testing text-to-speech generation performance with a medium length sentence.",
        "Short test.",
    ]
    
    # Run tests
    try:
        # Test LLM latency
        llm_stats = test_llm_latency(query_dispatcher, test_queries)
        
        # Test TTS latency
        tts_stats = test_tts_latency(tts, test_texts)
        
        # Test end-to-end latency
        e2e_stats = test_end_to_end_latency(query_dispatcher, tts, test_queries[:3])
        
        # Print summary
        Logger.print_info("\n")
        get_global_stats().print_summary()
        
        # Print analysis
        Logger.print_info("\n" + "=" * 60)
        Logger.print_info("ANALYSIS & RECOMMENDATIONS")
        Logger.print_info("=" * 60)
        
        if llm_stats:
            llm_mean = llm_stats['mean']
            Logger.print_info(f"\nLLM Mean Latency: {llm_mean:.2f}s")
            if llm_mean > 3.0:
                Logger.print_warning("  ⚠ LLM latency is high (>3s). Consider:")
                Logger.print_warning("    - Enabling streaming responses")
                Logger.print_warning("    - Using faster model (if available)")
            else:
                Logger.print_info("  ✓ LLM latency is reasonable")
        
        if tts_stats:
            tts_mean = tts_stats['mean']
            Logger.print_info(f"\nTTS Mean Latency: {tts_mean:.2f}s")
            if tts_mean > 1.0:
                Logger.print_warning("  ⚠ TTS latency is high (>1s). Consider:")
                Logger.print_warning("    - Parallel TTS for multi-sentence responses")
                Logger.print_warning("    - Trying OpenAI TTS API")
            else:
                Logger.print_info("  ✓ TTS latency is good")
        
        if e2e_stats:
            e2e_mean = e2e_stats['mean']
            Logger.print_info(f"\nEnd-to-End Mean Latency: {e2e_mean:.2f}s")
            Logger.print_info(f"  (This is the key roundtrip metric)")
            
            if e2e_mean > 4.0:
                Logger.print_warning("  ⚠ Total roundtrip is slow (>4s)")
                Logger.print_warning("  Quick wins:")
                Logger.print_warning("    1. Enable streaming LLM responses (saves 1-3s)")
                Logger.print_warning("    2. Parallelize TTS generation (saves 0.5-2s)")
                Logger.print_warning("    3. Reduce silence_threshold (saves 0.5-1s)")
            else:
                Logger.print_info("  ✓ Roundtrip latency is acceptable")
        
        Logger.print_info("=" * 60)
        
        return 0
        
    except Exception as e:
        Logger.print_error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

