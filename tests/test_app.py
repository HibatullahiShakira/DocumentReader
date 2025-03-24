import pytest
import os
from app.app import app, PitchDeckParser, init_db
from werkzeug.datastructures import FileStorage
import psycopg2
import redis
import json
from datetime import datetime
import io

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['UPLOAD_FOLDER'] = 'test_uploads'
    os.makedirs('test_uploads', exist_ok=True)
    init_db()

    with app.test_client() as client:
        yield client

    if os.path.exists('test_uploads'):
        for file in os.listdir('test_uploads'):
            os.remove(os.path.join('test_uploads', file))
        os.rmdir('test_uploads')

@pytest.fixture
def redis_client():
    return redis.Redis(host='redis', port=6379, db=0, decode_responses=True)

@pytest.fixture
def db_connection():
    conn = psycopg2.connect(**app.DB_CONFIG)
    yield conn
    conn.close()

def create_test_file(filename, content, mode='w'):
    with open(filename, mode) as f:
        f.write(content)
    return open(filename, 'rb')

def test_upload_valid_pdf(client, redis_client, capsys):
    pdf_file = FileStorage(
        stream=create_test_file('test_uploads/test.pdf', "Test PDF\nPage 2"),
        filename='test.pdf',
        content_type='application/pdf'
    )
    response = client.post('/api/upload', data={'file': pdf_file})
    captured = capsys.readouterr()

    assert response.status_code == 202
    assert b'File queued for processing' in response.data
    assert "Queued file for processing: test.pdf" in captured.out

    queue_item = redis_client.lpop('processing_queue')
    assert queue_item is not None
    job = json.loads(queue_item)
    assert job['filename'] == 'test.pdf'

def test_upload_no_file(client):
    response = client.post('/api/upload')
    assert response.status_code == 400
    assert b'No file provided' in response.data

def test_upload_empty_file(client, capsys):
    empty_file = FileStorage(
        stream=io.BytesIO(b""),
        filename='empty.pdf',
        content_type='application/pdf'
    )
    response = client.post('/api/upload', data={'file': empty_file})
    captured = capsys.readouterr()
    assert response.status_code == 202
    assert "Queued file for processing: empty.pdf" in captured.out

def test_upload_unsupported_format(client):
    txt_file = FileStorage(
        stream=create_test_file('test_uploads/test.txt', "Text content"),
        filename='test.txt',
        content_type='text/plain'
    )
    response = client.post('/api/upload', data={'file': txt_file})
    assert response.status_code == 400
    assert b'Unsupported file format' in response.data

def test_upload_large_file(client):
    large_content = b"A" * (app.config['MAX_CONTENT_LENGTH'] + 1)
    large_file = FileStorage(
        stream=io.BytesIO(large_content),
        filename='large.pdf',
        content_type='application/pdf'
    )
    response = client.post('/api/upload', data={'file': large_file})
    assert response.status_code == 413

def test_dashboard_display(client, db_connection, redis_client, capsys):
    cur = db_connection.cursor()
    cur.execute("""
        INSERT INTO pitch_decks (filename, upload_date, content, slide_count, status)
        VALUES (%s, %s, %s, %s, %s)
    """, ('test.pdf', datetime.now(), 'Test content', 2, 'processed'))
    db_connection.commit()

    redis_client.flushdb()
    response = client.get('/')
    captured = capsys.readouterr()
    assert response.status_code == 200
    assert b'test.pdf' in response.data
    assert "Cached new dashboard data" in captured.out

def test_parser_pdf_error_handling(capsys):
    parser = PitchDeckParser()
    with pytest.raises(Exception):
        parser.parse_pdf('nonexistent.pdf')
    captured = capsys.readouterr()
    assert "PDF parsing error" in captured.out

def test_database_connection_error(monkeypatch, capsys):
    parser = PitchDeckParser()
    def mock_connect(*args, **kwargs):
        raise psycopg2.Error("Connection failed")
    monkeypatch.setattr(psycopg2, 'connect', mock_connect)
    with pytest.raises(Exception):
        parser.store_data('test.pdf', 'content', 1, {'word_count': 1, 'char_count': 1, 'sentiment_score': 0, 'sentiment_type': 'Neutral'})
    captured = capsys.readouterr()
    assert "Database storage error" in captured.out

if __name__ == '__main__':
    pytest.main(['-v'])