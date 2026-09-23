from flask import Blueprint

backup_bp = Blueprint('backup', __name__)

from app.routes.backup import routes
