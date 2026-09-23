from flask import redirect, url_for
from app import create_app, db
from app.models.user import User
from app.models.center import Center

app = create_app('development')

@app.route('/')
def index():
    return redirect(url_for('auth.login'))

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Center': Center}

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
