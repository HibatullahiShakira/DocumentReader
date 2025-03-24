import unittest
import os
import redis
import psycopg2
from datetime import datetime
from unittest.mock import patch, MagicMock
from app.worker import PitchDeckParser, DB_CONFIG
import PyPDF2
import pptx

class TestPitchDeckParser(unittest.TestCase):
    def setUp(self):
        self.parser = PitchDeckParser()
        # Create a temporary file for testing
        self.test_pdf_path = "test.pdf"
        self.test_pptx_path = "test.pptx"
        # Mock Redis client
        self.redis_client = MagicMock(spec=redis.Redis)
        # Mock database connection
        self.conn = MagicMock()
        self.cur = MagicMock()
        self.conn.cursor.return_value = self.cur

    def tearDown(self):
        # Clean up temporary files if they exist
        if os.path.exists(self.test_pdf_path):
            os.remove(self.test_pdf_path)
        if os.path.exists(self.test_pptx_path):
            os.remove(self.test_pptx_path)

    @patch('PyPDF2.PdfReader')
    def test_parse_pdf(self, mock_pdf_reader):
        # Mock PDF reader
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Sample PDF content"
        mock_pdf.pages = [mock_page]
        mock_pdf_reader.return_value = mock_pdf

        # Create a dummy PDF file
        with open(self.test_pdf_path, 'wb') as f:
            f.write(b"Dummy PDF content")

        content, slide_count = self.parser.parse_pdf(self.test_pdf_path)
        self.assertEqual(content, "Sample PDF content\n")
        self.assertEqual(slide_count, 1)

    @patch('pptx.Presentation')
    def test_parse_pptx(self, mock_presentation):
        # Mock PPTX presentation
        mock_prs = MagicMock()
        mock_slide = MagicMock()
        mock_shape = MagicMock()
        mock_shape.text = "Sample PPTX content"
        mock_shape.has_text = True
        mock_slide.shapes = [mock_shape]
        mock_prs.slides = [mock_slide]
        mock_presentation.return_value = mock_prs

        # Create a dummy PPTX file
        with open(self.test_pptx_path, 'wb') as f:
            f.write(b"Dummy PPTX content")

        content, slide_count = self.parser.parse_pptx(self.test_pptx_path)
        self.assertEqual(content, "Sample PPTX content\n")
        self.assertEqual(slide_count, 1)

    def test_analyze_content(self):
        text = "This is a positive problem and solution for the market."
        analysis = self.parser.analyze_content(text)

        self.assertIn('upload_date', analysis)
        self.assertEqual(analysis['word_count'], 9)
        self.assertEqual(analysis['char_count'], 48)
        self.assertGreater(analysis['sentiment_score'], 0.05)  # Should be positive
        self.assertEqual(analysis['sentiment_type'], 'Positive')
        self.assertEqual(analysis['problem'], "this is a positive problem and solution for the market.")
        self.assertEqual(analysis['solution'], "this is a positive problem and solution for the market.")
        self.assertEqual(analysis['market'], "this is a positive problem and solution for the market.")

    @patch('psycopg2.connect')
    @patch('app.worker.redis_client', new_callable=MagicMock)
    def test_store_data(self, mock_redis_client, mock_connect):
        # Mock database connection
        mock_connect.return_value = self.conn
        self.cur.fetchone.return_value = [1]  # Mock deck_id

        filename = "test.pdf"
        content = "Sample content"
        slide_count = 2
        analysis = {
            'upload_date': "2025-03-24 15:00:00",
            'word_count': 2,
            'char_count': 13,
            'sentiment_score': 0.5,
            'sentiment_type': 'Positive',
            'problem': 'problem statement',
            'solution': 'solution statement',
            'market': 'market statement'
        }

        deck_id = self.parser.store_data(filename, content, slide_count, analysis)
        self.assertEqual(deck_id, 1)
        self.cur.execute.assert_called_once()
        mock_redis_client.delete.assert_called_once_with('dashboard_data')

if __name__ == '__main__':
    unittest.main()