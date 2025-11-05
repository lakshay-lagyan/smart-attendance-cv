#!/usr/bin/env python3
"""
Entrypoint script for deployment
Handles PORT environment variable properly
"""
import os
import sys
import subprocess

# Get PORT from environment, default to 5000
port = os.environ.get('PORT', '5000')

print(f"Starting application on port {port}")

# Start Gunicorn
cmd = [
    'gunicorn',
    '--bind', f'0.0.0.0:{port}',
    '--workers', '2',
    '--timeout', '120',
    '--access-logfile', '-',
    '--error-logfile', '-',
    'app:app'
]

print(f"Running command: {' '.join(cmd)}")

# Execute Gunicorn
try:
    subprocess.run(cmd, check=True)
except KeyboardInterrupt:
    print("\nShutting down gracefully...")
    sys.exit(0)
except Exception as e:
    print(f"Error starting application: {e}")
    sys.exit(1)
