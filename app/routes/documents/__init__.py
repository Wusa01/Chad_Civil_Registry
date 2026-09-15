from flask import Blueprint

documents_bp = Blueprint('documents', __name__)

from app.routes.documents import routes
