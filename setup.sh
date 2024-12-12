#!/bin/bash

# Stop all services and remove volumes
echo "Stopping all services and removing volumes..."
docker compose down -v

# Start database and Redis
echo "Starting database and Redis..."
docker compose up -d

# Wait for database to be ready
echo "Waiting for database to be ready..."
sleep 5

# Install dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Run migrations
echo "Running database migrations..."
python manage.py migrate

# Start Celery worker in the background
echo "Starting Celery worker..."
celery -A text_embeddings worker --loglevel=info &

# Start Django development server
echo "Starting Django development server..."
python manage.py runserver 