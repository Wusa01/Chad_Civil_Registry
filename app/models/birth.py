from app import db
from datetime import datetime


class Birth(db.Model):
    __tablename__ = 'births'

    id                 = db.Column(db.Integer, primary_key=True)
    certificate_number = db.Column(db.Text, unique=True, nullable=False)
    center_id          = db.Column(db.Integer, db.ForeignKey('centers.id'), nullable=False)
    registration_date  = db.Column(db.Date, nullable=False)

    # بيانات المولود
    child_full_name = db.Column(db.Text, nullable=False)
    child_gender    = db.Column(db.Text, nullable=False)
    birth_date      = db.Column(db.Date, nullable=False)
    birth_place     = db.Column(db.Text, nullable=False)

    # بيانات الأب
    father_full_name   = db.Column(db.Text, nullable=False)
    father_birth_date  = db.Column(db.Date, nullable=True)
    father_birth_place = db.Column(db.Text, nullable=True)
    father_profession  = db.Column(db.Text, nullable=False)

    # بيانات الأم
    mother_full_name   = db.Column(db.Text, nullable=False)
    mother_birth_date  = db.Column(db.Date, nullable=True)
    mother_birth_place = db.Column(db.Text, nullable=True)
    mother_profession  = db.Column(db.Text, nullable=False)

    # الشهود
    witness1_name     = db.Column(db.Text, nullable=True)
    witness1_id       = db.Column(db.Text, nullable=True)
    witness1_relation = db.Column(db.Text, nullable=True)
    witness2_name     = db.Column(db.Text, nullable=True)
    witness2_id       = db.Column(db.Text, nullable=True)
    witness2_relation = db.Column(db.Text, nullable=True)

    # ضابط الحالة المدنية
    civil_officer = db.Column(db.Text, nullable=False)
    registered_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    notes         = db.Column(db.Text, nullable=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at    = db.Column(db.DateTime, onupdate=datetime.utcnow)

    # العلاقات
    documents = db.relationship(
        'Document', backref='birth_ref',
        primaryjoin="and_(Document.ref_id==Birth.id, Document.doc_type=='birth')",
        foreign_keys='Document.ref_id', lazy='dynamic',
        overlaps="death_ref,divorce_ref,marriage_ref,documents"
    )

    def __repr__(self):
        return f'<Birth {self.certificate_number} - {self.child_full_name}>'

    def to_dict(self):
        return {
            'id':                 self.id,
            'certificate_number': self.certificate_number,
            'child_full_name':    self.child_full_name,
            'child_gender':       self.child_gender,
            'birth_date':         str(self.birth_date),
            'birth_place':        self.birth_place,
            'father_full_name':   self.father_full_name,
            'mother_full_name':   self.mother_full_name,
            'witness1_name':      self.witness1_name,
            'witness1_id':        self.witness1_id,
            'witness1_relation':  self.witness1_relation,
            'witness2_name':      self.witness2_name,
            'witness2_id':        self.witness2_id,
            'witness2_relation':  self.witness2_relation,
            'civil_officer':      self.civil_officer,
            'registration_date':  str(self.registration_date),
        }
