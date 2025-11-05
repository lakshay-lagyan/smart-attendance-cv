FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create necessary directories
RUN mkdir -p uploads face_data faiss_index instance

# Set default port
ENV PORT=5000

# Expose port
EXPOSE $PORT

# Run application (use shell form to allow environment variable expansion)
CMD gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 app:app
