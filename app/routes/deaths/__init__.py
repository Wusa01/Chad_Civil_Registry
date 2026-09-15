from flask import Blueprint

deaths_bp = Blueprint('deaths', __name__)

from app.routes.deaths import routes
