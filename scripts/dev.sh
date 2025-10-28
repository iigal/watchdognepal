#!/usr/bin/env bash
# scripts/dev.sh — quick local development helper
# Usage: ./scripts/dev.sh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

# Create venv if not present
if [ ! -d "venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv venv
fi

# Activate venv for the script's lifetime
# shellcheck source=/dev/null
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

# Load environment variables from .env if present
if [ -f .env ]; then
  echo "Loading .env file"
  # export all variables from .env
  set -a
  # shellcheck source=/dev/null
  source .env
  set +a
fi

# Apply migrations and runserver
python manage.py migrate

# Inform user about createsuperuser step
echo "If you need an admin user, run: python manage.py createsuperuser"

# Start server
python manage.py runserver 0.0.0.0:8000
