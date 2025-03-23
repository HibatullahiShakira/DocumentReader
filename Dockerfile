FROM python:3.12-slim

LABEL authors="Shakirah"

WORKDIR /app

COPY requirements.txt .

# Install system dependencies (e.g., for PyPDF2, python-pptx, etc.)
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -r requirements.txt

RUN useradd -m -u 1000 appuser
USER appuser

COPY . .

EXPOSE 5000

ENV FLASK_ENV=development
ENV FLASK_APP=app.py

# Command to run the Flask app (will be overridden in docker-compose.yml for different services)
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]