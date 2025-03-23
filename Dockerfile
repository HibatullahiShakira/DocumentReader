FROM python:3.12-slim

LABEL authors="Shakirah"

WORKDIR /app

COPY requirements.txt .

RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -r requirements.txt


RUN pip install gunicorn

RUN useradd -m -u 1000 appuser
USER appuser

COPY . .

EXPOSE 5000

# Default command for development (can be overridden in docker-compose.yml for production)
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]