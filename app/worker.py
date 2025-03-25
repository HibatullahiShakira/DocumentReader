# app/worker.py
import redis
import json
import os
from datetime import datetime
import nltk
nltk.download('vader_lexicon')
from flask import Flask
from dotenv import load_dotenv
from app.models import PitchDeckParser, PitchDeck, db
from app.config import get_config

load_dotenv()

app = Flask(__name__)
app.config.from_object(get_config())
db.init_app(app)

# Redis configuration
try:
    redis_client = redis.Redis(
        host=app.config['REDIS_HOST'],
        port=app.config['REDIS_PORT'],
        db=app.config['REDIS_DB'],
        decode_responses=True
    )
    redis_client.ping()
    print("Successfully connected to Redis")
except redis.ConnectionError as e:
    print(f"Failed to connect to Redis: {e}")
    raise

print("Starting worker")

def process_queue():
    parser = PitchDeckParser()
    with app.app_context():
        while True:
            try:
                print("Waiting for job in processing queue")
                job_data = redis_client.brpop('processing_queue', timeout=5)
                if job_data:
                    _, job_json = job_data
                    job = json.loads(job_json)
                    file_path = job['file_path']
                    filename = job['filename']

                    print(f"Processing file: {filename}")
                    if filename.endswith('.pdf'):
                        content, slide_count = parser.parse_pdf(file_path)
                    else:
                        content, slide_count = parser.parse_pptx(file_path)

                    print("Analyzing content")
                    analysis = parser.analyze_content(content)

                    print("Storing data in database")
                    pitch_deck = PitchDeck(filename, content, slide_count, analysis)
                    pitch_deck.save(redis_client)

                    print("Cleaning up temporary file")
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    print(f"Processed file: {filename}")
            except Exception as e:
                print(f"Queue processing error: {e}")

if __name__ == '__main__':
    print("Starting queue processing")
    process_queue()