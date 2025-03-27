import redis
import json
import os
import logging
import signal
import sys
from datetime import datetime
from flask import Flask
from dotenv import load_dotenv
from app.models import PitchDeckParser, PitchDeck, db
from app.config import get_config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

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
    logger.info("Successfully connected to Redis")
except redis.ConnectionError as e:
    logger.error(f"Failed to connect to Redis: {e}")
    raise

keep_running = True


def signal_handler(sig, frame):
    global keep_running
    logger.info("Received shutdown signal. Finishing current job and exiting...")
    keep_running = False


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def process_queue():
    parser = PitchDeckParser()
    with app.app_context():
        while keep_running:
            try:
                logger.info("Waiting for job in processing queue")
                job_data = redis_client.brpop('processing_queue', timeout=5)
                if job_data and keep_running:
                    _, job_json = job_data
                    job = json.loads(job_json)
                    file_path = job['file_path']
                    filename = job['filename']

                    logger.info(f"Processing file: {filename}")
                    start_time = datetime.now()
                    if filename.endswith('.pdf'):
                        content, slide_count = parser.parse_pdf(file_path)
                    else:
                        content, slide_count = parser.parse_pptx(file_path)

                    logger.info("Analyzing content")
                    analysis = parser.analyze_content(content)
                    logger.debug(f"Analysis results: {analysis}")

                    logger.info("Storing data in database")
                    pitch_deck = PitchDeck(filename, content, slide_count, analysis)
                    pitch_deck.save(redis_client)

                    logger.info("Cleaning up temporary file")
                    if os.path.exists(file_path):
                        try:
                            os.remove(file_path)
                            logger.info(f"Deleted temporary file: {file_path}")
                        except OSError as e:
                            logger.error(f"Failed to delete temporary file {file_path}: {e}")
                    else:
                        logger.warning(f"Temporary file not found: {file_path}")

                    processing_time = (datetime.now() - start_time).total_seconds()
                    logger.info(f"Processed file: {filename} in {processing_time:.2f} seconds")
            except Exception as e:
                logger.error(f"Queue processing error: {e}")


if __name__ == '__main__':
    logger.info("Starting queue processing")
    process_queue()
    logger.info("Worker stopped")
