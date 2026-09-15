from app import db
from datetime import datetime


class CitizenRequest(db.Model):
    __tablename__ = 'citizen_requests'

    id               = db.Column(db.Integer, primary_key=True)
    citizen_id       = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    center_id        = db.Column(db.Integer, db.ForeignKey('centers.id'), nullable=True)

    # نوع الطلب
    request_type     = db.Column(db.Text, nullable=False)
    # new_certificate / reissue / correction

    # نوع الوثيقة
    doc_type         = db.Column(db.Text, nullable=False)
    # birth / marriage / death / divorce

    # رقم الشهادة المرجعية (للإصدار أو التصحيح)
    # يُدخله المواطن عند طلب reissue أو correction
    ref_certificate_number = db.Column(db.Text, nullable=True)

    # حالة الطلب
    status           = db.Column(db.Text, nullable=False, default='pending')
    # pending / approved / rejected

    rejection_reason = db.Column(db.Text, nullable=True)

    # بيانات الطلب المُدخلة من المواطن (JSON)
    request_data     = db.Column(db.Text, nullable=True)

    # صلة القرابة
    relationship     = db.Column(db.Text, nullable=True)

    # الموظف الذي راجع الطلب
    reviewed_by      = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    reviewed_at      = db.Column(db.DateTime, nullable=True)

    # الوثيقة المُصدَرة بعد القبول
    issued_doc_id    = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=True)

    created_at       = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at       = db.Column(db.DateTime, onupdate=datetime.utcnow)

    # العلاقات
    citizen   = db.relationship('User', foreign_keys=[citizen_id],
                                backref='citizen_requests')
    reviewer  = db.relationship('User', foreign_keys=[reviewed_by])
    center    = db.relationship('Center', foreign_keys=[center_id])

    def __repr__(self):
        return f'<CitizenRequest {self.id} — {self.doc_type} — {self.status}>'

    def to_dict(self):
        return {
            'id':                    self.id,
            'doc_type':              self.doc_type,
            'request_type':          self.request_type,
            'ref_certificate_number': self.ref_certificate_number,
            'status':                self.status,
            'created_at':            str(self.created_at),
        }
