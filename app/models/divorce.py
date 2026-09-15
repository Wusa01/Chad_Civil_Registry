from app import db
from datetime import datetime


class Divorce(db.Model):
    __tablename__ = 'divorces'

    id                 = db.Column(db.Integer, primary_key=True)
    certificate_number = db.Column(db.Text, unique=True, nullable=False)
    center_id          = db.Column(db.Integer, db.ForeignKey('centers.id'), nullable=False)
    registration_date  = db.Column(db.Date, nullable=False)

    divorce_date         = db.Column(db.Date, nullable=False)
    divorce_place        = db.Column(db.Text, nullable=False)
    divorce_type         = db.Column(db.Text, nullable=False, default='mutual')
    marriage_cert_number = db.Column(db.Text, nullable=True)
    marriage_id          = db.Column(db.Integer, db.ForeignKey('marriages.id'), nullable=True)

    husband_full_name   = db.Column(db.Text, nullable=False)
    husband_birth_date  = db.Column(db.Date, nullable=False)
    husband_birth_place = db.Column(db.Text, nullable=False)
    husband_profession  = db.Column(db.Text, nullable=False)
    husband_nationality = db.Column(db.Text, nullable=False)
    husband_id_number   = db.Column(db.Text, nullable=False)

    wife_full_name   = db.Column(db.Text, nullable=False)
    wife_birth_date  = db.Column(db.Date, nullable=False)
    wife_birth_place = db.Column(db.Text, nullable=False)
    wife_profession  = db.Column(db.Text, nullable=False)
    wife_nationality = db.Column(db.Text, nullable=False)
    wife_id_number   = db.Column(db.Text, nullable=False)

    children_count   = db.Column(db.Integer, nullable=True, default=0)
    custody_decision = db.Column(db.Text, nullable=True)

    # الشهود
    witness1_name     = db.Column(db.Text, nullable=False)
    witness1_id       = db.Column(db.Text, nullable=False)
    witness1_relation = db.Column(db.Text, nullable=True)
    witness2_name     = db.Column(db.Text, nullable=False)
    witness2_id       = db.Column(db.Text, nullable=False)
    witness2_relation = db.Column(db.Text, nullable=True)

    court_decision_number = db.Column(db.Text, nullable=True)
    court_name            = db.Column(db.Text, nullable=True)

    civil_officer = db.Column(db.Text, nullable=False)
    registered_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    notes         = db.Column(db.Text, nullable=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at    = db.Column(db.DateTime, onupdate=datetime.utcnow)

    documents = db.relationship(
        'Document', backref='divorce_ref',
        primaryjoin="and_(Document.ref_id==Divorce.id, Document.doc_type=='divorce')",
        foreign_keys='Document.ref_id', lazy='dynamic',
        overlaps="birth_ref,death_ref,marriage_ref,documents"
    )

    def __repr__(self):
        return f'<Divorce {self.certificate_number}>'

    def to_dict(self):
        return {
            'id':                 self.id,
            'certificate_number': self.certificate_number,
            'husband_full_name':  self.husband_full_name,
            'wife_full_name':     self.wife_full_name,
            'divorce_date':       str(self.divorce_date),
            'divorce_place':      self.divorce_place,
            'divorce_type':       self.divorce_type,
            'witness1_name':      self.witness1_name,
            'witness1_id':        self.witness1_id,
            'witness1_relation':  self.witness1_relation,
            'witness2_name':      self.witness2_name,
            'witness2_id':        self.witness2_id,
            'witness2_relation':  self.witness2_relation,
            'civil_officer':      self.civil_officer,
            'registration_date':  str(self.registration_date),
        }
