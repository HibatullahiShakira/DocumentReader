import unittest
import os
from unittest.mock import patch, MagicMock
from flask import Flask
from app.app import app, redis_client, parser, DB_CONFIG

class TestFlaskRoutes(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.client = self.app.test_client()
        self.client.testing = True
        # Mock Redis client
        self.redis_client = MagicMock()
        app.config['redis_client'] = self.redis_client

    def test_upload_get(self):
        response = self.client.get('/upload')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Upload Pitch Deck', response.data)

    @patch('app.app.redis_client', new_callable=MagicMock)
    @patch('app.app.parser')
    def test_upload_post_pdf(self, mock_parser, mock_redis_client):
        # Mock file upload
        mock_file = MagicMock()
        mock_file.filename = 'test.pdf'
        mock_file.save = MagicMock()

        # Mock parser methods
        mock_parser.parse_pdf.return_value = ("Sample content", 2)
        mock_parser.analyze_content.return_value = {
            'word_count': 2,
            'char_count': 13,
            'sentiment_score': 0.5,
            'sentiment_type': 'Positive'
        }
        mock_parser.store_data.return_value = 1

        with patch('werkzeug.datastructures.FileStorage', return_value=mock_file):
            response = self.client.post('/upload', data={
                'file': mock_file
            }, content_type='multipart/form-data')

        self.assertEqual(response.status_code, 302)  # Redirect after successful upload
        self.assertIn(b'redirect', response.data)
        mock_redis_client.rpush.assert_called_once()

    @patch('psycopg2.connect')
    @patch('app.app.redis_client', new_callable=MagicMock)
    def test_dashboard(self, mock_redis_client, mock_connect):
        # Mock Redis cache miss
        mock_redis_client.get.return_value = None

        # Mock database connection
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_connect.return_value = mock_conn
        mock_cur.fetchall.return_value = [
            (1, 'test.pdf', '2025-03-24 15:00:00', 'Sample content', 2, 'processed',
             2, 13, 0.5, 'Positive', 'problem', 'solution', 'market')
        ]

        response = self.client.get('/dashboard')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Dashboard', response.data)
        mock_redis_client.setex.assert_called_once()

if __name__ == '__main__':
    unittest.main()