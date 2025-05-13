#!/usr/bin/env bash

# Exit if any command fails
set -o errexit

echo "🔧 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "🛠 Applying migrations..."
python manage.py migrate --noinput

echo "📦 Collecting static files..."
python manage.py collectstatic --noinput

echo "✅ Build complete."
