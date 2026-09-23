from app import db, login_manager, bcrypt
from flask_login import UserMixin
from datetime import datetime, timedelta
import pyotp
import secrets


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id         = db.Column(db.Integer, primary_key=True)
    username   = db.Column(db.Text, unique=True, nullable=False)
    email      = db.Column(db.Text, unique=True, nullable=True)
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

    # ── استعادة كلمة المرور (كود مكوَّن من 8 أرقام) ────────
    reset_code_hash    = db.Column(db.Text, nullable=True)
    reset_code_expires = db.Column(db.DateTime, nullable=True)

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

    # ── استعادة كلمة المرور عبر البريد الإلكتروني (كود 8 أرقام) ──
    def generate_reset_code(self, expires_minutes=15):
        """
        توليد كود من 8 أرقام، حفظ نسخة مُشفَّرة (هاش) منه فقط في القاعدة،
        وإرجاع الكود الصريح ليُرسَل عبر البريد. الكود صالح لمدة محدودة
        ويُحذف تلقائياً بعد أول استخدام ناجح.
        """
        code = f'{secrets.randbelow(100_000_000):08d}'
        self.reset_code_hash = bcrypt.generate_password_hash(code).decode('utf-8')
        self.reset_code_expires = datetime.utcnow() + timedelta(minutes=expires_minutes)
        return code

    def verify_reset_code(self, code):
        """التحقق من صحة الكود وعدم انتهاء صلاحيته"""
        if not self.reset_code_hash or not self.reset_code_expires:
            return False
        if datetime.utcnow() > self.reset_code_expires:
            return False
        return bcrypt.check_password_hash(self.reset_code_hash, code)

    def clear_reset_code(self):
        self.reset_code_hash = None
        self.reset_code_expires = None

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
            'email':        self.email,
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
