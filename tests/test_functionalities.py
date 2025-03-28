import unittest
import os
import redis
import json
import re
from app.app import create_app
from app.models import db, PitchDeck, PitchDeckParser
from nltk.sentiment import SentimentIntensityAnalyzer

class TestPitchDeckFunctionalities(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.from_object('app.config.TestingConfig')
        self.client = self.app.test_client()

        with self.app.app_context():
            try:
                db.drop_all()
                db.create_all()
            except Exception as e:
                self.fail(f"Failed to initialize database: {e}")

        try:
            self.redis_client = redis.Redis(
                host=self.app.config['REDIS_HOST'],
                port=self.app.config['REDIS_PORT'],
                db=self.app.config['REDIS_DB'],
                decode_responses=True
            )
            self.redis_client.ping()
        except redis.ConnectionError as e:
            self.fail(f"Failed to connect to Redis: {e}")
        self.redis_client.flushdb()

        self.test_pdf_path = os.path.join(self.app.config['UPLOAD_FOLDER'], "Data Engineer.pdf")
        print(f"Looking for Data Engineer.pdf at: {self.test_pdf_path}")
        if not os.path.exists(self.test_pdf_path):
            self.fail(f"Test PDF file not found at {self.test_pdf_path}.")

        self.test_pptx_path = os.path.join(self.app.config['UPLOAD_FOLDER'], "test.pptx")
        with open(self.test_pptx_path, "wb") as f:
            f.write(b"Placeholder PPTX content")

        self.test_generic_pdf_path = os.path.join(self.app.config['UPLOAD_FOLDER'], "Full-Stack Developer (Backend Specialist) - Mar 2025 (2).pdf")
        print(f"Looking for Full-Stack Developer (Backend Specialist) - Mar 2025 (2).pdf at: {self.test_generic_pdf_path}")
        if not os.path.exists(self.test_generic_pdf_path):
            self.fail(f"Test PDF file not found at {self.test_generic_pdf_path}.")

    def tearDown(self):
        with self.app.app_context():
            try:
                db.session.remove()
                db.drop_all()
            except Exception as e:
                print(f"Warning: Failed to drop database: {e}")
        self.redis_client.flushdb()
        if os.path.exists(self.test_pptx_path):
            os.remove(self.test_pptx_path)

    def test_upload_endpoint_no_file(self):
        response = self.client.post('/api/upload')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json, {'error': 'No file provided'})

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
            'filename': 'Data_Engineer.pdf'
        })

        job = self.redis_client.lpop("processing_queue")
        self.assertIsNotNone(job, "No job was added to the queue")
        job_data = json.loads(job)
        self.assertEqual(job_data["filename"], "Data_Engineer.pdf", "Job filename mismatch")
        self.assertEqual(job_data["file_path"], os.path.join(self.app.config['UPLOAD_FOLDER'], "Data_Engineer.pdf"))

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
        print(f"Content of Data Engineer.pdf:\n{content}")
        analysis = parser.analyze_content(content)

        print(f"Extracted experience: {analysis.get('experience')}")
        print(f"Extracted skills: {analysis.get('skills')}")

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
            self.assertEqual(pitch_deck.document_type, "resume")
            normalized_content = re.sub(r'\s+', ' ', pitch_deck.content)
            self.assertIn("Shakira Hibatullahi", normalized_content)
            self.assertIn("Aspiring Data Engineer Intern", normalized_content)
            self.assertIsInstance(pitch_deck.slide_count, int)
            self.assertGreater(pitch_deck.slide_count, 0)
            self.assertEqual(pitch_deck.word_count, len(content.split()))
            self.assertEqual(pitch_deck.char_count, len(content.replace('\n', '')))
            self.assertEqual(pitch_deck.status, "processed")
            self.assertIsInstance(pitch_deck.sentiment_score, float)
            self.assertIn(pitch_deck.sentiment_type, ['Positive', 'Negative', 'Neutral'])
            self.assertIn("aspiring data engineer intern", pitch_deck.problem.lower())
            self.assertIn("data engineering & analytics intern", pitch_deck.experience.lower())
            self.assertIn("programming: python, sql, nosql", pitch_deck.skills.lower())
            self.assertIsNone(pitch_deck.solution)
            self.assertIsNone(pitch_deck.market)
            self.assertIsNone(pitch_deck.summary)
            self.assertIsNone(pitch_deck.key_phrases)

        self.assertIsNone(self.redis_client.get('dashboard_data'), "Redis cache was not invalidated")

    def test_worker_processing_generic_pdf(self):
        job = {
            'file_path': self.test_generic_pdf_path,
            'filename': 'Full-Stack Developer (Backend Specialist) - Mar 2025 (2).pdf',
            'timestamp': '2023-01-01T00:00:00'
        }
        self.redis_client.lpush('processing_queue', json.dumps(job))

        sia = SentimentIntensityAnalyzer()
        parser = PitchDeckParser(sia=sia)

        content, slide_count = parser.parse_pdf(self.test_generic_pdf_path)
        print(f"Content of Full-Stack Developer PDF:\n{content}")
        print(f"Content length with newlines: {len(content)}")
        print(f"Content length without newlines: {len(content.replace('\n', ''))}")
        analysis = parser.analyze_content(content)
        print(f"Analysis:\n{analysis}")

        with self.app.app_context():
            pitch_deck = PitchDeck(
                filename="Full-Stack Developer (Backend Specialist) - Mar 2025 (2).pdf",
                content=content,
                slide_count=slide_count,
                analysis=analysis,
                status="processed"
            )
            pitch_deck.save(self.redis_client)

        with self.app.app_context():
            pitch_deck = PitchDeck.query.filter_by(filename="Full-Stack Developer (Backend Specialist) - Mar 2025 (2).pdf").first()
            self.assertIsNotNone(pitch_deck, "Pitch deck was not saved to the database")
            self.assertEqual(pitch_deck.filename, "Full-Stack Developer (Backend Specialist) - Mar 2025 (2).pdf")
            self.assertEqual(pitch_deck.document_type, "generic")
            self.assertIsInstance(pitch_deck.slide_count, int)
            self.assertGreater(pitch_deck.slide_count, 0)
            self.assertEqual(pitch_deck.word_count, len(content.split()))
            self.assertEqual(pitch_deck.char_count, len(content.replace('\n', '')))
            self.assertEqual(pitch_deck.status, "processed")
            self.assertIsInstance(pitch_deck.sentiment_score, float)
            self.assertIn(pitch_deck.sentiment_type, ['Positive', 'Negative', 'Neutral'])
            print(f"Problem: {pitch_deck.problem}")
            print(f"Summary: {pitch_deck.summary}")
            print(f"Key Phrases: {pitch_deck.key_phrases}")
            self.assertIn("full-stack developer", pitch_deck.summary.lower())
            self.assertIn("web application", pitch_deck.summary.lower())
            self.assertIn("full-stack developer", pitch_deck.key_phrases.lower())
            self.assertIn("web application", pitch_deck.key_phrases.lower())
            self.assertIn("data parsing", pitch_deck.key_phrases.lower())
            self.assertIsNone(pitch_deck.solution)
            self.assertIsNone(pitch_deck.market)
            self.assertIsNone(pitch_deck.experience)
            self.assertIsNone(pitch_deck.skills)

        self.assertIsNone(self.redis_client.get('dashboard_data'), "Redis cache was not invalidated")

    def test_database_save_and_retrieve(self):
        analysis = {
            'word_count': 2,
            'char_count': 12,
            'sentiment_score': 0.5,
            'sentiment_type': 'Positive',
            'document_type': 'pitch_deck',
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
            self.assertEqual(retrieved_deck.document_type, "pitch_deck")
            self.assertEqual(retrieved_deck.problem, "Test problem")
            self.assertEqual(retrieved_deck.solution, "Test solution")
            self.assertEqual(retrieved_deck.market, "Test market")
            self.assertEqual(retrieved_deck.status, "processed")
            self.assertIsNone(retrieved_deck.experience)
            self.assertIsNone(retrieved_deck.skills)
            self.assertIsNone(retrieved_deck.summary)
            self.assertIsNone(retrieved_deck.key_phrases)

    def test_database_update(self):
        analysis = {
            'word_count': 2,
            'char_count': 12,
            'sentiment_score': 0.0,
            'sentiment_type': 'Neutral',
            'document_type': 'pitch_deck',
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
                'document_type': 'pitch_deck',
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
            pitch_deck.document_type = updated_analysis['document_type']
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
            self.assertEqual(updated_deck.document_type, "pitch_deck")
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
            'document_type': 'pitch_deck',
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

        # Test a pitch deck document
        content_lines = [
            "Our problem is that people struggle to find affordable housing.",
            "Our solution is a platform that connects renters with landlords directly.",
            "The market is the rental industry, valued at $100 billion."
        ]
        content = "\n".join(content_lines)
        print(f"Content: {repr(content)}")
        print(f"Length with newlines: {len(content)}")
        print(f"Length without newlines: {len(content.replace('\n', ''))}")
        print(f"Characters: {[c for c in content]}")
        analysis = parser.analyze_content(content)

        self.assertEqual(analysis['document_type'], "pitch_deck")
        self.assertEqual(analysis['problem'], "our problem is that people struggle to find affordable housing.")
        self.assertEqual(analysis['solution'],
                         "our solution is a platform that connects renters with landlords directly.")
        self.assertEqual(analysis['market'], "the market is the rental industry, valued at $100 billion.")
        self.assertIsInstance(analysis['sentiment_score'], float)
        self.assertIn(analysis['sentiment_type'], ['Positive', 'Negative', 'Neutral'])
        self.assertEqual(analysis['word_count'], 31)
        self.assertEqual(analysis['char_count'], 194)
        self.assertIsNone(analysis.get('experience'))
        self.assertIsNone(analysis.get('skills'))
        self.assertIsNone(analysis.get('summary'))
        self.assertIsNone(analysis.get('key_phrases'))

        # Test a generic document
        content = (
            "This is a report on climate change impacts. "
            "The earth is warming due to greenhouse gas emissions. "
            "Scientists at NASA are researching renewable energy solutions to mitigate these effects. "
            "The report was published in 2023."
        )
        content = re.sub(r'\s+', ' ', content).strip()
        analysis = parser.analyze_content(content)

        self.assertEqual(analysis['document_type'], "generic")
        self.assertNotIn('solution', analysis)
        self.assertNotIn('market', analysis)
        self.assertIsInstance(analysis['sentiment_score'], float)
        self.assertIn(analysis['sentiment_type'], ['Positive', 'Negative', 'Neutral'])
        self.assertEqual(analysis['word_count'], 35)
        self.assertEqual(analysis['char_count'], 220)
        self.assertIn("climate change", analysis['summary'])
        self.assertIn("renewable energy", analysis['summary'])
        self.assertIn("climate change", ', '.join(analysis['key_phrases']).lower())
        self.assertIn("greenhouse gas", ', '.join(analysis['key_phrases']).lower())
        self.assertIn("renewable energy", ', '.join(analysis['key_phrases']).lower())
        self.assertIsNone(analysis.get('experience'))
        self.assertIsNone(analysis.get('skills'))

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
            pitch_deck = PitchDeck.query.filter_by(filename="Data_Engineer.pdf").first()
            self.assertIsNotNone(pitch_deck, "Pitch deck was not saved to the database")
            self.assertEqual(pitch_deck.status, "processed")
            self.assertEqual(pitch_deck.document_type, "resume")
            self.assertIn("Shakira Hibatullahi", re.sub(r'\s+', ' ', pitch_deck.content))
            self.assertIn("Aspiring Data Engineer Intern", re.sub(r'\s+', ' ', pitch_deck.content))
            self.assertIsInstance(pitch_deck.slide_count, int)
            self.assertGreater(pitch_deck.slide_count, 0)
            self.assertEqual(pitch_deck.word_count, len(content.split()))
            self.assertEqual(pitch_deck.char_count, len(content.replace('\n', '')))

if __name__ == "__main__":
    unittest.main()