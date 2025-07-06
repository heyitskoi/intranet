"""
Migration to add original_user_id to standby_overrides table.
This tracks who was originally assigned before an override was applied.
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

def migrate_add_original_user_to_standby_override():
    """Add original_user_id column to standby_overrides table."""
    app = create_app()
    
    with app.app_context():
        print("\nAdding original_user_id to standby_overrides table...")
        print("=" * 60)
        
        try:
            # Add the new column
            db.session.execute(text("""
                ALTER TABLE standby_overrides 
                ADD COLUMN original_user_id INTEGER 
                REFERENCES users(id)
            """))
            
            db.session.commit()
            print("✓ Successfully added original_user_id column to standby_overrides table")
            
            # Update existing overrides to have NULL for original_user_id
            # (we can't determine what the original assignment was for existing overrides)
            db.session.execute(text("""
                UPDATE standby_overrides 
                SET original_user_id = NULL 
                WHERE original_user_id IS NULL
            """))
            
            db.session.commit()
            print("✓ Updated existing overrides to have NULL original_user_id")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error during migration: {e}")
            raise

if __name__ == '__main__':
    migrate_add_original_user_to_standby_override() 