from flask import Blueprint

archive_bp = Blueprint('archive', __name__)

from app.routes.archive import routes
