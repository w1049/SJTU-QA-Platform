from flask import Blueprint

auth_bp = Blueprint('auth_bp', __name__)
from . import views
