# Use official Python image
FROM python:3.12-slim

# Set working directory inside the container
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your app code
COPY app ./app

# Environment variables
ENV PORT=8080 DATA_DIR=/data

# Expose port 8080
EXPOSE 8080

# Run the app
CMD ["python", "-m", "app.main"]
