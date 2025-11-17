# Stage 1: Build React Mini App
FROM node:18-alpine AS miniapp-builder

WORKDIR /build

# Copy Mini App package files
COPY miniapp/package*.json ./

# Install dependencies
RUN npm install

# Copy Mini App source
COPY miniapp/ ./

# Build Mini App
RUN npm run build

# Stage 2: Build Analytics Dashboard
FROM node:18-alpine AS analytics-builder

WORKDIR /build

# Copy Analytics Dashboard package files
COPY analytics-dashboard/package*.json ./

# Install dependencies
RUN npm install

# Copy Analytics Dashboard source
COPY analytics-dashboard/ ./

# Build Analytics Dashboard
RUN npm run build

# Stage 3: Python application
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app ./app
COPY config ./config
COPY alembic.ini .
COPY scripts ./scripts

# Copy built Mini App from builder stage
COPY --from=miniapp-builder /build/dist ./miniapp/dist

# Copy built Analytics Dashboard from builder stage
COPY --from=analytics-builder /build/dist ./analytics-dashboard/dist

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Expose port (Railway will override this)
EXPOSE 8080

# Run migrations and start server
CMD set -e && \
    echo "🔧 Checking alembic version..." && \
    python scripts/fix_alembic_version.py && \
    echo "🔄 Running migrations..." && \
    alembic upgrade head && \
    echo "✅ Migrations complete" && \
    echo "🚀 Starting FastAPI server on port ${PORT:-8080}..." && \
    uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}


