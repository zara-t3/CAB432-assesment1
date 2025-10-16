FROM python:3.11-slim

# System libs for Pillow/TF/OpenCV (headless)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    libjpeg62-turbo libpng16-16 libwebp7 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py processor.py ./
ENV PYTHONUNBUFFERED=1
CMD ["python", "main.py"]
