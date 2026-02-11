# Use official Python 3.10 image
FROM python:3.10-slim

# Set working directory inside the container
WORKDIR /app

# Install system dependencies for PDF parsing
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml .
COPY src/ ./src/
COPY app.py .
COPY static/ ./static/
COPY templates/ ./templates/

# Install dependencies
RUN pip install --no-cache-dir -e .

# Create directories for data and logs
RUN mkdir -p data/notes logs

# Study materials mount point
VOLUME /app/data/notes

# Expose the port the app runs on
EXPOSE 8080

# Run the application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
