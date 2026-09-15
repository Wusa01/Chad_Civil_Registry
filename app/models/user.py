from app import db, login_manager, bcrypt
from flask_login import UserMixin
from datetime import datetime
import pyotp


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id         = db.Column(db.Integer, primary_key=True)
    username   = db.Column(db.Text, unique=True, nullable=False)
    password   = db.Column(db.Text, nullable=False)
    full_name  = db.Column(db.Text, nullable=False)
    role       = db.Column(db.Text, nullable=False)
    nni        = db.Column(db.Text, unique=True, nullable=True)
    center_id  = db.Column(db.Integer, db.ForeignKey('centers.id'), nullable=True)
    is_active  = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # ── 2FA ──────────────────────────────────────────────
    totp_secret  = db.Column(db.Text, nullable=True)   # مفتاح TOTP
    totp_enabled = db.Column(db.Boolean, default=False) # هل 2FA مفعَّل؟

    # العلاقات
    births    = db.relationship('Birth',    backref='registrar', lazy='dynamic')
    marriages = db.relationship('Marriage', backref='registrar', lazy='dynamic')
    deaths    = db.relationship('Death',    backref='registrar', lazy='dynamic')
    documents = db.relationship('Document', backref='issuer',   lazy='dynamic')
    logs      = db.relationship('AuditLog', backref='user',     lazy='dynamic')

    def set_password(self, password):
        self.password = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password, password)

    # ── دوال 2FA ─────────────────────────────────────────
    def generate_totp_secret(self):
        """توليد مفتاح TOTP جديد وحفظه"""
        self.totp_secret = pyotp.random_base32()
        return self.totp_secret

    def get_totp_uri(self):
        """رابط QR Code لتطبيق المصادقة"""
        return pyotp.totp.TOTP(self.totp_secret).provisioning_uri(
            name=self.username,
            issuer_name='السجل المدني التشادي'
        )

    def verify_totp(self, code):
        """التحقق من رمز TOTP مع نافذة زمنية ±30 ثانية"""
        if not self.totp_secret:
            return False
        totp = pyotp.TOTP(self.totp_secret)
        return totp.verify(code, valid_window=1)

    # ── دوال الأدوار ──────────────────────────────────────
    def is_admin(self):
        return self.role == 'admin'

    def is_officer(self):
        return self.role == 'officer'

    def is_region_mgr(self):
        return self.role == 'region_mgr'

    def is_citizen(self):
        return self.role == 'citizen'

    def __repr__(self):
        return f'<User {self.username} - {self.role}>'

    def to_dict(self):
        return {
            'id':           self.id,
            'username':     self.username,
            'full_name':    self.full_name,
            'role':         self.role,
            'nni':          self.nni,
            'center_id':    self.center_id,
            'is_active':    self.is_active,
            'totp_enabled': self.totp_enabled,
        }


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
