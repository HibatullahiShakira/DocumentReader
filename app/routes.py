import os

from flask import render_template, request, jsonify
import redis
import json
import psycopg2
from psycopg2 import Error
from werkzeug.utils import secure_filename
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def init_routes(app, redis_client, parser, DB_CONFIG):
    @app.route('/')
    def dashboard():
        try:
            # Check Redis cache first
            cached_data = redis_client.get('dashboard_data')
            if cached_data:
                logger.info("Serving dashboard from cache")
                data = json.loads(cached_data)
            else:
                # Fetch from database if not in cache
                conn = psycopg2.connect(**DB_CONFIG)
                cur = conn.cursor()
                cur.execute("SELECT * FROM pitch_decks ORDER BY upload_date DESC")
                data = cur.fetchall()
                cur.close()
                conn.close()

                redis_client.setex('dashboard_data', 300, json.dumps(data))

            return render_template('dashboard.html', data=data)
        except Error as e:
            logger.error(f"Dashboard data fetch error: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    @app.route('/api/upload', methods=['POST'])
    def upload_file():
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']

        if not file or file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if not allowed_file(file.filename):
            return jsonify({'error': 'Unsupported file format'}), 400

        try:
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            # Add to Redis queue for processing
            job = {
                'filename': filename,
                'file_path': file_path,
                'timestamp': datetime.now().isoformat()
            }
            redis_client.lpush('processing_queue', json.dumps(job))

            return jsonify({
                'message': 'File queued for processing',
                'filename': filename
            }), 202

        except Exception as e:
            logger.error(f"Upload error: {e}")
            return jsonify({'error': str(e)}), 500


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'pdf', 'pptx'}
