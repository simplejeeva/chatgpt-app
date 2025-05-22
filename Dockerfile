FROM python:3.11.4-slim-bullseye

WORKDIR /app

# Avoid Python writing .pyc files and ensure logs are unbuffered
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system build tools and dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    gcc \
    g++ \
    git \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install Python dependencies
COPY ./requirements.txt /app/
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Copy project code
COPY . /app

# Set entrypoint using gunicorn to run Django
ENTRYPOINT ["gunicorn", "core.wsgi:application", "-b", "0.0.0.0:8000"]
