from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import JSON


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
    standby_member = db.relationship('StandbyMember', back_populates='user', uselist=False)
    overtime_logs = db.relationship('OvertimeLog', back_populates='user')

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


# Standby Module Models
class StandbyMember(db.Model):
    """Standby team member configuration."""

    __tablename__ = 'standby_members'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    color = db.Column(db.String(7), nullable=False, default='#007bff')  # Hex color code
    active = db.Column(db.Boolean, default=True, nullable=False)
    rotation_order = db.Column(db.Integer, nullable=True)  # Position in rotation (1-based)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', back_populates='standby_member')

    def __repr__(self) -> str:
        return f'<StandbyMember {self.user.username}>'


class StandbyOverride(db.Model):
    """Date overrides for standby rotation."""

    __tablename__ = 'standby_overrides'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    original_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Who was originally assigned
    reason = db.Column(db.String(255), nullable=True)  # Optional reason for override
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    user = db.relationship('User', foreign_keys=[user_id])
    original_user = db.relationship('User', foreign_keys=[original_user_id])
    created_by = db.relationship('User', foreign_keys=[created_by_id])

    def __repr__(self) -> str:
        return f'<StandbyOverride {self.date} -> {self.user.username}>'


class StandbyAssignment(db.Model):
    """Actual standby assignments for specific dates."""

    __tablename__ = 'standby_assignments'

    id = db.Column(db.Integer, primary_key=True)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    department = db.relationship('Department')
    user = db.relationship('User')

    # Composite unique constraint to prevent duplicate assignments
    __table_args__ = (
        db.UniqueConstraint('department_id', 'date', name='uq_department_date'),
    )

    def __repr__(self) -> str:
        return f'<StandbyAssignment {self.date} -> {self.user.username}>'


class OvertimeLog(db.Model):
    """Overtime log entries."""

    __tablename__ = 'overtime_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    duration_hours = db.Column(db.Float, nullable=False)
    issue_description = db.Column(db.Text, nullable=True)
    resolution_notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', back_populates='overtime_logs')

    def __repr__(self) -> str:
        return f'<OvertimeLog {self.user.username} {self.start_time.date()}>'

    @property
    def year(self) -> int:
        """Get the year of the overtime entry."""
        return self.start_time.year

    @property
    def month(self) -> int:
        """Get the month of the overtime entry."""
        return self.start_time.month


class StandbyDurationConfig(db.Model):
    """Department-specific standby configuration."""

    __tablename__ = 'standby_duration_configs'

    id = db.Column(db.Integer, primary_key=True)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False, unique=True)
    
    # Simple standby shift settings
    standby_shift_days = db.Column(db.Integer, nullable=False, default=1)  # How many days each person works on standby
    rotation_start_date = db.Column(db.Date, nullable=False, default=datetime(2024, 1, 1).date())
    
    # Overtime settings
    monthly_overtime_limit = db.Column(db.Float, nullable=False, default=40.0)
    overtime_warning_threshold = db.Column(db.Float, nullable=False, default=35.0)
    
    # Notification settings
    dashboard_refresh_interval = db.Column(db.Integer, nullable=False, default=300)  # 5 minutes
    notification_auto_dismiss = db.Column(db.Integer, nullable=False, default=10)  # 10 seconds
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    updated_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Relationships
    department = db.relationship('Department')
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    updated_by = db.relationship('User', foreign_keys=[updated_by_id])

    def __repr__(self) -> str:
        return f'<StandbyDurationConfig {self.department.name}>'


class FutureRotationPlan(db.Model):
    __tablename__ = 'future_rotation_plans'

    id = db.Column(db.Integer, primary_key=True)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    rotation_order = db.Column(db.Text, nullable=False)  # Store as JSON string
    start_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    notes = db.Column(db.Text, nullable=True)

    department = db.relationship('Department')
    created_by = db.relationship('User', foreign_keys=[created_by_id])

    def get_rotation_list(self):
        import json
        return json.loads(self.rotation_order)
