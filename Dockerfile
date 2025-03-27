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

# Download NLTK data as root (to ensure it's available globally)
RUN python -m nltk.downloader vader_lexicon punkt averaged_perceptron_tagger stopwords || { echo "NLTK download failed"; exit 1; }

# Copy the entire app directory (preserving the directory structure)
COPY app/ app/

# Copy the run.py file
COPY run.py .

# Create a non-root user
RUN useradd -m appuser

# Create the uploads directory (needed for runtime, will be mounted via volume)
RUN mkdir -p uploads
RUN chown -R appuser:appuser uploads

# Create the NLTK data directory for the non-root user and copy NLTK data
RUN mkdir -p /home/appuser/nltk_data
RUN cp -r /root/nltk_data/* /home/appuser/nltk_data/ || true
RUN chown -R appuser:appuser /home/appuser/nltk_data

# Switch to the non-root user
USER appuser

# Set the NLTK_DATA environment variable to point to the user's NLTK data directory
ENV NLTK_DATA=/home/appuser/nltk_data

# Verify NLTK data is accessible to the non-root user
RUN python -c "import nltk; nltk.download('vader_lexicon', download_dir='/home/appuser/nltk_data'); nltk.download('punkt', download_dir='/home/appuser/nltk_data'); nltk.download('averaged_perceptron_tagger', download_dir='/home/appuser/nltk_data'); nltk.download('stopwords', download_dir='/home/appuser/nltk_data')"

# Expose the port the app runs on
EXPOSE 5000

# Command to run the application
CMD ["python", "run.py"]