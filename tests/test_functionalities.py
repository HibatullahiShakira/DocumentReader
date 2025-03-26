import unittest
import os
import redis
import json
from app.app import create_app
from app.models import db, PitchDeck, PitchDeckParser
from nltk.sentiment import SentimentIntensityAnalyzer


class TestPitchDeckFunctionalities(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.from_object('app.config.TestingConfig')
        self.client = self.app.test_client()

        try:
            os.makedirs(self.app.config['UPLOAD_FOLDER'], exist_ok=True)
        except Exception as e:
            self.fail(f"Failed to create test uploads folder: {e}")

        with self.app.app_context():
            try:
                db.drop_all()
                db.create_all()
            except Exception as e:
                self.fail(f"Failed to initialize database: {e}")

        try:
            self.redis_client = redis.Redis(
                host='redis',
                port=6379,
                db=1,
                decode_responses=True
            )
            self.redis_client.ping()
        except redis.ConnectionError as e:
            self.fail(f"Failed to connect to Redis: {e}")
        # Clear the Redis queue and cache
        self.redis_client.flushdb()

        self.test_pdf_path = os.path.join(self.app.config['UPLOAD_FOLDER'], "Data Engineer.pdf")
        print(f"Looking for Data Engineer.pdf at: {self.test_pdf_path}")
        if not os.path.exists(self.test_pdf_path):
            self.fail(
                f"Test PDF file not found at {self.test_pdf_path}.")

        self.test_pptx_path = os.path.join(self.app.config['UPLOAD_FOLDER'], "test.pptx")
        with open(self.test_pptx_path, "wb") as f:
            f.write(b"Placeholder PPTX content")

    def tearDown(self):
        with self.app.app_context():
            try:
                db.drop_all()
            except Exception as e:
                print(f"Warning: Failed to drop database: {e}")
        self.redis_client.flushdb()
        if os.path.exists(self.app.config['UPLOAD_FOLDER']):
            for file in os.listdir(self.app.config['UPLOAD_FOLDER']):
                if file != "Data Engineer.pdf":  # Don't delete the test PDF
                    file_path = os.path.join(self.app.config['UPLOAD_FOLDER'], file)
                    if os.path.isfile(file_path):
                        os.remove(file_path)

    def test_upload_endpoint_no_file(self):
        response = self.client.post('/api/upload')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json, {'error': 'No file provided'})

        # Verify no pitch deck is saved to the database
        with self.app.app_context():
            pitch_deck = PitchDeck.query.filter_by(filename="Data Engineer.pdf").first()
            self.assertIsNone(pitch_deck, "A pitch deck was unexpectedly saved to the database")

    def test_upload_endpoint_invalid_file(self):
        with open("test.txt", "w") as f:
            f.write("Invalid file")
        with open("test.txt", "rb") as f:
            response = self.client.post(
                '/api/upload',
                content_type='multipart/form-data',
                data={'file': (f, 'test.txt')}
            )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json, {'error': 'Unsupported file format'})

        with self.app.app_context():
            pitch_deck = PitchDeck.query.filter_by(filename="test.txt").first()
            self.assertIsNone(pitch_deck, "A pitch deck was unexpectedly saved to the database")
        os.remove("test.txt")

    def test_upload_endpoint_valid_pdf_file(self):
        with open(self.test_pdf_path, "rb") as f:
            response = self.client.post(
                '/api/upload',
                content_type='multipart/form-data',
                data={'file': (f, 'Data Engineer.pdf')}
            )
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json, {
            'message': 'File queued for processing',
            'filename': 'Data Engineer.pdf'
        })

        job = self.redis_client.lpop("processing_queue")
        self.assertIsNotNone(job, "No job was added to the queue")
        job_data = json.loads(job)
        self.assertEqual(job_data["filename"], "Data Engineer.pdf", "Job filename mismatch")
        self.assertEqual(job_data["file_path"], os.path.join(self.app.config['UPLOAD_FOLDER'], "Data Engineer.pdf"))

        self.assertTrue(os.path.exists(self.test_pdf_path), f"File was not found at {self.test_pdf_path}")

        with self.app.app_context():
            pitch_deck = PitchDeck.query.filter_by(filename="Data Engineer.pdf").first()
            self.assertIsNone(pitch_deck, "A pitch deck was unexpectedly saved to the database")

    def test_upload_endpoint_valid_pptx_file(self):
        with open(self.test_pptx_path, "rb") as f:
            response = self.client.post(
                '/api/upload',
                content_type='multipart/form-data',
                data={'file': (f, 'test.pptx')}
            )
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json, {
            'message': 'File queued for processing',
            'filename': 'test.pptx'
        })

        job = self.redis_client.lpop("processing_queue")
        self.assertIsNotNone(job, "No job was added to the queue")
        job_data = json.loads(job)
        self.assertEqual(job_data["filename"], "test.pptx", "Job filename mismatch")
        self.assertEqual(job_data["file_path"], os.path.join(self.app.config['UPLOAD_FOLDER'], "test.pptx"))

        self.assertTrue(os.path.exists(self.test_pptx_path), f"File was not saved to {self.test_pptx_path}")

    def test_worker_processing_pdf(self):
        job = {
            'file_path': self.test_pdf_path,
            'filename': 'Data Engineer.pdf',
            'timestamp': '2023-01-01T00:00:00'
        }
        self.redis_client.lpush('processing_queue', json.dumps(job))

        sia = SentimentIntensityAnalyzer()
        parser = PitchDeckParser(sia=sia)

        content, slide_count = parser.parse_pdf(self.test_pdf_path)
        analysis = parser.analyze_content(content)

        with self.app.app_context():
            pitch_deck = PitchDeck(
                filename="Data Engineer.pdf",
                content=content,
                slide_count=slide_count,
                analysis=analysis,
                status="processed"
            )
            pitch_deck.save(self.redis_client)

        with self.app.app_context():
            pitch_deck = PitchDeck.query.filter_by(filename="Data Engineer.pdf").first()
            self.assertIsNotNone(pitch_deck, "Pitch deck was not saved to the database")
            self.assertEqual(pitch_deck.filename, "Data Engineer.pdf")
            self.assertIn("Shakira Hibatullahi", pitch_deck.content)
            self.assertIn("Aspiring Data Engineer Intern", pitch_deck.content)
            self.assertIsInstance(pitch_deck.slide_count, int)
            self.assertGreater(pitch_deck.slide_count, 0)
            self.assertEqual(pitch_deck.word_count, len(content.split()))
            self.assertEqual(pitch_deck.char_count, len(content))
            self.assertEqual(pitch_deck.status, "processed")
            self.assertIsInstance(pitch_deck.sentiment_score, float)
            self.assertIn(pitch_deck.sentiment_type, ['Positive', 'Negative', 'Neutral'])
            self.assertIn("aspiring data engineer intern", pitch_deck.problem.lower())

        self.assertIsNone(self.redis_client.get('dashboard_data'), "Redis cache was not invalidated")

    def test_database_save_and_retrieve(self):
        analysis = {
            'word_count': 2,
            'char_count': 12,
            'sentiment_score': 0.5,
            'sentiment_type': 'Positive',
            'problem': 'Test problem',
            'solution': 'Test solution',
            'market': 'Test market'
        }
        with self.app.app_context():
            pitch_deck = PitchDeck(
                filename="Data Engineer.pdf",
                content="Test content",
                slide_count=5,
                analysis=analysis,
                status="processed"
            )
            pitch_deck.save(self.redis_client)

            retrieved_deck = PitchDeck.query.filter_by(filename="Data Engineer.pdf").first()
            self.assertIsNotNone(retrieved_deck)
            self.assertEqual(retrieved_deck.filename, "Data Engineer.pdf")
            self.assertEqual(retrieved_deck.content, "Test content")
            self.assertEqual(retrieved_deck.slide_count, 5)
            self.assertEqual(retrieved_deck.word_count, 2)
            self.assertEqual(retrieved_deck.char_count, 12)
            self.assertEqual(retrieved_deck.sentiment_score, 0.5)
            self.assertEqual(retrieved_deck.sentiment_type, "Positive")
            self.assertEqual(retrieved_deck.problem, "Test problem")
            self.assertEqual(retrieved_deck.solution, "Test solution")
            self.assertEqual(retrieved_deck.market, "Test market")
            self.assertEqual(retrieved_deck.status, "processed")

    def test_database_update(self):
        analysis = {
            'word_count': 2,
            'char_count': 12,
            'sentiment_score': 0.0,
            'sentiment_type': 'Neutral',
            'problem': 'Initial problem',
            'solution': 'Initial solution',
            'market': 'Initial market'
        }
        with self.app.app_context():
            pitch_deck = PitchDeck(
                filename="Data Engineer.pdf",
                content="Initial content",
                slide_count=3,
                analysis=analysis,
                status="pending"
            )
            pitch_deck.save(self.redis_client)

            updated_analysis = {
                'word_count': 3,
                'char_count': 15,
                'sentiment_score': 0.6,
                'sentiment_type': 'Positive',
                'problem': 'Updated problem',
                'solution': 'Updated solution',
                'market': 'Updated market'
            }
            pitch_deck.content = "Updated content"
            pitch_deck.slide_count = 5
            pitch_deck.status = "processed"
            pitch_deck.word_count = updated_analysis['word_count']
            pitch_deck.char_count = updated_analysis['char_count']
            pitch_deck.sentiment_score = updated_analysis['sentiment_score']
            pitch_deck.sentiment_type = updated_analysis['sentiment_type']
            pitch_deck.problem = updated_analysis['problem']
            pitch_deck.solution = updated_analysis['solution']
            pitch_deck.market = updated_analysis['market']
            pitch_deck.save(self.redis_client)

            updated_deck = PitchDeck.query.filter_by(filename="Data Engineer.pdf").first()
            self.assertIsNotNone(updated_deck)
            self.assertEqual(updated_deck.content, "Updated content")
            self.assertEqual(updated_deck.slide_count, 5)
            self.assertEqual(updated_deck.word_count, 3)
            self.assertEqual(updated_deck.char_count, 15)
            self.assertEqual(updated_deck.sentiment_score, 0.6)
            self.assertEqual(updated_deck.sentiment_type, "Positive")
            self.assertEqual(updated_deck.problem, "Updated problem")
            self.assertEqual(updated_deck.solution, "Updated solution")
            self.assertEqual(updated_deck.market, "Updated market")
            self.assertEqual(updated_deck.status, "processed")

    def test_database_delete(self):
        analysis = {
            'word_count': 2,
            'char_count': 12,
            'sentiment_score': 0.5,
            'sentiment_type': 'Positive',
            'problem': 'Test problem',
            'solution': 'Test solution',
            'market': 'Test market'
        }
        with self.app.app_context():
            pitch_deck = PitchDeck(
                filename="Data Engineer.pdf",
                content="Test content",
                slide_count=5,
                analysis=analysis,
                status="processed"
            )
            pitch_deck.save(self.redis_client)

            db.session.delete(pitch_deck)
            db.session.commit()

            deleted_deck = PitchDeck.query.filter_by(filename="Data Engineer.pdf").first()
            self.assertIsNone(deleted_deck, "Pitch deck was not deleted from the database")

    def test_pitch_deck_parser_analyze_content(self):
        sia = SentimentIntensityAnalyzer()
        parser = PitchDeckParser(sia=sia)

        content = (
            "Our problem is that people struggle to find affordable housing.\n"
            "Our solution is a platform that connects renters with landlords directly.\n"
            "The market is the rental industry, valued at $100 billion."
        )
        analysis = parser.analyze_content(content)

        self.assertEqual(analysis['problem'], "our problem is that people struggle to find affordable housing.")
        self.assertEqual(analysis['solution'],
                         "our solution is a platform that connects renters with landlords directly.")
        self.assertEqual(analysis['market'], "the market is the rental industry, valued at $100 billion.")
        self.assertIsInstance(analysis['sentiment_score'], float)
        self.assertIn(analysis['sentiment_type'], ['Positive', 'Negative', 'Neutral'])
        self.assertEqual(analysis['word_count'], 16)
        self.assertEqual(analysis['char_count'], 92)

        content = "This is a generic presentation with no specific details."
        analysis = parser.analyze_content(content)

        self.assertNotIn('problem', analysis)
        self.assertNotIn('solution', analysis)
        self.assertNotIn('market', analysis)
        self.assertIsInstance(analysis['sentiment_score'], float)
        self.assertIn(analysis['sentiment_type'], ['Positive', 'Negative', 'Neutral'])
        self.assertEqual(analysis['word_count'], 9)
        self.assertEqual(analysis['char_count'], 55)

    def test_file_handling_and_database(self):
        with open(self.test_pdf_path, "rb") as f:
            response = self.client.post(
                '/api/upload',
                content_type='multipart/form-data',
                data={'file': (f, 'Data Engineer.pdf')}
            )
        self.assertEqual(response.status_code, 202)

        job = self.redis_client.lpop("processing_queue")
        job_data = json.loads(job)

        sia = SentimentIntensityAnalyzer()
        parser = PitchDeckParser(sia=sia)
        content, slide_count = parser.parse_pdf(job_data['file_path'])
        analysis = parser.analyze_content(content)

        with self.app.app_context():
            pitch_deck = PitchDeck(
                filename=job_data['filename'],
                content=content,
                slide_count=slide_count,
                analysis=analysis,
                status="processed"
            )
            pitch_deck.save(self.redis_client)

        with self.app.app_context():
            pitch_deck = PitchDeck.query.filter_by(filename="Data Engineer.pdf").first()
            self.assertEqual(pitch_deck.status, "processed")
            self.assertIn("Shakira Hibatullahi", pitch_deck.content)
            self.assertIn("Aspiring Data Engineer Intern", pitch_deck.content)
            self.assertIsInstance(pitch_deck.slide_count, int)
            self.assertGreater(pitch_deck.slide_count, 0)
            self.assertEqual(pitch_deck.word_count, len(content.split()))
            self.assertEqual(pitch_deck.char_count, len(content))


if __name__ == "__main__":
    unittest.main()
