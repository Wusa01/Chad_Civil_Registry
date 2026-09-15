from app import db
from datetime import datetime


class Marriage(db.Model):
    __tablename__ = 'marriages'

    id                 = db.Column(db.Integer, primary_key=True)
    certificate_number = db.Column(db.Text, unique=True, nullable=False)
    center_id          = db.Column(db.Integer, db.ForeignKey('centers.id'), nullable=False)
    registration_date  = db.Column(db.Date, nullable=True)
    marriage_date      = db.Column(db.Date, nullable=False)
    marriage_place     = db.Column(db.Text, nullable=False)

    husband_full_name   = db.Column(db.Text, nullable=False)
    husband_birth_date  = db.Column(db.Date, nullable=False)
    husband_birth_place = db.Column(db.Text, nullable=False)
    husband_profession  = db.Column(db.Text, nullable=False)
    husband_nationality = db.Column(db.Text, nullable=False)
    husband_id_number   = db.Column(db.Text, nullable=False)
    husband_father_name = db.Column(db.Text, nullable=False)
    husband_mother_name = db.Column(db.Text, nullable=False)

    wife_full_name   = db.Column(db.Text, nullable=False)
    wife_birth_date  = db.Column(db.Date, nullable=False)
    wife_birth_place = db.Column(db.Text, nullable=False)
    wife_profession  = db.Column(db.Text, nullable=False)
    wife_nationality = db.Column(db.Text, nullable=False)
    wife_id_number   = db.Column(db.Text, nullable=False)
    wife_father_name = db.Column(db.Text, nullable=False)
    wife_mother_name = db.Column(db.Text, nullable=False)

    marriage_type    = db.Column(db.Text, nullable=False, default='monogamy')
    dowry_mentioned  = db.Column(db.Boolean, default=False)
    dowry_amount     = db.Column(db.Float, nullable=True)
    age_dispensation = db.Column(db.Boolean, default=False)

    # الشهود
    witness1_name     = db.Column(db.Text, nullable=False)
    witness1_id       = db.Column(db.Text, nullable=False)
    witness1_relation = db.Column(db.Text, nullable=True)
    witness2_name     = db.Column(db.Text, nullable=False)
    witness2_id       = db.Column(db.Text, nullable=False)
    witness2_relation = db.Column(db.Text, nullable=True)

    civil_officer = db.Column(db.Text, nullable=False)
    registered_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at    = db.Column(db.DateTime, onupdate=datetime.utcnow)

    documents = db.relationship(
        'Document', backref='marriage_ref',
        primaryjoin="and_(Document.ref_id==Marriage.id, Document.doc_type=='marriage')",
        foreign_keys='Document.ref_id', lazy='dynamic',
        overlaps="birth_ref,death_ref,divorce_ref,documents"
    )

    def __repr__(self):
        return f'<Marriage {self.certificate_number}>'

    def to_dict(self):
        return {
            'id':                 self.id,
            'certificate_number': self.certificate_number,
            'husband_full_name':  self.husband_full_name,
            'wife_full_name':     self.wife_full_name,
            'marriage_date':      str(self.marriage_date),
            'marriage_place':     self.marriage_place,
            'witness1_name':      self.witness1_name,
            'witness1_id':        self.witness1_id,
            'witness1_relation':  self.witness1_relation,
            'witness2_name':      self.witness2_name,
            'witness2_id':        self.witness2_id,
            'witness2_relation':  self.witness2_relation,
            'civil_officer':      self.civil_officer,
        }
