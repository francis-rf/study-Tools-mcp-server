# Use official Python 3.10 image
FROM python:3.10-slim

# Set working directory inside the container
WORKDIR /app

# Install system dependencies for PDF parsing
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY app.py .
COPY static/ ./static/
COPY templates/ ./templates/

# Create directories for data and logs
RUN mkdir -p data/notes logs

# Expose the port the app runs on
EXPOSE 8080

# Run the application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
