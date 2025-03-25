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

        os.makedirs(self.app.config['UPLOAD_FOLDER'], exist_ok=True)

        with self.app.app_context():
            db.drop_all()
            db.create_all()

        self.redis_client = redis.Redis(
            host=self.app.config['REDIS_HOST'],
            port=self.app.config['REDIS_PORT'],
            db=self.app.config['REDIS_DB'],
            decode_responses=True
        )
        self.redis_client.flushdb()

        self.test_file_path = os.path.join(self.app.config['UPLOAD_FOLDER'], "test.pdf")
        with open(self.test_file_path, "wb") as f:
            f.write(b"%PDF-1.4\n% Test PDF content\n")

    def tearDown(self):
        with self.app.app_context():
            db.drop_all()
        self.redis_client.flushdb()
        if os.path.exists(self.app.config['UPLOAD_FOLDER']):
            for file in os.listdir(self.app.config['UPLOAD_FOLDER']):
                file_path = os.path.join(self.app.config['UPLOAD_FOLDER'], file)
                if os.path.isfile(file_path):
                    os.remove(file_path)
            os.rmdir(self.app.config['UPLOAD_FOLDER'])

    def test_upload_endpoint_no_file(self):
        response = self.client.post('/api/upload')
        self.assertEqual(response.status_code, 400)
        self.assertIn(b'No file part', response.data)

        with self.app.app_context():
            pitch_deck = PitchDeck.query.filter_by(filename="test.pdf").first()
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
        self.assertIn(b'Invalid file type', response.data)

        with self.app.app_context():
            pitch_deck = PitchDeck.query.filter_by(filename="test.txt").first()
            self.assertIsNone(pitch_deck, "A pitch deck was unexpectedly saved to the database")
        os.remove("test.txt")

    def test_upload_endpoint_valid_file(self):
        with open(self.test_file_path, "rb") as f:
            response = self.client.post(
                '/api/upload',
                content_type='multipart/form-data',
                data={'file': (f, 'test.pdf')}
            )
        self.assertEqual(response.status_code, 302)
        self.assertIn('Location', response.headers)
        self.assertEqual(
            response.headers['Location'],
            '/?file=test.pdf'
        )

        job = self.redis_client.lpop("processing_queue")
        self.assertIsNotNone(job, "No job was added to the queue")
        job_data = json.loads(job)
        self.assertEqual(job_data["filename"], "test.pdf", "Job filename mismatch")
        self.assertEqual(job_data["file_path"], "/app/test_uploads/test.pdf")

        saved_file_path = "/app/test_uploads/test.pdf"
        self.assertTrue(os.path.exists(self.test_file_path), f"File was not saved to {saved_file_path}")

        with self.app.app_context():
            pitch_deck = PitchDeck.query.filter_by(filename="test.pdf").first()
            self.assertIsNotNone(pitch_deck, "Pitch deck was not saved to the database")
            self.assertEqual(pitch_deck.status, "pending", "Pitch deck status should be 'pending' after upload")

    def test_worker_processing(self):
        job = {
            'file_path': self.test_file_path,
            'filename': 'test.pdf'
        }
        self.redis_client.lpush('processing_queue', json.dumps(job))

        with self.app.app_context():
            pitch_deck = PitchDeck(
                filename="test.pdf",
                status="pending"
            )
            db.session.add(pitch_deck)
            db.session.commit()

        sia = SentimentIntensityAnalyzer()
        parser = PitchDeckParser(sia=sia)

        content = "Test content with a problem and solution in a market."
        slide_count = 5
        word_count = len(content.split())
        analysis = parser.analyze_content(content)

        with self.app.app_context():
            pitch_deck = PitchDeck.query.filter_by(filename="test.pdf").first()
            pitch_deck.content = content
            pitch_deck.slide_count = slide_count
            pitch_deck.word_count = word_count
            pitch_deck.sentiment = analysis['sentiment']
            pitch_deck.problem = analysis['problem']
            pitch_deck.solution = analysis['solution']
            pitch_deck.market = analysis['market']
            pitch_deck.status = "processed"
            pitch_deck.save(self.redis_client)

        # Verify the data was saved to the database
        with self.app.app_context():
            pitch_deck = PitchDeck.query.filter_by(filename="test.pdf").first()
            self.assertIsNotNone(pitch_deck, "Pitch deck was not saved to the database")
            self.assertEqual(pitch_deck.filename, "test.pdf")
            self.assertEqual(pitch_deck.content, "Test content with a problem and solution in a market.")
            self.assertEqual(pitch_deck.slide_count, 5)
            self.assertEqual(pitch_deck.word_count, 8)
            self.assertEqual(pitch_deck.status, "processed")
            self.assertEqual(pitch_deck.problem, "a problem")
            self.assertEqual(pitch_deck.solution, "solution")
            self.assertEqual(pitch_deck.market, "a market")
            self.assertIn(pitch_deck.sentiment, ['positive', 'negative', 'neutral'])

    def test_database_save_and_retrieve(self):
        with self.app.app_context():
            # Create and save a pitch deck
            pitch_deck = PitchDeck(
                filename="test.pdf",
                content="Test content",
                slide_count=5,
                word_count=2,
                sentiment="positive",
                problem="Test problem",
                solution="Test solution",
                market="Test market",
                status="processed"
            )
            pitch_deck.save(self.redis_client)

            retrieved_deck = PitchDeck.query.filter_by(filename="test.pdf").first()
            self.assertIsNotNone(retrieved_deck)
            self.assertEqual(retrieved_deck.filename, "test.pdf")
            self.assertEqual(retrieved_deck.content, "Test content")
            self.assertEqual(retrieved_deck.slide_count, 5)
            self.assertEqual(retrieved_deck.word_count, 2)
            self.assertEqual(retrieved_deck.sentiment, "positive")
            self.assertEqual(retrieved_deck.problem, "Test problem")
            self.assertEqual(retrieved_deck.solution, "Test solution")
            self.assertEqual(retrieved_deck.market, "Test market")
            self.assertEqual(retrieved_deck.status, "processed")

    def test_database_update(self):
        with self.app.app_context():
            pitch_deck = PitchDeck(
                filename="test.pdf",
                content="Initial content",
                slide_count=3,
                word_count=2,
                sentiment="neutral",
                problem="Initial problem",
                solution="Initial solution",
                market="Initial market",
                status="pending"
            )
            pitch_deck.save(self.redis_client)

            pitch_deck.content = "Updated content"
            pitch_deck.slide_count = 5
            pitch_deck.word_count = 3
            pitch_deck.sentiment = "positive"
            pitch_deck.problem = "Updated problem"
            pitch_deck.solution = "Updated solution"
            pitch_deck.market = "Updated market"
            pitch_deck.status = "processed"
            pitch_deck.save(self.redis_client)

            updated_deck = PitchDeck.query.filter_by(filename="test.pdf").first()
            self.assertIsNotNone(updated_deck)
            self.assertEqual(updated_deck.content, "Updated content")
            self.assertEqual(updated_deck.slide_count, 5)
            self.assertEqual(updated_deck.word_count, 3)
            self.assertEqual(updated_deck.sentiment, "positive")
            self.assertEqual(updated_deck.problem, "Updated problem")
            self.assertEqual(updated_deck.solution, "Updated solution")
            self.assertEqual(updated_deck.market, "Updated market")
            self.assertEqual(updated_deck.status, "processed")

    def test_database_delete(self):
        with self.app.app_context():
            # Create and save a pitch deck
            pitch_deck = PitchDeck(
                filename="test.pdf",
                content="Test content",
                slide_count=5,
                word_count=2,
                sentiment="positive",
                problem="Test problem",
                solution="Test solution",
                market="Test market",
                status="processed"
            )
            pitch_deck.save(self.redis_client)

            db.session.delete(pitch_deck)
            db.session.commit()

            deleted_deck = PitchDeck.query.filter_by(filename="test.pdf").first()
            self.assertIsNone(deleted_deck, "Pitch deck was not deleted from the database")

    def test_pitch_deck_parser(self):
        sia = SentimentIntensityAnalyzer()
        parser = PitchDeckParser(sia=sia)

        content = (
            "Our problem is that people struggle to find affordable housing. "
            "Our solution is a platform that connects renters with landlords directly. "
            "The market is the rental industry, valued at $100 billion."
        )
        analysis = parser.analyze_content(content)

        self.assertEqual(analysis['problem'], "people struggle to find affordable housing")
        self.assertEqual(analysis['solution'], "a platform that connects renters with landlords directly")
        self.assertEqual(analysis['market'], "the rental industry")
        self.assertIn(analysis['sentiment'], ['positive', 'negative', 'neutral'])

        content = "This is a generic presentation with no specific details."
        analysis = parser.analyze_content(content)

        self.assertEqual(analysis['problem'], "Not identified")
        self.assertEqual(analysis['solution'], "Not identified")
        self.assertEqual(analysis['market'], "Not identified")
        self.assertIn(analysis['sentiment'], ['positive', 'negative', 'neutral'])

    def test_file_handling_and_database(self):
        with open(self.test_file_path, "rb") as f:
            response = self.client.post(
                '/api/upload',
                content_type='multipart/form-data',
                data={'file': (f, 'test.pdf')}
            )
        self.assertEqual(response.status_code, 302)

        with self.app.app_context():
            pitch_deck = PitchDeck.query.filter_by(filename="test.pdf").first()
            self.assertIsNotNone(pitch_deck)
            self.assertEqual(pitch_deck.status, "pending")

        # Process the job with the worker
        job = self.redis_client.lpop("processing_queue")
        job_data = json.loads(job)

        sia = SentimentIntensityAnalyzer()
        parser = PitchDeckParser(sia=sia)
        content = "Test content with a problem and solution in a market."
        slide_count = 5
        word_count = len(content.split())
        analysis = parser.analyze_content(content)

        with self.app.app_context():
            pitch_deck = PitchDeck.query.filter_by(filename="test.pdf").first()
            pitch_deck.content = content
            pitch_deck.slide_count = slide_count
            pitch_deck.word_count = word_count
            pitch_deck.sentiment = analysis['sentiment']
            pitch_deck.problem = analysis['problem']
            pitch_deck.solution = analysis['solution']
            pitch_deck.market = analysis['market']
            pitch_deck.status = "processed"
            pitch_deck.save(self.redis_client)

        with self.app.app_context():
            pitch_deck = PitchDeck.query.filter_by(filename="test.pdf").first()
            self.assertEqual(pitch_deck.status, "processed")
            self.assertEqual(pitch_deck.content, "Test content with a problem and solution in a market.")
            self.assertEqual(pitch_deck.slide_count, 5)
            self.assertEqual(pitch_deck.word_count, 8)


if __name__ == "__main__":
    unittest.main()
