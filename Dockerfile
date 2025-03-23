FROM python:3.12-slim

LABEL authors="Shakirah"

WORKDIR /app


RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    libpq5 \
    && apt-get install --reinstall libpq5 \
    && rm -rf /var/lib/apt/lists/*


COPY requirements.txt .


RUN pip install --no-cache-dir -r requirements.txt

RUN pip install gunicorn


RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app


USER appuser

COPY --chown=appuser:appuser . .


EXPOSE 5000


CMD ["python", "run.py"]