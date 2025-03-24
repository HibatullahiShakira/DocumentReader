# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies for psycopg2-binary and other packages
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install dependencies with verbose output for debugging
RUN pip install --no-cache-dir -r requirements.txt -v || { echo "pip install failed"; exit 1; }

RUN python -m nltk.downloader vader_lexicon

COPY . .


RUN useradd -m appuser
USER appuser

EXPOSE 5000

# Command to run the application (will be overridden by docker-compose.yml)
CMD ["python", "app/app.py"]