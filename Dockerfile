FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Install system dependencies (for builds)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install -r requirements.txt

# Copy project source code
COPY . .

# Expose the application port
EXPOSE 8000

# Run the application
CMD ["python", "server.py"]
