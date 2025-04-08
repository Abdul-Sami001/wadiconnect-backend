#!/bin/bash

# Navigate to the project directory
cd ~/wadiconnect/wadiconnect-backend

# Pull latest changes
git pull

# Activate virtual environment
source ~/.virtualenvs/Wadiconnect/bin/activate

# Install/update requirements
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Reload the web app
touch /var/www/xavics_pythonanywhere_com_wsgi.py

# Create superuser if needed
# python manage.py createsuperuser