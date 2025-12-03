#!/usr/bin/env bash
# exit on error
set -o errexit

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

echo "Build completed successfully!"
echo "Note: Database will be initialized when the app starts"
