prep_env() {
    # Allow direnv to load environment variables
    if ! direnv allow; then
        echo "Failed to allow direnv. Exiting."
        return 1
    fi

    # Source the .envrc file
    source "$AGENT_HOME/.envrc"

    # Check if AGENT_HOME is set
    if [ -z "$AGENT_HOME" ]; then
        echo "AGENT_HOME environment variable not set. Exiting."
        return 1
    fi

    # Activate the virtual environment
    source "$AGENT_HOME/venv/bin/activate"

    # Change directory to AGENT_HOME
    cd "$AGENT_HOME" || return 1
}
