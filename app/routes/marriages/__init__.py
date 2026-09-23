from flask import Blueprint

marriages_bp = Blueprint('marriages', __name__)

from app.routes.marriages import routes
