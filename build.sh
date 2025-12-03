#!/usr/bin/env bash
# exit on error
set -o errexit

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Run database migrations
echo "Running database migrations..."
flask db upgrade || echo "No migrations to run or db upgrade failed"

# Create database tables if they don't exist
echo "Creating database tables..."
python -c "from app import create_app; from extensions import db; app = create_app('production'); app.app_context().push(); db.create_all(); print('Database initialized')"

echo "Build completed successfully!"
