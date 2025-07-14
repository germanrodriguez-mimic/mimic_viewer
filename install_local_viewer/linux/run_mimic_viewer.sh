#!/bin/bash

# This script activates the virtual environment and runs the Rerun viewer.
# It expects the URL provided by the protocol handler as its first argument.

VENV_DIR="$HOME/.cache/mimic_viewer_opener_venv"
source "$VENV_DIR/bin/activate"

# The first argument ($1) is the rerun:// URL passed by the desktop environment.
DATA_SOURCE=$1

if [ -z "$DATA_SOURCE" ]; then
    echo "Usage: $0 <rerun_url>"
    exit 1
fi

# replace rerun:// with rerun+http://
DATA_SOURCE="${DATA_SOURCE/rerun:\/\//rerun+http:\/\/}"
rerun --memory-limit 90% DATA_SOURCE &
