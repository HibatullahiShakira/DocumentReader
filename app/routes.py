import os
from flask import render_template, request, jsonify
import json
from werkzeug.utils import secure_filename
from datetime import datetime
from app.models import PitchDeck


def init_routes(app, redis_client, parser):
    @app.route('/')
    def dashboard():
        try:
            cached_data = redis_client.get('dashboard_data')
            if cached_data:
                print("Serving dashboard from cache")
                data = json.loads(cached_data)
            else:
                pitch_decks = PitchDeck.query.order_by(PitchDeck.upload_date.desc()).all()
                data = [{
                    'id': pd.id,
                    'filename': pd.filename,
                    'upload_date': pd.upload_date.isoformat(),
                    'content': pd.content,
                    'slide_count': pd.slide_count,
                    'status': pd.status,
                    'word_count': pd.word_count,
                    'char_count': pd.char_count,
                    'sentiment_score': pd.sentiment_score,
                    'sentiment_type': pd.sentiment_type,
                    'document_type': pd.document_type,
                    'problem': pd.problem,
                    'solution': pd.solution,
                    'market': pd.market,
                    'experience': pd.experience,
                    'skills': pd.skills,
                    'summary': pd.summary,
                    'key_phrases': pd.key_phrases
                } for pd in pitch_decks]
                redis_client.setex('dashboard_data', 300, json.dumps(data))
                print("Cached new dashboard data")
            return render_template('dashboard.html', data=data)
        except Exception as e:
            print(f"Dashboard data fetch error: {e}")
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
            job = {
                'filename': filename,
                'file_path': file_path,
                'timestamp': datetime.now().isoformat()
            }
            redis_client.lpush('processing_queue', json.dumps(job))
            print(f"Queued file for processing: {filename}")
            return jsonify({
                'message': 'File queued for processing',
                'filename': filename
            }), 202
        except Exception as e:
            print(f"Upload error: {e}")
            return jsonify({'error': str(e)}), 500


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'pdf', 'pptx'}
