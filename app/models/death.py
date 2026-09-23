from app import db
from datetime import datetime


class Death(db.Model):
    __tablename__ = 'deaths'

    id                 = db.Column(db.Integer, primary_key=True)
    certificate_number = db.Column(db.Text, unique=True, nullable=False)
    center_id          = db.Column(db.Integer, db.ForeignKey('centers.id'), nullable=False)
    registration_date  = db.Column(db.Date, nullable=False)

    deceased_full_name  = db.Column(db.Text, nullable=False)
    deceased_gender     = db.Column(db.Text, nullable=False)
    deceased_birth_date = db.Column(db.Date, nullable=True)
    deceased_age        = db.Column(db.Integer, nullable=True)
    usual_residence     = db.Column(db.Text, nullable=False)

    death_date       = db.Column(db.Date, nullable=False)
    death_place      = db.Column(db.Text, nullable=False)
    death_place_type = db.Column(db.Text, nullable=False)
    cause_of_death   = db.Column(db.Text, nullable=False)
    certifier_name   = db.Column(db.Text, nullable=False)

    birth_ref_id  = db.Column(db.Integer, db.ForeignKey('births.id'), nullable=True)

    # الشهود
    witness1_name     = db.Column(db.Text, nullable=True)
    witness1_id       = db.Column(db.Text, nullable=True)
    witness1_relation = db.Column(db.Text, nullable=True)
    witness2_name     = db.Column(db.Text, nullable=True)
    witness2_id       = db.Column(db.Text, nullable=True)
    witness2_relation = db.Column(db.Text, nullable=True)

    civil_officer = db.Column(db.Text, nullable=False)
    registered_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    notes         = db.Column(db.Text, nullable=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at    = db.Column(db.DateTime, onupdate=datetime.utcnow)

    documents = db.relationship(
        'Document', backref='death_ref',
        primaryjoin="and_(Document.ref_id==Death.id, Document.doc_type=='death')",
        foreign_keys='Document.ref_id', lazy='dynamic',
        overlaps="birth_ref,divorce_ref,marriage_ref,documents"
    )

    def __repr__(self):
        return f'<Death {self.certificate_number} - {self.deceased_full_name}>'

    def to_dict(self):
        return {
            'id':                  self.id,
            'certificate_number':  self.certificate_number,
            'deceased_full_name':  self.deceased_full_name,
            'deceased_gender':     self.deceased_gender,
            'death_date':          str(self.death_date),
            'death_place':         self.death_place,
            'cause_of_death':      self.cause_of_death,
            'certifier_name':      self.certifier_name,
            'witness1_name':       self.witness1_name,
            'witness1_id':         self.witness1_id,
            'witness1_relation':   self.witness1_relation,
            'witness2_name':       self.witness2_name,
            'witness2_id':         self.witness2_id,
            'witness2_relation':   self.witness2_relation,
            'civil_officer':       self.civil_officer,
            'registration_date':   str(self.registration_date),
        }
