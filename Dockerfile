FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for PDF processing
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code only — no frontend
COPY src/ ./src/

# Environment variables
ENV PYTHONPATH=/app

# Expose port
EXPOSE 7860

# Run the app
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "7860"]