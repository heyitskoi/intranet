from flask import Flask
from flask_login import LoginManager, login_required, current_user

from config import Config, BASE_DIR
from models import db, User, Department, Role, AuditLog

# extensions

login_manager = LoginManager()


def create_app(config_class=Config):
    app = Flask(__name__, instance_path=BASE_DIR)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from auth import auth_bp
    app.register_blueprint(auth_bp)

    from blueprints.standby import standby_bp
    app.register_blueprint(standby_bp)

    # Ensure standby directories exist
    from blueprints.standby.config import ensure_directories
    ensure_directories()

    @app.route('/dashboard')
    @login_required
    def dashboard():
        return (
            f"Welcome {current_user.username} from Department {current_user.department_id}"
        )

    return app

app = create_app()

if __name__ == '__main__':
    app.run()
