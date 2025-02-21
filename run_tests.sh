#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Load direnv if available
if command -v direnv >/dev/null 2>&1; then
    eval "$(direnv export bash)"
fi

# Only set the GANGLIA_TEMP_DIR if it's not already set
if [ -z "$GANGLIA_TEMP_DIR" ]; then
    # Get the GANGLIA temp directory in a platform-agnostic way
    GANGLIA_TEMP_DIR=$(python3 -c "import sys; sys.path.append('$SCRIPT_DIR'); from utils.file_utils import get_tempdir; print(get_tempdir())")
    export GANGLIA_TEMP_DIR
fi

# Check for required credentials and warn about missing features
echo "Checking available features based on credentials..."

# Google Cloud features
if [ -z "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
    echo "Warning: GOOGLE_APPLICATION_CREDENTIALS not set - Google Cloud Speech/TTS and GCS storage features will not be available"
fi

# YouTube features
if [ -z "$YOUTUBE_CREDENTIALS_FILE" ] || [ -z "$YOUTUBE_TOKEN_FILE" ]; then
    echo "Warning: YOUTUBE_CREDENTIALS_FILE or YOUTUBE_TOKEN_FILE not set - YouTube video upload tests will not be available"
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
if [ -z "$FOXAI_SUNO_API_KEY" ] || [ -z "$SUNO_API_URL" ] || [ -z "$SUNO_API_ORG_KEY" ]; then
    echo "Warning: FOXAI_SUNO_API_KEY, SUNO_API_URL, or SUNO_API_ORG_KEY not set - Music generation features will not be available"
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

# Create logs directory in the GANGLIA temp directory
mkdir -p "${GANGLIA_TEMP_DIR}/logs"
LOG_FILE="${GANGLIA_TEMP_DIR}/logs/test_run_${MODE}_${TEST_TYPE}_${TIMESTAMP}.log"

# Set status file based on test type
case "$TEST_TYPE" in
    "unit")
        STATUS_FILE="${GANGLIA_TEMP_DIR}/test_status_${TIMESTAMP}.txt"
        ;;
    "smoke")
        STATUS_FILE="${GANGLIA_TEMP_DIR}/smoke_status_${TIMESTAMP}.txt"
        ;;
    "integration")
        STATUS_FILE="${GANGLIA_TEMP_DIR}/integration_status_${TIMESTAMP}.txt"
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
CREDS_DIR="${GANGLIA_TEMP_DIR}/credentials"
mkdir -p "$CREDS_DIR"
GCP_CREDS_FILE="${CREDS_DIR}/gcp-credentials.json"

if [ -f "$GCP_CREDS_FILE" ]; then
    echo "[DEBUG] GAC file already exists at $GCP_CREDS_FILE"
else
    # Remove any existing file or directory
    rm -rf "$GCP_CREDS_FILE"
    touch "$GCP_CREDS_FILE"

    if [ -f "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
        # Local development with file path
        echo "[DEBUG] GAC is a file at $GOOGLE_APPLICATION_CREDENTIALS"
        if [ "$GOOGLE_APPLICATION_CREDENTIALS" != "$GCP_CREDS_FILE" ]; then
            if ! cp "$GOOGLE_APPLICATION_CREDENTIALS" "$GCP_CREDS_FILE"; then
                echo "Error: Failed to copy credentials file"
                exit 1
            fi
        fi
    else
        # Treat as JSON content
        echo "[DEBUG] GAC provided as content"
        if ! printf "%s" "$GOOGLE_APPLICATION_CREDENTIALS" > "$GCP_CREDS_FILE"; then
            echo "Error: Failed to write credentials content"
            exit 1
        fi
    fi

    # Verify the file contains valid JSON
    if ! jq empty "$GCP_CREDS_FILE" 2>/dev/null; then
        echo "Error: Invalid JSON in credentials file"
        exit 1
    fi
fi

# Verify the credentials file exists and is a regular file
if [ ! -f "$GCP_CREDS_FILE" ]; then
    echo "Error: $GCP_CREDS_FILE is not a regular file"
    exit 1
fi

# Set restrictive permissions
chmod 600 "$GCP_CREDS_FILE"

# Setup YouTube credentials
YOUTUBE_CREDS_FILE="${CREDS_DIR}/youtube_credentials.json"
if [ -f "$YOUTUBE_CREDS_FILE" ]; then
    echo "[DEBUG] YouTube credentials file already exists at $YOUTUBE_CREDS_FILE"

    # Clean up any trailing characters
    tr -d '\r\n%' < "$YOUTUBE_CREDS_FILE" > "${YOUTUBE_CREDS_FILE}.tmp" && mv "${YOUTUBE_CREDS_FILE}.tmp" "$YOUTUBE_CREDS_FILE"

    # Verify the file contains valid JSON
    if ! jq empty "$YOUTUBE_CREDS_FILE" 2>/dev/null; then
        echo "Error: Invalid JSON in YouTube credentials file at $YOUTUBE_CREDS_FILE"
        exit 1
    fi
else
    # Remove any existing file or directory
    rm -rf "$YOUTUBE_CREDS_FILE"
    touch "$YOUTUBE_CREDS_FILE"

    # Clean up the credentials file path
    CLEAN_YOUTUBE_CREDS_PATH=$(printf "%s" "$YOUTUBE_CREDENTIALS_FILE" | tr -d '\r\n%')

    # Copy or write credentials content
    if [ -f "$CLEAN_YOUTUBE_CREDS_PATH" ]; then
        # Local development with file path
        echo "[DEBUG] YouTube credentials is a file at $CLEAN_YOUTUBE_CREDS_PATH"
        if [ "$CLEAN_YOUTUBE_CREDS_PATH" != "$YOUTUBE_CREDS_FILE" ]; then
            # Read and clean up the content before writing
            tr -d '\r\n%' < "$CLEAN_YOUTUBE_CREDS_PATH" > "$YOUTUBE_CREDS_FILE"
            if [ $? -ne 0 ]; then
                echo "Error: Failed to copy and clean YouTube credentials from $CLEAN_YOUTUBE_CREDS_PATH"
                exit 1
            fi
        fi
    else
        # Treat as JSON content
        echo "[DEBUG] YouTube credentials provided as content"
        # Clean up any trailing characters before writing
        printf "%s" "$YOUTUBE_CREDENTIALS_FILE" | tr -d '\r\n%' > "$YOUTUBE_CREDS_FILE"
    fi

    # Verify the file contains valid JSON
    if ! jq empty "$YOUTUBE_CREDS_FILE" 2>/dev/null; then
        echo "Error: Invalid JSON in YouTube credentials file at $YOUTUBE_CREDS_FILE"
        echo "Content of file:"
        cat "$YOUTUBE_CREDS_FILE"
        exit 1
    fi
fi

# Set restrictive permissions
chmod 600 "$YOUTUBE_CREDS_FILE"

# Setup YouTube token
YOUTUBE_TOKEN_DEST="${CREDS_DIR}/youtube_token.json"
if [ -f "$YOUTUBE_TOKEN_DEST" ]; then
    echo "[DEBUG] YouTube token file already exists at $YOUTUBE_TOKEN_DEST"

    # Clean up any trailing characters
    tr -d '\r\n%' < "$YOUTUBE_TOKEN_DEST" > "${YOUTUBE_TOKEN_DEST}.tmp" && mv "${YOUTUBE_TOKEN_DEST}.tmp" "$YOUTUBE_TOKEN_DEST"

    # Verify the file contains valid JSON
    if ! jq empty "$YOUTUBE_TOKEN_DEST" 2>/dev/null; then
        echo "Error: Invalid JSON in YouTube token file at $YOUTUBE_TOKEN_DEST"
        echo "Content of file:"
        cat "$YOUTUBE_TOKEN_DEST"
        exit 1
    fi
else
    # Clean up the token file path
    CLEAN_YOUTUBE_TOKEN_PATH=$(printf "%s" "$YOUTUBE_TOKEN_FILE" | tr -d '\r\n%')

    if [ -f "$CLEAN_YOUTUBE_TOKEN_PATH" ]; then
        # Local development with file path
        echo "[DEBUG] YouTube token is a file at $CLEAN_YOUTUBE_TOKEN_PATH"
        # Read and clean up the content before writing
        tr -d '\r\n%' < "$CLEAN_YOUTUBE_TOKEN_PATH" > "$YOUTUBE_TOKEN_DEST"
        if [ $? -ne 0 ]; then
            echo "Error: Failed to copy and clean YouTube token from $CLEAN_YOUTUBE_TOKEN_PATH"
            exit 1
        fi
    else
        echo "Error: YouTube token file not found at $CLEAN_YOUTUBE_TOKEN_PATH"
        exit 1
    fi

    # Verify the file contains valid JSON
    if ! jq empty "$YOUTUBE_TOKEN_DEST" 2>/dev/null; then
        echo "Error: Invalid JSON in YouTube token file at $YOUTUBE_TOKEN_DEST"
        echo "Content of file:"
        cat "$YOUTUBE_TOKEN_DEST"
        exit 1
    fi
fi

# Update YOUTUBE_TOKEN_FILE to point to the copied file
YOUTUBE_TOKEN_FILE="$YOUTUBE_TOKEN_DEST"
export YOUTUBE_TOKEN_FILE

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
                -v "${GCP_CREDS_FILE}:/tmp/gcp-credentials.json" \
                -v "${YOUTUBE_CREDS_FILE}:/tmp/youtube_credentials.json" \
                -v "${YOUTUBE_TOKEN_FILE}:/tmp/youtube_token.json" \
                -v "${SCRIPT_DIR}/tests/integration/test_data:/app/tests/integration/test_data" \
                -v "${SCRIPT_DIR}/tests/unit/ttv/test_data:/app/tests/unit/ttv/test_data" \
                -v "${GANGLIA_TEMP_DIR}:/tmp/GANGLIA" \
                -v "${GANGLIA_TEMP_DIR}/logs:/app/logs" \
                -e OPENAI_API_KEY \
                -e GCP_BUCKET_NAME \
                -e GCP_PROJECT_NAME \
                -e FOXAI_SUNO_API_KEY \
                -e SUNO_API_URL \
                -e SUNO_API_ORG_KEY \
                -e GOOGLE_APPLICATION_CREDENTIALS=/tmp/gcp-credentials.json \
                -e YOUTUBE_CREDENTIALS_FILE=/tmp/youtube_credentials.json \
                -e YOUTUBE_TOKEN_FILE=/tmp/youtube_token.json \
                -e UPLOAD_INTEGRATION_TESTS_TO_YOUTUBE \
                -e UPLOAD_SMOKE_TESTS_TO_YOUTUBE \
                -e "GANGLIA_TEMP_DIR=${GANGLIA_TEMP_DIR}" \
                ganglia:latest \
                /bin/sh -c "pytest tests/unit/ -v -s -m 'costly'" 2>&1 | tee -a "$LOG_FILE"
            UNIT_EXIT_CODE=${PIPESTATUS[0]}

            if [ $UNIT_EXIT_CODE -ne 0 ]; then
                echo "Costly unit tests failed in Docker with exit code $UNIT_EXIT_CODE" | tee -a "$LOG_FILE"
                echo $UNIT_EXIT_CODE > "$STATUS_FILE"
                exit $UNIT_EXIT_CODE
            fi

            echo "Running smoke tests in Docker..." | tee -a "$LOG_FILE"
        else
            echo "Command to be run inside Docker: pytest ${TEST_DIR} -v -s" | tee -a "$LOG_FILE"
        fi

        # Run Docker with credentials mount and pass through environment variables
        docker run --rm \
            -v "${GCP_CREDS_FILE}:/tmp/gcp-credentials.json" \
            -v "${YOUTUBE_CREDS_FILE}:/tmp/youtube_credentials.json" \
            -v "${YOUTUBE_TOKEN_FILE}:/tmp/youtube_token.json" \
            -v "${SCRIPT_DIR}/tests/integration/test_data:/app/tests/integration/test_data" \
            -v "${SCRIPT_DIR}/tests/unit/ttv/test_data:/app/tests/unit/ttv/test_data" \
            -v "${GANGLIA_TEMP_DIR}:/tmp/GANGLIA" \
            -v "${GANGLIA_TEMP_DIR}/logs:/app/logs" \
            -e OPENAI_API_KEY \
            -e GCP_BUCKET_NAME \
            -e GCP_PROJECT_NAME \
            -e FOXAI_SUNO_API_KEY \
            -e SUNO_API_URL \
            -e SUNO_API_ORG_KEY \
            -e GOOGLE_APPLICATION_CREDENTIALS=/tmp/gcp-credentials.json \
            -e YOUTUBE_CREDENTIALS_FILE=/tmp/youtube_credentials.json \
            -e YOUTUBE_TOKEN_FILE=/tmp/youtube_token.json \
            -e UPLOAD_INTEGRATION_TESTS_TO_YOUTUBE \
            -e UPLOAD_SMOKE_TESTS_TO_YOUTUBE \
            -e "GANGLIA_TEMP_DIR=${GANGLIA_TEMP_DIR}" \
            ganglia:latest \
            /bin/sh -c "pytest ${TEST_DIR} -v -s $([ "$TEST_TYPE" = "unit" ] && echo "-m 'not costly'")" 2>&1 | tee -a "$LOG_FILE"
        TEST_EXIT_CODE=${PIPESTATUS[0]}
        echo $TEST_EXIT_CODE > "$STATUS_FILE"
        exit $TEST_EXIT_CODE
        ;;
esac
