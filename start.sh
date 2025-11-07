#!/bin/bash
# Startup script for production

# Use PORT from environment or default to 5000
export PORT=${PORT:-5000}

echo "Starting Smart Attendance System on port $PORT"

# Run database migrations if DATABASE_URL is set (PostgreSQL)
if [ -n "$DATABASE_URL" ]; then
    echo "Running database migrations..."
    python railway_migrate.py || echo "Migration completed with warnings"
fi

# Create necessary directories
mkdir -p uploads face_data faiss_index instance

echo "Starting application server..."

# Run with Gunicorn
gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --access-logfile - --error-logfile - app:app
