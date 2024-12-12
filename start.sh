#!/bin/bash

# Start Celery worker in the background
echo "Starting Celery worker..."
celery -A text_embeddings worker --loglevel=info &

# Start Django development server
echo "Starting Django development server..."
python manage.py runserver 