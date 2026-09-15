from app import db
from datetime import datetime

class Center(db.Model):
    __tablename__ = 'centers'

    id         = db.Column(db.Integer, primary_key=True)
    name_ar    = db.Column(db.Text, nullable=False)
    name_fr    = db.Column(db.Text, nullable=False)
    region     = db.Column(db.Text, nullable=False)
    department = db.Column(db.Text, nullable=False)
    code       = db.Column(db.Text, unique=True, nullable=False)
    is_active  = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # العلاقات
    users     = db.relationship('User',     backref='center', lazy='dynamic')
    births    = db.relationship('Birth',    backref='center', lazy='dynamic')
    marriages = db.relationship('Marriage', backref='center', lazy='dynamic')
    deaths    = db.relationship('Death',    backref='center', lazy='dynamic')
    divorces  = db.relationship('Divorce',  backref='center', lazy='dynamic')

    def __repr__(self):
        return f'<Center {self.code} - {self.name_ar}>'

    def to_dict(self):
        return {
            'id':         self.id,
            'name_ar':    self.name_ar,
            'name_fr':    self.name_fr,
            'region':     self.region,
            'department': self.department,
            'code':       self.code,
            'is_active':  self.is_active
        }
