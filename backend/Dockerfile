FROM python:3.11-slim

# Install system dependencies for sandbox executor
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    make \
    python3 \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create sandbox workspace directory
RUN mkdir -p /workspace/sandbox

ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
