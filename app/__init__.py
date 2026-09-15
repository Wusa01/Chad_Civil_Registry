from flask import Flask, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from config import config

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
bcrypt = Bcrypt()


def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'يرجى تسجيل الدخول أولاً'

    # تسجيل Blueprints
    from app.routes.auth      import auth_bp
    from app.routes.births    import births_bp
    from app.routes.marriages import marriages_bp
    from app.routes.divorces  import divorces_bp
    from app.routes.deaths    import deaths_bp
    from app.routes.documents import documents_bp
    from app.routes.reports   import reports_bp
    from app.routes.admin     import admin_bp
    from app.routes.citizen   import citizen_bp
    from app.routes.backup    import backup_bp 
    from app.routes.archive   import archive_bp  

    app.register_blueprint(auth_bp,      url_prefix='/auth')
    app.register_blueprint(births_bp,    url_prefix='/births')
    app.register_blueprint(marriages_bp, url_prefix='/marriages')
    app.register_blueprint(divorces_bp,  url_prefix='/divorces')
    app.register_blueprint(deaths_bp,    url_prefix='/deaths')
    app.register_blueprint(documents_bp, url_prefix='/documents')
    app.register_blueprint(reports_bp,   url_prefix='/reports')
    app.register_blueprint(admin_bp,     url_prefix='/admin')
    app.register_blueprint(citizen_bp,   url_prefix='/citizen')
    app.register_blueprint(backup_bp,    url_prefix='/backup')
    app.register_blueprint(archive_bp,   url_prefix='/archive') 

    @app.context_processor
    def inject_lang():
        lang = session.get('lang', 'ar')
        return dict(lang=lang)

    return app
