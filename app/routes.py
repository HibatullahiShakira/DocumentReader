# app/routes.py
from flask import Blueprint, request, jsonify, render_template
from app import db
from app.models import File, Slide
from app.task import process_file
import os
from sqlalchemy.exc import SQLAlchemyError

main = Blueprint('main', __name__)


@main.route('/')
def index():
    try:
        files = File.query.order_by(File.created_at.desc()).all()
        return render_template('index.html', files=files)
    except SQLAlchemyError as e:
        return render_template('index.html', files=[], error="Database error: Unable to load files")


@main.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'status': 'error', 'message': 'No file part'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'status': 'error', 'message': 'No selected file'}), 400

        if not (file.filename.endswith('.pdf') or file.filename.endswith('.pptx')):
            return jsonify({'status': 'error', 'message': 'Only PDF and PPTX files are allowed'}), 400

        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)

        MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB (limit)
        if file_size > MAX_FILE_SIZE:
            return jsonify({'status': 'error', 'message': 'File size exceeds the maximum limit of 10 MB'}), 400

        upload_folder = os.getenv('UPLOAD_FOLDER', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        filepath = os.path.join(upload_folder, file.filename)
        file.save(filepath)

        try:
            new_file = File(filename=file.filename, filepath=filepath)
            db.session.add(new_file)
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            os.remove(filepath)
            return jsonify({'status': 'error', 'message': 'Database error: Unable to save file'}), 500

        process_file.delay(new_file.id, filepath)

        return jsonify({'status': 'success', 'message': 'File uploaded and processing started', 'file_id': new_file.id})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Error processing file: {str(e)}'}), 500


@main.route('/file/<int:file_id>')
def file_status(file_id):
    try:
        file = File.query.get(file_id)
        if not file:
            return jsonify({'status': 'error', 'message': 'File not found'}), 404

        slides = Slide.query.filter_by(file_id=file_id).all()
        slides_data = [
            {
                'slide_number': slide.slide_number,
                'title': slide.title,
                'content': slide.content,
                'metadata': slide.slide_metadata
            }
            for slide in slides
        ]

        return jsonify({
            'status': file.status,
            'filename': file.filename,
            'created_at': file.created_at.isoformat(),
            'slides': slides_data
        })
    except SQLAlchemyError as e:
        return jsonify({'status': 'error', 'message': 'Database error: Unable to retrieve file'}), 500
