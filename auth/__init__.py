from flask import Blueprint

# Blueprint for authentication routes
auth_bp = Blueprint('auth', __name__)

# Import routes to register them with the blueprint
from . import routes  # noqa: E402,F401
