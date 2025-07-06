"""
Migration to create future_rotation_plans table.
This table stores planned future rotation patterns that will be applied after the current cycle ends.
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
import os
import sys

# Add the parent directory to the path so we can import the app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import db

def migrate_create_future_rotation_plans_table():
    """Create future_rotation_plans table."""
    app = create_app()
    
    with app.app_context():
        print("\nCreating future_rotation_plans table...")
        print("=" * 60)
        
        try:
            # Create the future_rotation_plans table
            db.session.execute(text("""
                CREATE TABLE future_rotation_plans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    department_id INTEGER NOT NULL,
                    rotation_order TEXT NOT NULL,
                    start_date DATE NOT NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    created_by_id INTEGER NOT NULL,
                    notes TEXT,
                    FOREIGN KEY (department_id) REFERENCES departments(id),
                    FOREIGN KEY (created_by_id) REFERENCES users(id)
                )
            """))
            
            db.session.commit()
            print("✓ Successfully created future_rotation_plans table")
            
            # Create an index on department_id and start_date for better performance
            db.session.execute(text("""
                CREATE INDEX idx_future_rotation_plans_dept_date 
                ON future_rotation_plans(department_id, start_date)
            """))
            
            db.session.commit()
            print("✓ Successfully created index on future_rotation_plans table")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error during migration: {e}")
            raise

if __name__ == '__main__':
    migrate_create_future_rotation_plans_table() 