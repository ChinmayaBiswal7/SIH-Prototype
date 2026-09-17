# Multi-Stage Build: React Vite Frontend + Python Flask Backend
# Stage 1: Build the React Dashboard
FROM node:20-alpine AS build-frontend
WORKDIR /app/frontend

COPY ClearWays-main/clearways-react/package.json ./
RUN npm install

COPY ClearWays-main/clearways-react/ ./
RUN npm run build

# Stage 2: Production Python Backend Server
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies (including ffmpeg, glib for OpenCV, and tesseract)
RUN apt-get update && apt-get install -y --no-install-recommends curl ffmpeg libglib2.0-0 libgomp1 tesseract-ocr libtesseract-dev && rm -rf /var/lib/apt/lists/*

# Install lightweight CPU-only PyTorch & Torchvision (~150MB instead of 900MB GPU torch)
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Install EasyOCR and pytesseract
RUN pip install --no-cache-dir easyocr pytesseract

# Install Python requirements (JSON array syntax handles spaces cleanly)
COPY ["city flow model/requirements.txt", "./"]
RUN pip install --no-cache-dir -r requirements.txt

# Copy CityFlow Backend code
COPY ["city flow model/", "./cityflow_model/"]

# Copy Vehicle Tracking & Firebase Backend code
COPY ["portotype/", "./portotype/"]

# Copy built React frontend to web static directory
COPY --from=build-frontend /app/frontend/dist ./dist

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV REACT_DIST_DIR=/app/dist
ENV PYTHONPATH="/app/cityflow_model:/app/portotype:${PYTHONPATH}"
ENV PORT=5000


EXPOSE 5000

WORKDIR /app/cityflow_model

# Run with Gunicorn production WSGI server
CMD exec gunicorn --workers 1 --threads 4 --bind 0.0.0.0:${PORT:-5000} --timeout 120 server_standalone:app
