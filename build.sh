#!/usr/bin/env bash
# Render build script

set -o errexit

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Collecting static files..."
python manage.py collectstatic --no-input

echo "Running migrations..."
python manage.py migrate_schemas --shared --no-input
python manage.py migrate_schemas --no-input

echo "Build complete!"

