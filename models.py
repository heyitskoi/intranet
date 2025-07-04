from datetime import datetime
from flask_sqlalchemy import SQLAlchemy


# SQLAlchemy instance used across the app
# app.py will import this instance
# before initializing it with the Flask app

db = SQLAlchemy()


class Department(db.Model):
    """Company department."""

    __tablename__ = 'departments'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), unique=True, nullable=False)

    users = db.relationship('User', back_populates='department')

    def __repr__(self) -> str:  # pragma: no cover - simple representation
        return f'<Department {self.name}>'


class Role(db.Model):
    """User role."""

    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), unique=True, nullable=False)

    users = db.relationship('User', back_populates='role')

    def __repr__(self) -> str:  # pragma: no cover - simple representation
        return f'<Role {self.name}>'


class User(db.Model):
    """Application user."""

    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))

    department = db.relationship('Department', back_populates='users')
    role = db.relationship('Role', back_populates='users')
    audit_logs = db.relationship('AuditLog', back_populates='user')

    # Flask-Login interface ------------------------------
    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def is_active(self) -> bool:
        return True

    @property
    def is_anonymous(self) -> bool:
        return False

    def get_id(self) -> str:
        return str(self.id)

    def __repr__(self) -> str:  # pragma: no cover - simple representation
        return f'<User {self.username}>'


class AuditLog(db.Model):
    """Record of user actions."""

    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', back_populates='audit_logs')

    def __repr__(self) -> str:  # pragma: no cover - simple representation
        return f'<AuditLog {self.user_id} {self.action}>'
