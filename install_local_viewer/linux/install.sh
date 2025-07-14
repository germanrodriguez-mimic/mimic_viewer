#!/bin/bash

VENV_DIR="$HOME/.cache/mimic_viewer_opener_venv"
MIMIC_VIEWER_DIR="$HOME/.mimic_viewer"
RUNNER_SCRIPT="install_local_viewer/linux/run_mimic_viewer.sh"
DESKTOP_FILE="install_local_viewer/linux/mimic_viewer.desktop"

echo "Step 1: Checking for 'uv'..."
if ! command -v uv &> /dev/null; then
    echo "Error: 'uv' is not installed or not in your PATH."
    echo "Please install it before running this script."
    echo "See: https://github.com/astral-sh/uv"
    exit 1
fi
echo "'uv' found."


echo "Step 2: Creating virtual environment in '$VENV_DIR'..."
uv venv "$VENV_DIR"
echo "Virtual environment created."


source "$VENV_DIR/bin/activate"
uv pip install .
deactivate
echo "Project installed."


mkdir -p "$MIMIC_VIEWER_DIR"
if [ ! -f "$RUNNER_SCRIPT" ]; then
    echo "Error: The runner script '$RUNNER_SCRIPT' was not found in the current directory."
    exit 1
fi
mv "$RUNNER_SCRIPT" "$MIMIC_VIEWER_DIR/"
echo "Runner script moved to '$MIMIC_VIEWER_DIR'."


APP_DIR="$HOME/.local/share/applications"
mkdir -p "$APP_DIR"
cp "$DESKTOP_FILE" "$APP_DIR/"

echo "Updating desktop database..."
update-desktop-database "$APP_DIR"
echo "Registering 'rerun' scheme handler..."
xdg-mime default "$APP_DIR/mimic_viewer.desktop" x-scheme-handler/rerun


echo "---"
echo "✅ Setup complete!"
echo "Your system is now configured to work with the mimic viewer."
echo "---"