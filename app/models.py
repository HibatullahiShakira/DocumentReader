# app/models.py
from app import db
from datetime import datetime


class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(50), nullable=False, default='PENDING')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime)
    slides = db.relationship('Slide', backref='file', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<File {self.id} - {self.filename}>'


class Slide(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.Integer, db.ForeignKey('file.id'), nullable=False)
    slide_number = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(255), nullable=True)
    content = db.Column(db.Text, nullable=True)
    metadata = db.Column(db.JSON, nullable=True)

    def __repr__(self):
        return f'<Slide {self.id} - Slide {self.slide_number}>'
