
FROM python:3.12

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -v || { echo "pip install failed"; exit 1; }

RUN python -m nltk.downloader vader_lexicon || { echo "NLTK download failed"; exit 1; }


COPY app/* .

COPY run.py .


RUN mkdir -p uploads
RUN chown -R appuser:appuser uploads

RUN useradd -m appuser
USER appuser

RUN python -c "import nltk; nltk.download('vader_lexicon')"

EXPOSE 5000

CMD ["python", "run.py"]


RUN useradd -m appuser
USER appuser

RUN python -c "import nltk; nltk.download('vader_lexicon')"


EXPOSE 5000

CMD ["python", "run.py"]


