from flask import Blueprint

births_bp = Blueprint('births', __name__)

from app.routes.births import routes
