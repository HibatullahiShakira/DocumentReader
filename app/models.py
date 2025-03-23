from app import db


class Slide(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.Integer, db.ForeignKey('file.id'), nullable=False)
    slide_number = db.Column(db.Integer, nullable=False)
    title = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text)
    metadata = db.Column(db.JSON)


class File(db.model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(255), nullable=False)
    slides = db.relationship('Slide', backref='file', lazy=True)
