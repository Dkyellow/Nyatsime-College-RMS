from flask import Blueprint

newsletter_bp = Blueprint('newsletter', __name__, template_folder='../templates/newsletters')

from app.newsletter import routes  # noqa: E402,F401
