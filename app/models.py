import re
from nltk.sentiment import SentimentIntensityAnalyzer
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
from nltk.tag import pos_tag
import nltk
from collections import Counter
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, UTC
import pdfplumber
import pptx

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
            with pdfplumber.open(file_path) as pdf:
                content = ""
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        page_text = re.sub(r'\s+', ' ', page_text.strip())
                        content += page_text + "\n"
                content = content.rstrip()
                return content, len(pdf.pages)
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
        pitch_deck_patterns = [
            r'our problem is\s+[^.\n]+',
            r'our solution is\s+[^.\n]+',
            r'the market is\s+[^.\n]+',
            r'problem is\s+[^.\n]+',
            r'solution is\s+[^.\n]+'
        ]
        for pattern in pitch_deck_patterns:
            if re.search(pattern, text_lower):
                print(f"Found pitch deck pattern: {pattern}")
                return 'pitch_deck'

        personal_sections = ['objective', 'summary', 'profile']
        other_sections = ['experience', 'education', 'skills', 'certifications']
        has_personal_section = False
        has_other_section = False

        for keyword in personal_sections:
            if re.search(rf'\b{keyword}\b(?:\s*$|\s+.*$)', text_lower, re.MULTILINE):
                print(f"Found personal section: {keyword}")
                has_personal_section = True
                break

        for keyword in other_sections:
            if re.search(rf'\b{keyword}\b(?:\s*$|\s+.*$)', text_lower, re.MULTILINE):
                print(f"Found other section: {keyword}")
                has_other_section = True
                break

        print(f"has_personal_section: {has_personal_section}, has_other_section: {has_other_section}")
        if has_personal_section and has_other_section:
            return 'resume'

        return 'generic'

    def extract_section(self, lines, start_keyword, max_lines=10):
        for i, line in enumerate(lines):
            line_lower = line.lower().strip()
            if (re.match(rf'^{start_keyword}(?:\s*|\s+&.*|\s*:.*)$', line_lower) and
                    not re.search(rf'^{start_keyword}\s+[^&:].*', line_lower)):
                section_lines = [line.strip()]
                for j in range(1, max_lines + 1):
                    if i + j < len(lines):
                        next_line = lines[i + j].strip()
                        next_line_lower = next_line.lower()
                        if not next_line or next_line_lower.startswith(('objective', 'summary', 'profile', 'experience', 'skills', 'education', 'certifications')):
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
            if tag.startswith(('NN', 'JJ', 'VB')):
                current_phrase.append(word)
            else:
                if current_phrase and len(current_phrase) > 1:
                    phrases.append(' '.join(current_phrase))
                current_phrase = []
        if current_phrase and len(current_phrase) > 1:
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
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    slide_count = db.Column(db.Integer, nullable=False)
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
    status = db.Column(db.String(50), default='pending')
    upload_date = db.Column(db.DateTime, default=lambda: datetime.now(UTC))

    def save(self, redis_client):
        self.word_count = self.analysis.get('word_count')
        self.char_count = self.analysis.get('char_count')
        self.sentiment_score = self.analysis.get('sentiment_score')
        self.sentiment_type = self.analysis.get('sentiment_type')
        self.document_type = self.analysis.get('document_type')
        self.problem = self.analysis.get('problem')
        self.solution = self.analysis.get('solution')
        self.market = self.analysis.get('market')
        self.experience = self.analysis.get('experience')
        self.skills = self.analysis.get('skills')
        self.summary = self.analysis.get('summary')
        self.key_phrases = ', '.join(self.analysis.get('key_phrases', [])) if self.analysis.get('key_phrases') else None
        self.upload_date = datetime.strptime(self.analysis.get('upload_date'), "%Y-%m-%d %H:%M:%S")

        db.session.add(self)
        db.session.commit()

        redis_client.delete('dashboard_data')