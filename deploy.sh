#!/bin/bash

# Create necessary directories
mkdir -p static
mkdir -p media

# Install dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --noinput

# Run migrations
python manage.py migrate

# Create superuser if needed
# python manage.py createsuperuser