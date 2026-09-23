import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'chad-civil-registry-secret-2026'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///civil_registry.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True
    LANGUAGES = ['ar', 'fr']
    DEFAULT_LANGUAGE = 'ar'

    # ── إعدادات البريد الإلكتروني (لاستعادة كلمة المرور) ──
    MAIL_SERVER        = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT          = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS       = os.environ.get('MAIL_USE_TLS', 'True') == 'True'
    MAIL_USERNAME      = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD      = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', MAIL_USERNAME)

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
