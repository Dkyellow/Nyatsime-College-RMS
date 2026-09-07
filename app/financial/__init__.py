from flask import Blueprint

financial_bp = Blueprint('financial', __name__, url_prefix='/admin/financial')

from app.financial import routes  # noqa: F401, E402
