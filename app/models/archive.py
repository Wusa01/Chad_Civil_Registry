"""
archive.py — نموذج الأرشفة الرقمية للسجلات التاريخية الورقية
جمهورية تشاد — نظام الحالة المدنية
"""

from app import db
from datetime import datetime


class ArchiveRecord(db.Model):
    __tablename__ = 'archive_records'

    id = db.Column(db.Integer, primary_key=True)

    # ── تصنيف الوثيقة ─────────────────────────────────────
    doc_type = db.Column(db.Text, nullable=False)
    # birth / marriage / death / divorce / other

    doc_subtype = db.Column(db.Text, nullable=True)
    # مثال: شهادة ميلاد / عقد زواج ديني / ...

    # ── بيانات الوثيقة الورقية الأصلية ───────────────────
    original_number    = db.Column(db.Text, nullable=True)   # الرقم على الورقة
    original_date      = db.Column(db.Date, nullable=True)   # تاريخ الوثيقة الأصلية
    original_year      = db.Column(db.Integer, nullable=True) # السنة (للبحث السريع)
    original_center    = db.Column(db.Text, nullable=True)   # المركز المُصدِر الأصلي
    original_region    = db.Column(db.Text, nullable=True)   # المنطقة

    # ── الشخص الرئيسي ─────────────────────────────────────
    person_name        = db.Column(db.Text, nullable=False)   # اسم صاحب الوثيقة
    person_name_fr     = db.Column(db.Text, nullable=True)    # الاسم بالفرنسية
    person_birth_year  = db.Column(db.Integer, nullable=True) # سنة الميلاد التقريبية
    father_name        = db.Column(db.Text, nullable=True)
    mother_name        = db.Column(db.Text, nullable=True)

    # ── بيانات الأرشفة الرقمية ────────────────────────────
    scan_file          = db.Column(db.Text, nullable=True)
    # مسار الصورة الممسوحة داخل مجلد static/archive_scans/
    scan_quality       = db.Column(db.Text, nullable=True, default='medium')
    # good / medium / poor

    transcription      = db.Column(db.Text, nullable=True)
    # النص المُنسَّخ يدوياً من الوثيقة الورقية

    transcription_status = db.Column(db.Text, nullable=False, default='pending')
    # pending / in_progress / done / verified

    # ربط بسجل رقمي موجود إن وُجد
    linked_doc_type    = db.Column(db.Text, nullable=True)
    linked_record_id   = db.Column(db.Integer, nullable=True)
    # يشير إلى birth.id أو marriage.id ... إلخ

    # ── مصدر التوثيق ──────────────────────────────────────
    source_type        = db.Column(db.Text, nullable=False, default='paper')
    # paper / microfilm / photo / other

    register_volume    = db.Column(db.Text, nullable=True)   # رقم السجل/المجلد
    register_page      = db.Column(db.Text, nullable=True)   # رقم الصفحة
    register_entry     = db.Column(db.Text, nullable=True)   # رقم القيد

    # ── الحالة والتحكم ────────────────────────────────────
    center_id          = db.Column(db.Integer, db.ForeignKey('centers.id'), nullable=True)
    digitized_by       = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    verified_by        = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    verified_at        = db.Column(db.DateTime, nullable=True)

    notes              = db.Column(db.Text, nullable=True)
    is_confidential    = db.Column(db.Boolean, default=False)
    created_at         = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at         = db.Column(db.DateTime, onupdate=datetime.utcnow)

    # ── العلاقات ──────────────────────────────────────────
    center       = db.relationship('Center',  foreign_keys=[center_id],
                                   backref='archive_records')
    digitizer    = db.relationship('User',    foreign_keys=[digitized_by],
                                   backref='digitized_records')
    verifier     = db.relationship('User',    foreign_keys=[verified_by],
                                   backref='verified_records')

    def __repr__(self):
        return f'<Archive {self.doc_type} — {self.person_name} ({self.original_year})>'

    def to_dict(self):
        return {
            'id':                   self.id,
            'doc_type':             self.doc_type,
            'original_number':      self.original_number,
            'original_date':        str(self.original_date) if self.original_date else None,
            'original_year':        self.original_year,
            'person_name':          self.person_name,
            'transcription_status': self.transcription_status,
            'scan_file':            self.scan_file,
            'created_at':           str(self.created_at),
        }

    @property
    def status_label_ar(self):
        return {
            'pending':     'في الانتظار',
            'in_progress': 'جارٍ النسخ',
            'done':        'منسوخ',
            'verified':    'مُتحقَّق منه',
        }.get(self.transcription_status, self.transcription_status)

    @property
    def status_color(self):
        return {
            'pending':     'secondary',
            'in_progress': 'warning',
            'done':        'info',
            'verified':    'success',
        }.get(self.transcription_status, 'secondary')

    @property
    def doc_type_label_ar(self):
        return {
            'birth':    'ميلاد',
            'marriage': 'زواج',
            'death':    'وفاة',
            'divorce':  'طلاق',
            'other':    'أخرى',
        }.get(self.doc_type, self.doc_type)
