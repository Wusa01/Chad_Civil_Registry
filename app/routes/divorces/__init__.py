from flask import Blueprint

# 1. تعريف الـ Blueprint أولاً
divorces_bp = Blueprint('divorces', __name__)

# 2. استيراد المسارات من ملف routes.py لربطها بالـ Blueprint
from . import routes
