FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY apps/ /app/apps/
COPY configs/ /app/configs/

# Set Python path
ENV PYTHONPATH=/app

# Default command (will be overridden by docker-compose)
CMD ["python", "-u", "/app/apps/ingestor/main.py"]
