FROM python:3.12-slim

# Helpful OS deps (certs for HTTPS; safe to keep)
RUN apt-get update \
  && apt-get install -y --no-install-recommends ca-certificates \
  && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install Python deps first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY app ./app

# Ensure data dir exists inside the container
RUN mkdir -p /data

# App runs on 8080
EXPOSE 8080

# Start Flask app (module form)
CMD ["python", "-m", "app.main"]
