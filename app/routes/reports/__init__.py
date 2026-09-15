from flask import Blueprint

reports_bp = Blueprint('reports', __name__)

from app.routes.reports import routes
