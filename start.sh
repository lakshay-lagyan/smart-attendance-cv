#!/bin/bash
# Startup script for production

# Use PORT from environment or default to 5000
export PORT=${PORT:-5000}

echo "Starting application on port $PORT"

# Run with Gunicorn
gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --access-logfile - --error-logfile - app:app
