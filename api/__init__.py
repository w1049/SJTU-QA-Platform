from flask import Blueprint

api_bp = Blueprint('api_bp', __name__)
from .views import api

api.init_app(api_bp)
