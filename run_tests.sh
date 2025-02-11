#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Load direnv if available
if command -v direnv >/dev/null 2>&1; then
    eval "$(direnv export bash)"
fi

# Check for required credentials and warn about missing features
echo "Checking available features based on credentials..."

# Google Cloud features
if [ -z "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
    echo "Warning: GOOGLE_APPLICATION_CREDENTIALS not set - Google Cloud Speech/TTS and GCS storage features will not be available"
fi

# YouTube features
if [ -z "$YOUTUBE_CREDENTIALS_FILE" ]; then
    echo "Warning: YOUTUBE_CREDENTIALS_FILE not set - YouTube video upload tests will not be available"
fi

# OpenAI features
if [ -z "$OPENAI_API_KEY" ]; then
    echo "Warning: OPENAI_API_KEY not set - OpenAI GPT and DALL-E features will not be available"
fi

# GCS features
if [ -z "$GCP_BUCKET_NAME" ] || [ -z "$GCP_PROJECT_NAME" ]; then
    echo "Warning: GCP_BUCKET_NAME or GCP_PROJECT_NAME not set - GCS storage features will not be available"
fi

# Music generation features
if [ -z "$SUNO_API_KEY" ]; then
    echo "Warning: SUNO_API_KEY not set - Music generation features will not be available"
fi

echo "Feature check complete"
echo

# Check if we have exactly two arguments
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <mode> <test_type>"
    echo "  mode: 'local' or 'docker'"
    echo "  test_type: 'unit', 'smoke', or 'integration'"
    exit 1
fi

MODE=$1
TEST_TYPE=$2

# Generate timestamp for this test run
TIMESTAMP=$(date +"%Y-%m-%d-%H-%M-%S")

# Create logs directory if it doesn't exist
mkdir -p "${SCRIPT_DIR}/logs"
LOG_FILE="${SCRIPT_DIR}/logs/test_run_${MODE}_${TEST_TYPE}_${TIMESTAMP}.log"

# Create status directory if it doesn't exist
mkdir -p "/tmp/GANGLIA"

# Set status file based on test type
case "$TEST_TYPE" in
    "unit")
        STATUS_FILE="/tmp/GANGLIA/test_status_${TIMESTAMP}.txt"
        ;;
    "smoke")
        STATUS_FILE="/tmp/GANGLIA/smoke_status_${TIMESTAMP}.txt"
        ;;
    "integration")
        STATUS_FILE="/tmp/GANGLIA/integration_status_${TIMESTAMP}.txt"
        ;;
esac

# Validate mode argument
if [[ "$MODE" != "local" && "$MODE" != "docker" ]]; then
    echo "Error: First argument must be either 'local' or 'docker'" | tee -a "$LOG_FILE"
    exit 1
fi

# Validate test type argument and set the appropriate test directory
if [[ "$TEST_TYPE" == "unit" ]]; then
    TEST_DIR="tests/unit/"
elif [[ "$TEST_TYPE" == "smoke" ]]; then
    TEST_DIR="tests/smoke/"
elif [[ "$TEST_TYPE" == "integration" ]]; then
    TEST_DIR="tests/integration/"
else
    echo "Error: Second argument must be either 'unit', 'smoke', or 'integration'" | tee -a "$LOG_FILE"
    exit 1
fi

# Setup Google credentials
if [ -f "/tmp/gcp-credentials.json" ]; then
    echo "[DEBUG] GAC file already exists at /tmp/gcp-credentials.json"
else
    # Ensure parent directory exists
    mkdir -p "/tmp"
    
    # Remove any existing file or directory
    rm -rf "/tmp/gcp-credentials.json"
    touch "/tmp/gcp-credentials.json"
    
    if [ -f "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
        # Local development with file path
        echo "[DEBUG] GAC is a file at $GOOGLE_APPLICATION_CREDENTIALS"
        if [ "$GOOGLE_APPLICATION_CREDENTIALS" != "/tmp/gcp-credentials.json" ]; then
            if ! cp "$GOOGLE_APPLICATION_CREDENTIALS" "/tmp/gcp-credentials.json"; then
                echo "Error: Failed to copy credentials file"
                exit 1
            fi
        fi
    else
        # Treat as JSON content
        echo "[DEBUG] GAC provided as content"
        if ! printf "%s" "$GOOGLE_APPLICATION_CREDENTIALS" > "/tmp/gcp-credentials.json"; then
            echo "Error: Failed to write credentials content"
            exit 1
        fi
    fi
    
    # Verify the file contains valid JSON
    if ! jq empty "/tmp/gcp-credentials.json" 2>/dev/null; then
        echo "Error: Invalid JSON in credentials file"
        exit 1
    fi
fi

# Verify the credentials file exists and is a regular file
if [ ! -f "/tmp/gcp-credentials.json" ]; then
    echo "Error: /tmp/gcp-credentials.json is not a regular file"
    exit 1
fi

# Set restrictive permissions
chmod 600 "/tmp/gcp-credentials.json"

# Setup YouTube credentials
if [ -f "/tmp/youtube_credentials.json" ]; then
    echo "[DEBUG] YouTube credentials file already exists at /tmp/youtube_credentials.json"
    
    # Verify the file contains valid JSON
    if ! jq empty "/tmp/youtube_credentials.json" 2>/dev/null; then
        echo "Error: Invalid JSON in YouTube credentials file"
        exit 1
    fi
else
    # Ensure parent directory exists
    mkdir -p "/tmp"
    
    # Remove any existing file or directory
    rm -rf "/tmp/youtube_credentials.json"
    touch "/tmp/youtube_credentials.json"
    
    # Write credentials content
    echo "[DEBUG] Writing YouTube credentials content"
    if ! printf "%s" "$YOUTUBE_CREDENTIALS_FILE" > "/tmp/youtube_credentials.json"; then
        echo "Error: Failed to write YouTube credentials content"
        exit 1
    fi
    
    # Verify the file contains valid JSON
    if ! jq empty "/tmp/youtube_credentials.json" 2>/dev/null; then
        echo "Error: Invalid JSON in YouTube credentials file"
        exit 1
    fi
fi

# Set restrictive permissions
chmod 600 "/tmp/youtube_credentials.json"

# Setup YouTube token
if [ -f "/tmp/youtube_token.json" ]; then
    echo "[DEBUG] YouTube token file already exists at /tmp/youtube_token.json"
    
    # Verify the file contains valid JSON
    if ! jq empty "/tmp/youtube_token.json" 2>/dev/null; then
        echo "Error: Invalid JSON in YouTube token file"
        exit 1
    fi
else
    echo "Error: YouTube token file not found at /tmp/youtube_token.json"
    exit 1
fi

# Set restrictive permissions
chmod 600 "/tmp/youtube_token.json"

case $MODE in
    "local")
        if [[ "$TEST_TYPE" == "unit" ]]; then
            echo "Executing: python -m pytest ${TEST_DIR} -v -s -m 'not costly'" | tee -a "$LOG_FILE"
            eval "python -m pytest ${TEST_DIR} -v -s -m 'not costly'" 2>&1 | tee -a "$LOG_FILE"
        elif [[ "$TEST_TYPE" == "smoke" ]]; then
            # First run costly unit tests
            echo "Executing costly unit tests before smoke tests..." | tee -a "$LOG_FILE"
            echo "Executing: python -m pytest tests/unit/ -v -s -m 'costly'" | tee -a "$LOG_FILE"
            eval "python -m pytest tests/unit/ -v -s -m 'costly'" 2>&1 | tee -a "$LOG_FILE"
            UNIT_EXIT_CODE=${PIPESTATUS[0]}
            
            if [ $UNIT_EXIT_CODE -ne 0 ]; then
                echo "Costly unit tests failed with exit code $UNIT_EXIT_CODE" | tee -a "$LOG_FILE"
                echo $UNIT_EXIT_CODE > "$STATUS_FILE"
                exit $UNIT_EXIT_CODE
            fi
            
            # Then run smoke tests
            echo "Executing smoke tests..." | tee -a "$LOG_FILE"
            echo "Executing: python -m pytest ${TEST_DIR} -v -s" | tee -a "$LOG_FILE"
            eval "python -m pytest ${TEST_DIR} -v -s" 2>&1 | tee -a "$LOG_FILE"
        else
            echo "Executing: python -m pytest ${TEST_DIR} -v -s" | tee -a "$LOG_FILE"
            eval "python -m pytest ${TEST_DIR} -v -s" 2>&1 | tee -a "$LOG_FILE"
        fi
        TEST_EXIT_CODE=${PIPESTATUS[0]}
        echo $TEST_EXIT_CODE > "$STATUS_FILE"
        exit $TEST_EXIT_CODE
        ;;
    "docker")
        # Build the Docker image
        docker build -t ganglia:latest . 2>&1 | tee -a "$LOG_FILE" || exit 1
        
        # Show the command that will be run
        if [[ "$TEST_TYPE" == "unit" ]]; then
            echo "Command to be run inside Docker: pytest ${TEST_DIR} -v -s -m 'not costly'" | tee -a "$LOG_FILE"
        elif [[ "$TEST_TYPE" == "smoke" ]]; then
            echo "Running costly unit tests before smoke tests in Docker..." | tee -a "$LOG_FILE"
            # Run costly unit tests first
            docker run --rm \
                -v /tmp/gcp-credentials.json:/tmp/gcp-credentials.json \
                -v /tmp/youtube_credentials.json:/tmp/youtube_credentials.json \
                -v /tmp/youtube_token.json:/tmp/youtube_token.json \
                -v "${SCRIPT_DIR}/tests/integration/test_data:/app/tests/integration/test_data" \
                -v "${SCRIPT_DIR}/tests/unit/ttv/test_data:/app/tests/unit/ttv/test_data" \
                -v "/tmp/GANGLIA:/tmp/GANGLIA" \
                -e OPENAI_API_KEY \
                -e GCP_BUCKET_NAME \
                -e GCP_PROJECT_NAME \
                -e SUNO_API_KEY \
                -e GOOGLE_APPLICATION_CREDENTIALS=/tmp/gcp-credentials.json \
                -e YOUTUBE_CREDENTIALS_FILE=/tmp/youtube_credentials.json \
                -e YOUTUBE_TOKEN_FILE=/tmp/youtube_token.json \
                ganglia:latest \
                /bin/sh -c "pytest tests/unit/ -v -s -m 'costly'" 2>&1 | tee -a "$LOG_FILE"
            UNIT_EXIT_CODE=${PIPESTATUS[0]}
            
            if [ $UNIT_EXIT_CODE -ne 0 ]; then
                echo "Costly unit tests failed in Docker with exit code $UNIT_EXIT_CODE" | tee -a "$LOG_FILE"
                echo $UNIT_EXIT_CODE > "$STATUS_FILE"
                rm -f /tmp/gcp-credentials.json /tmp/youtube_credentials.json /tmp/youtube_token.json
                exit $UNIT_EXIT_CODE
            fi
            
            echo "Running smoke tests in Docker..." | tee -a "$LOG_FILE"
        else
            echo "Command to be run inside Docker: pytest ${TEST_DIR} -v -s" | tee -a "$LOG_FILE"
        fi
        
        # Run Docker with credentials mount and pass through environment variables
        docker run --rm \
            -v /tmp/gcp-credentials.json:/tmp/gcp-credentials.json \
            -v /tmp/youtube_credentials.json:/tmp/youtube_credentials.json \
            -v /tmp/youtube_token.json:/tmp/youtube_token.json \
            -v "${SCRIPT_DIR}/tests/integration/test_data:/app/tests/integration/test_data" \
            -v "${SCRIPT_DIR}/tests/unit/ttv/test_data:/app/tests/unit/ttv/test_data" \
            -v "/tmp/GANGLIA:/tmp/GANGLIA" \
            -e OPENAI_API_KEY \
            -e GCP_BUCKET_NAME \
            -e GCP_PROJECT_NAME \
            -e SUNO_API_KEY \
            -e GOOGLE_APPLICATION_CREDENTIALS=/tmp/gcp-credentials.json \
            -e YOUTUBE_CREDENTIALS_FILE=/tmp/youtube_credentials.json \
            -e YOUTUBE_TOKEN_FILE=/tmp/youtube_token.json \
            ganglia:latest \
            /bin/sh -c "pytest ${TEST_DIR} -v -s $([ "$TEST_TYPE" = "unit" ] && echo "-m 'not costly'")" 2>&1 | tee -a "$LOG_FILE"
        TEST_EXIT_CODE=${PIPESTATUS[0]}
        echo $TEST_EXIT_CODE > "$STATUS_FILE"
        rm -f /tmp/gcp-credentials.json /tmp/youtube_credentials.json /tmp/youtube_token.json
        exit $TEST_EXIT_CODE
        ;;
esac 

