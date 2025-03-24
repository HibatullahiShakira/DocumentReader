# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies for psycopg2-binary and other packages
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip to the latest version to avoid warnings
RUN pip install --upgrade pip==25.0.1

# Copy the requirements file into the container
COPY requirements.txt .

# Install dependencies with verbose output for debugging
RUN pip install --no-cache-dir -r requirements.txt -v || { echo "pip install failed"; exit 1; }

# Download NLTK data
RUN python -m nltk.downloader vader_lexicon || { echo "NLTK download failed"; exit 1; }

# Copy the rest of the application code
COPY . .

# Create a non-root user and switch to it
RUN useradd -m appuser
USER appuser

# Ensure NLTK data is available for the non-root user
RUN python -c "import nltk; nltk.download('vader_lexicon')"

# Expose the port the app runs on
EXPOSE 5000

# Command to run the application (will be overridden by docker-compose.yml)
CMD ["python", "-m", "app.app"]