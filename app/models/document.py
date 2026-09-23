from app import db
from datetime import datetime


class Document(db.Model):
    __tablename__ = 'documents'

    id        = db.Column(db.Integer, primary_key=True)
    doc_type  = db.Column(db.Text, nullable=False)  # birth / marriage / death / divorce
    ref_id    = db.Column(db.Integer, nullable=False)
    qr_code   = db.Column(db.Text, unique=True, nullable=False)
    issued_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    issued_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_valid  = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'<Document {self.doc_type} - {self.qr_code}>'

    def to_dict(self):
        return {
            'id':       self.id,
            'doc_type': self.doc_type,
            'ref_id':   self.ref_id,
            'qr_code':  self.qr_code,
            'issued_at': str(self.issued_at),
            'is_valid': self.is_valid,
        }
