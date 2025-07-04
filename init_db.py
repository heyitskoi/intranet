#!/usr/bin/env python3
"""
Database initialization script.
This script creates the database in the project root with all necessary tables.
"""

import os
from app import create_app, db
from models import Department, Role, User, AuditLog

def init_database():
    """Initialize the database with tables."""
    app = create_app()
    
    with app.app_context():
        db_uri = app.config['SQLALCHEMY_DATABASE_URI']
        print(f"SQLALCHEMY_DATABASE_URI: {db_uri}")
        if db_uri.startswith('sqlite:///'):
            db_path = db_uri.replace('sqlite:///', '')
            print(f"Resolved SQLite DB path: {os.path.abspath(db_path)}")
        
        # Ensure all models are imported and registered
        print("Models to be created:")
        print(f"  - {Department.__name__}")
        print(f"  - {Role.__name__}")
        print(f"  - {User.__name__}")
        print(f"  - {AuditLog.__name__}")
        
        # Create all tables
        db.create_all()
        print("Database tables created successfully!")
        
        # Verify tables were created by checking the database
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"Tables in database: {tables}")
        
        # Check if we need to add some initial data
        if not Department.query.first():
            # Add some default departments
            departments = [
                Department(name='IT'),
                Department(name='HR'),
                Department(name='Finance'),
                Department(name='Marketing'),
                Department(name='Operations')
            ]
            db.session.add_all(departments)
            
        if not Role.query.first():
            # Add some default roles
            roles = [
                Role(name='Admin'),
                Role(name='Manager'),
                Role(name='Employee'),
                Role(name='Guest')
            ]
            db.session.add_all(roles)
            
        db.session.commit()
        print("Initial data added successfully!")

if __name__ == '__main__':
    init_database() 