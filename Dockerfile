# Use a Python base image
FROM python:3.12

# Set the working directory
WORKDIR /app

# Install system dependencies for PostgreSQL and compilation
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -v || { echo "pip install failed"; exit 1; }

# Download NLTK data
RUN python -m nltk.downloader vader_lexicon || { echo "NLTK download failed"; exit 1; }

# Copy the application code (only the app/ directory contents)
COPY app/* .

# Copy the run.py file
COPY run.py .

# Create the uploads directory (needed for runtime, will be mounted via volume)
RUN mkdir -p uploads
RUN chown -R appuser:appuser uploads

# Create a non-root user and switch to it
RUN useradd -m appuser
USER appuser

# Ensure NLTK data is available for the non-root user
RUN python -c "import nltk; nltk.download('vader_lexicon')"

# Expose the port the app runs on
EXPOSE 5000

# Command to run the application
CMD ["python", "run.py"]