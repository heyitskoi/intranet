import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'change-me')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URI') or \
        f'sqlite:///{os.path.join(BASE_DIR, "intranet.db")}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Ensure database is created in project root, not instance folder
    INSTANCE_PATH = BASE_DIR
    # Disable Flask's default instance folder behavior
    INSTANCE_RELATIVE_CONFIG = False
