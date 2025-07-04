import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'change-me')
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URI', f"sqlite:///{os.path.join(basedir, 'intranet.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
