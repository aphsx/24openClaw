FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for asyncpg/psycopg2 if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run as module or directly
CMD ["uvicorn", "app:socket_app", "--host", "0.0.0.0", "--port", "3001"]
EXPOSE 3001
