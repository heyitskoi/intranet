from flask import Blueprint

standby_bp = Blueprint('standby', __name__, url_prefix='/standby')

@standby_bp.route('/')
def index():
    return 'Standby Module'
