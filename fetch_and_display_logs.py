import json
import datetime
import subprocess
import os
import tempfile
from blessed import Terminal

term = Terminal()

# ANSI color codes for file output (these will be preserved in the file)
CYAN = '\033[38;5;39m'      # Deep sky blue for user
RED = '\033[38;5;160m'      # Firebrick red for GANGLIA  
GRAY = '\033[90m'           # Gray for conversation breaks
WHITE = '\033[0m'           # Reset to default

def parse_timestamp(timestamp_str):
    """Parse timestamp string into datetime object, handling both formats with and without milliseconds."""
    # Replace periods with colons in the time portion of the timestamp
    timestamp_str = timestamp_str.replace('.', ':')
    try:
        return datetime.datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S.%f")  # Handle milliseconds
    except ValueError:
        return datetime.datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S")  # Fallback to no milliseconds


def fetch_logs_from_gcs(hours):
    """Fetch logs from GCS based on the given time range."""
    logs = []
    current_time = datetime.datetime.now()

    for i in range(1, 5000):  # Loop to get up to 5000 files or until the range is exceeded
        # Get the file list from GCS and download one at a time
        try:
            command = f"gsutil ls -l gs://ganglia_session_logger/ | grep -v 'TOTAL:' | sort -rk 2,2 | head -n {i} | tail -n 1 | awk '{{print $NF}}' | xargs -I {{}} sh -c 'temp_file=$(mktemp); gsutil cp {{}} $temp_file; cat $temp_file; rm $temp_file'"
            log_content = subprocess.check_output(command, shell=True).decode("utf-8")

            log_json = json.loads(log_content)
            conversation_logs = log_json.get("conversation", [])

            # Get timestamp of the first event in this log file
            if not conversation_logs:
                print("No conversation logs found in this file. Skipping.")
                continue
            first_event_timestamp = parse_timestamp(conversation_logs[0]['time_logged'])
            print(f"First event timestamp: {first_event_timestamp}")

            # Calculate the time difference
            time_diff = current_time - first_event_timestamp
            hours_diff = time_diff.total_seconds() / 3600

            # Stop if we've exceeded the time range
            if hours_diff > hours:
                print("Exceeded the specified time range: hours_diff (" + str(hours_diff) + ") > hours (" + str(hours) + ")")
                break

            # Add logs from this file to the result
            logs.extend(conversation_logs)

        except subprocess.CalledProcessError as e:
            print(f"Error fetching logs: {e}")
            continue
        except (ValueError, json.JSONDecodeError):
            print("Invalid log format. Skipping this log.")
            continue

    return logs


def display_logs(hours):
    logs = fetch_logs_from_gcs(hours)

    # Combine and sort the logs based on timestamps
    sorted_logs = sorted(logs, key=lambda x: parse_timestamp(x['time_logged']))

    # Get output file path in GANGLIA temp directory
    from utils.file_utils import get_tempdir
    temp_dir = get_tempdir()
    output_file = os.path.join(temp_dir, 'conversation_logs.txt')
    
    # Write logs to file
    with open(output_file, 'w', encoding='utf-8') as f:
        previous_timestamp = None
        for entry in sorted_logs:
            timestamp = parse_timestamp(entry['time_logged'])
            user_input = entry.get('user_input', '')
            response_output = entry.get('response_output', '')

            # Detect conversation break (more than 5 minutes between events)
            if previous_timestamp and (timestamp - previous_timestamp).total_seconds() > 300:
                f.write(f"\n{GRAY}{'='*80}\n")
                f.write(f"{GRAY}  Conversation Break - {int((timestamp - previous_timestamp).total_seconds() / 60)} minutes\n")
                f.write(f"{GRAY}{'='*80}{WHITE}\n\n")

            # Format timestamp
            time_str = timestamp.strftime('%I:%M:%S %p')
            
            # Write user input (left side, cyan)
            if user_input:
                f.write(f"{CYAN}[{time_str}] You:{WHITE}\n")
                f.write(f"{CYAN}{user_input}{WHITE}\n")
                f.write("\n")  # Empty line for spacing
            
            # Write GANGLIA response (right side visually with indent, red)
            if response_output:
                f.write(f"{RED}             [{time_str}] GANGLIA:{WHITE}\n")
                f.write(f"{RED}             {response_output}{WHITE}\n")
                f.write("\n")  # Empty line for spacing

            previous_timestamp = timestamp
    
    # Print location and cat the file
    print(f"\n{term.green}Conversation logs saved to: {output_file}{term.white}\n")
    subprocess.run(['cat', output_file])
