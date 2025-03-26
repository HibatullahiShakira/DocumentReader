import pypdf
import pptx
from datetime import datetime
from nltk.sentiment import SentimentIntensityAnalyzer
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class PitchDeckParser:
    def __init__(self, sia=None):
        self.sia = sia if sia else SentimentIntensityAnalyzer()

    def parse_pdf(self, file_path):
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = pypdf.PdfReader(file)
                content = ""
                for page in pdf_reader.pages:
                    content += page.extract_text() + "\n"
                return content, len(pdf_reader.pages)
        except Exception as e:
            print(f"PDF parsing error: {e}")
            raise

    def parse_pptx(self, file_path):
        try:
            prs = pptx.Presentation(file_path)
            content = ""
            for slide in prs.slides:
                for shape in slide.shapes:
                    if hasattr(shape, "text"):
                        content += shape.text + "\n"
            return content, len(prs.slides)
        except Exception as e:
            print(f"PPTX parsing error: {e}")
            raise

    def analyze_content(self, text):
        info = {
            'upload_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'word_count': len(text.split()),
            'char_count': len(text)
        }
        sentiment = self.sia.polarity_scores(text)
        info['sentiment_score'] = sentiment['compound']
        info['sentiment_type'] = 'Positive' if sentiment['compound'] > 0.05 else \
            'Negative' if sentiment['compound'] < -0.05 else 'Neutral'
        lines = text.lower().split('\n')
        for line in lines:
            if 'problem' in line:
                info['problem'] = line.strip()
            elif 'solution' in line:
                info['solution'] = line.strip()
            elif 'market' in line:
                info['market'] = line.strip()
        return info


class PitchDeck(db.Model):
    __tablename__ = 'pitch_decks'

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    content = db.Column(db.Text)
    slide_count = db.Column(db.Integer)
    status = db.Column(db.String(50))
    word_count = db.Column(db.Integer)
    char_count = db.Column(db.Integer)
    sentiment_score = db.Column(db.Float)
    sentiment_type = db.Column(db.String(50))
    problem = db.Column(db.Text)
    solution = db.Column(db.Text)
    market = db.Column(db.Text)

    def __init__(self, filename, content, slide_count, analysis, status='processed'):
        self.filename = filename
        self.content = content
        self.slide_count = slide_count
        self.status = status
        self.word_count = analysis['word_count']
        self.char_count = analysis['char_count']
        self.sentiment_score = analysis['sentiment_score']
        self.sentiment_type = analysis['sentiment_type']
        self.problem = analysis.get('problem')
        self.solution = analysis.get('solution')
        self.market = analysis.get('market')

    def save(self, redis_client):
        try:
            db.session.add(self)
            db.session.commit()
            redis_client.delete('dashboard_data')
            return self.id
        except Exception as e:
            db.session.rollback()
            print(f"Database storage error: {e}")
            raise
