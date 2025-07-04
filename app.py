from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

from config import Config

# extensions

db = SQLAlchemy()
login_manager = LoginManager()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)

    from auth import auth_bp
    app.register_blueprint(auth_bp)

    from blueprints.standby import standby_bp
    app.register_blueprint(standby_bp)

    return app

if __name__ == '__main__':
    app = create_app()
    app.run()
