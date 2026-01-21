# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file (adjusting path for Docker context)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code (adjusting paths for Docker context)
# Assuming build context is 'backend' directory
COPY . .

# Expose port
EXPOSE 8000

# Command to run the application
# Use shell form to allow variable expansion of $PORT
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
