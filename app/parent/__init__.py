from flask import Blueprint

parent_bp = Blueprint('parent', __name__, template_folder='../templates/parent')

from app.parent import routes
