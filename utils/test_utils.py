"""Test utilities for managing test execution and log monitoring."""

import os
import glob
from datetime import datetime
from typing import Optional

def get_most_recent_test_logs(test_type: Optional[str] = None) -> str:
    """Get the path to the most recent test log file.
    
    Args:
        test_type: Optional test type ('unit', 'smoke', 'integration'). 
                  If None, returns most recent of any type.
    
    Returns:
        str: Path to the most recent log file
        
    Raises:
        FileNotFoundError: If no matching log files are found
    """
    # Construct glob pattern based on test type
    if test_type:
        pattern = f"logs/test_run_*_{test_type}_*.log"
    else:
        pattern = "logs/test_run_*.log"
    
    # Get all matching log files
    log_files = glob.glob(pattern)
    if not log_files:
        raise FileNotFoundError(f"No log files found matching pattern: {pattern}")
    
    # Return the most recent file by creation time
    return max(log_files, key=os.path.getctime)

def parse_test_log_timestamp(log_file: str) -> datetime:
    """Parse the timestamp from a test log filename.
    
    Args:
        log_file: Path to the log file
        
    Returns:
        datetime: The timestamp from the filename
        
    Raises:
        ValueError: If timestamp cannot be parsed from filename
    """
    try:
        # Extract timestamp from filename (format: test_run_MODE_TYPE_YYYY-MM-DD-HH-MM-SS.log)
        filename = os.path.basename(log_file)
        timestamp_str = filename.split('_')[-1].replace('.log', '')
        return datetime.strptime(timestamp_str, '%Y-%m-%d-%H-%M-%S')
    except (IndexError, ValueError) as e:
        raise ValueError(f"Could not parse timestamp from log file: {log_file}") from e

def get_test_status(log_file: str) -> Optional[int]:
    """Get the exit code status from a test run.
    
    Args:
        log_file: Path to the log file
        
    Returns:
        Optional[int]: The exit code if found, None otherwise
    """
    # Get timestamp from log filename
    timestamp = parse_test_log_timestamp(log_file)
    timestamp_str = timestamp.strftime('%Y-%m-%d-%H-%M-%S')
    
    # Check corresponding status file
    status_files = {
        'unit': f'/tmp/GANGLIA/test_status_{timestamp_str}.txt',
        'smoke': f'/tmp/GANGLIA/smoke_status_{timestamp_str}.txt',
        'integration': f'/tmp/GANGLIA/integration_status_{timestamp_str}.txt'
    }
    
    # Try each possible status file
    for status_file in status_files.values():
        if os.path.exists(status_file):
            try:
                with open(status_file, 'r', encoding='utf-8') as f:
                    return int(f.read().strip())
            except (ValueError, IOError):
                continue
    
    return None 