import pptx
import pypdf
import re
from nltk.sentiment import SentimentIntensityAnalyzer
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
from nltk.tag import pos_tag
import nltk
from collections import Counter
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, UTC

nltk.download('punkt')
nltk.download('punkt_tab')
nltk.download('averaged_perceptron_tagger')
nltk.download('averaged_perceptron_tagger_eng')
nltk.download('stopwords')
nltk.download('vader_lexicon')

db = SQLAlchemy()

class PitchDeckParser:
    def __init__(self, sia=None):
        self.sia = sia if sia else SentimentIntensityAnalyzer()
        self.stop_words = set(stopwords.words('english'))

    def parse_pdf(self, file_path):
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = pypdf.PdfReader(file)
                content = ""
                for page in pdf_reader.pages:
                    page_text = page.extract_text().strip()
                    if page_text:
                        content += page_text + "\n"
                return content.rstrip(), len(pdf_reader.pages)
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

    def detect_document_type(self, text):
        text_lower = text.lower()
        pitch_deck_keywords = ['problem is', 'solution is', 'market is', 'our problem', 'our solution']
        if any(keyword in text_lower for keyword in pitch_deck_keywords):
            return 'pitch_deck'

        resume_keywords = ['objective', 'summary', 'profile', 'experience', 'education', 'skills', 'certifications']
        for keyword in resume_keywords:
            if re.search(rf'^{keyword}\s*:|^\s*{keyword}\s*\n', text_lower, re.MULTILINE):
                return 'resume'

        return 'generic'

    def extract_section(self, lines, start_keyword, max_lines=5):  # Increased max_lines
        for i, line in enumerate(lines):
            if start_keyword in line.lower():  # Case-insensitive match
                section_lines = [line.strip()]
                for j in range(1, max_lines + 1):
                    if i + j < len(lines):
                        next_line = lines[i + j].strip()
                        if not next_line or next_line.lower().startswith(('objective', 'summary', 'profile', 'experience', 'skills', 'education', 'certifications')):
                            break
                        section_lines.append(next_line)
                    else:
                        break
                return re.sub(r'\s+', ' ', ' '.join(section_lines))
        return None

    def extract_key_phrases(self, text, top_n=5):
        words = word_tokenize(text.lower())
        words = [word for word in words if word.isalnum() and word not in self.stop_words]
        tagged_words = pos_tag(words)
        phrases = []
        current_phrase = []
        for word, tag in tagged_words:
            if tag.startswith(('NN', 'JJ')):
                current_phrase.append(word)
            else:
                if current_phrase:
                    phrases.append(' '.join(current_phrase))
                    current_phrase = []
        if current_phrase:
            phrases.append(' '.join(current_phrase))

        phrase_counts = Counter(phrases)
        key_phrases = [phrase for phrase, count in phrase_counts.most_common(top_n) if len(phrase.split()) > 1]
        return key_phrases if key_phrases else ["No key phrases identified"]

    def extract_summary(self, text, max_sentences=3):
        sentences = sent_tokenize(text.strip())
        if not sentences:
            return "No content to summarize."

        key_phrases = self.extract_key_phrases(text, top_n=5)
        if not key_phrases:
            return ' '.join(sentences[:max_sentences]).strip()

        sentence_scores = []
        for sentence in sentences:
            score = sum(1 for phrase in key_phrases if phrase.lower() in sentence.lower())
            sentence_scores.append((sentence, score))

        sentence_scores.sort(key=lambda x: x[1], reverse=True)
        top_sentences = [sentence for sentence, score in sentence_scores[:max_sentences] if score > 0]
        if not top_sentences:
            top_sentences = sentences[:max_sentences]
        top_sentences = sorted(top_sentences, key=lambda s: sentences.index(s))
        return ' '.join(top_sentences).strip()

    def analyze_content(self, text):
        info = {
            'upload_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'word_count': len(text.split()),
            'char_count': len(text.replace('\n', ''))
        }
        sentiment = self.sia.polarity_scores(text)
        info['sentiment_score'] = sentiment['compound']
        info['sentiment_type'] = 'Positive' if sentiment['compound'] > 0.05 else \
            'Negative' if sentiment['compound'] < -0.05 else 'Neutral'

        doc_type = self.detect_document_type(text.lower())
        info['document_type'] = doc_type
        lines = text.lower().split('\n')

        if doc_type == 'pitch_deck':
            for line in lines:
                if 'problem' in line:
                    info['problem'] = line.strip()
                elif 'solution' in line:
                    info['solution'] = line.strip()
                elif 'market' in line:
                    info['market'] = line.strip()
        elif doc_type == 'resume':
            info['problem'] = self.extract_section(lines, 'objective') or \
                              self.extract_section(lines, 'summary') or \
                              self.extract_section(lines, 'profile')
            info['experience'] = self.extract_section(lines, 'experience')
            info['skills'] = self.extract_section(lines, 'skills')
        else:
            info['key_phrases'] = self.extract_key_phrases(text, top_n=5)
            info['summary'] = self.extract_summary(text)

        if 'problem' not in info or not info['problem']:
            info['problem'] = self.extract_summary(text)

        return info

class PitchDeck(db.Model):
    __tablename__ = 'pitch_decks'

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    upload_date = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    content = db.Column(db.Text)
    slide_count = db.Column(db.Integer)
    status = db.Column(db.String(50))
    word_count = db.Column(db.Integer)
    char_count = db.Column(db.Integer)
    sentiment_score = db.Column(db.Float)
    sentiment_type = db.Column(db.String(50))
    document_type = db.Column(db.String(50))
    problem = db.Column(db.Text)
    solution = db.Column(db.Text)
    market = db.Column(db.Text)
    experience = db.Column(db.Text)
    skills = db.Column(db.Text)
    summary = db.Column(db.Text)
    key_phrases = db.Column(db.Text)

    def __init__(self, filename, content, slide_count, analysis, status='processed'):
        self.filename = filename
        self.content = content
        self.slide_count = slide_count
        self.status = status
        self.word_count = analysis['word_count']
        self.char_count = analysis['char_count']
        self.sentiment_score = analysis['sentiment_score']
        self.sentiment_type = analysis['sentiment_type']
        self.document_type = analysis.get('document_type')
        self.problem = analysis.get('problem')
        self.solution = analysis.get('solution')
        self.market = analysis.get('market')
        self.experience = analysis.get('experience')
        self.skills = analysis.get('skills')
        self.summary = analysis.get('summary')
        self.key_phrases = ', '.join(analysis.get('key_phrases', [])) if analysis.get('key_phrases') else None

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
