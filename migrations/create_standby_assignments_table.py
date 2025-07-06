#!/usr/bin/env python3
"""
Migration script to create the StandbyAssignment table.
This separates actual assignments from the rotation pattern configuration.
"""

import os
import sys
from datetime import datetime, timedelta
from sqlalchemy import text

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from models import User, StandbyMember, StandbyOverride, StandbyAssignment, StandbyDurationConfig, Department

def create_standby_assignments_table():
    """Create the StandbyAssignment table and migrate existing data."""
    app = create_app()
    
    with app.app_context():
        print("Creating StandbyAssignment table...")
        print("=" * 50)
        
        # Create the new table
        try:
            # Create the table using raw SQL for better control
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS standby_assignments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    department_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    date DATE NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (department_id) REFERENCES departments (id),
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    UNIQUE (department_id, date)
                )
            """))
            
            # Create index for better performance
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_standby_assignments_date 
                ON standby_assignments (date)
            """))
            
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_standby_assignments_department_date 
                ON standby_assignments (department_id, date)
            """))
            
            db.session.commit()
            print("✓ StandbyAssignment table created successfully")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error creating table: {e}")
            raise

def migrate_existing_assignments():
    """Migrate existing rotation data to assignments for the past 30 days."""
    app = create_app()
    
    with app.app_context():
        print("\nMigrating existing rotation data to assignments...")
        print("=" * 50)
        
        try:
            # Get all departments with standby configurations
            departments = Department.query.all()
            
            total_assignments = 0
            
            for department in departments:
                print(f"Processing department: {department.name}")
                
                # Get department configuration
                config = StandbyDurationConfig.query.filter_by(department_id=department.id).first()
                if not config:
                    print(f"  ⚠ No configuration found for {department.name}, skipping")
                    continue
                
                # Get active standby members for this department
                active_members = StandbyMember.query.filter_by(active=True).join(User).filter(
                    User.department_id == department.id
                ).order_by(StandbyMember.rotation_order).all()
                
                if not active_members:
                    print(f"  ⚠ No active standby members found for {department.name}")
                    continue
                
                # Generate assignments for the past 30 days
                end_date = datetime.now().date()
                start_date = end_date - timedelta(days=30)
                
                current_date = start_date
                member_index = 0
                
                while current_date <= end_date:
                    # Check if assignment already exists
                    existing = StandbyAssignment.query.filter_by(
                        department_id=department.id,
                        date=current_date
                    ).first()
                    
                    if not existing:
                        # Check for override first
                        override = StandbyOverride.query.filter_by(date=current_date).first()
                        
                        if override:
                            # Use override user if they're still active in this department
                            override_member = StandbyMember.query.filter_by(
                                user_id=override.user_id,
                                active=True
                            ).join(User).filter(User.department_id == department.id).first()
                            
                            if override_member:
                                assignment = StandbyAssignment(
                                    department_id=department.id,
                                    user_id=override.user_id,
                                    date=current_date
                                )
                                db.session.add(assignment)
                                total_assignments += 1
                        else:
                            # Use rotation pattern
                            if active_members:
                                current_member = active_members[member_index % len(active_members)]
                                assignment = StandbyAssignment(
                                    department_id=department.id,
                                    user_id=current_member.user_id,
                                    date=current_date
                                )
                                db.session.add(assignment)
                                total_assignments += 1
                    
                    # Move to next day and next person in rotation
                    current_date += timedelta(days=1)
                    member_index += 1
                
                print(f"  ✓ Generated assignments for {department.name}")
            
            db.session.commit()
            print(f"\n✓ Successfully migrated {total_assignments} assignments")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error migrating assignments: {e}")
            raise

def generate_future_assignments():
    """Generate assignments for the next 90 days."""
    app = create_app()
    
    with app.app_context():
        print("\nGenerating future assignments...")
        print("=" * 50)
        
        try:
            departments = Department.query.all()
            total_assignments = 0
            
            for department in departments:
                print(f"Processing department: {department.name}")
                
                # Get department configuration
                config = StandbyDurationConfig.query.filter_by(department_id=department.id).first()
                if not config:
                    print(f"  ⚠ No configuration found for {department.name}, skipping")
                    continue
                
                # Get active standby members for this department
                active_members = StandbyMember.query.filter_by(active=True).join(User).filter(
                    User.department_id == department.id
                ).order_by(StandbyMember.rotation_order).all()
                
                if not active_members:
                    print(f"  ⚠ No active standby members found for {department.name}")
                    continue
                
                # Generate assignments for the next 90 days
                start_date = datetime.now().date() + timedelta(days=1)
                end_date = start_date + timedelta(days=90)
                
                current_date = start_date
                member_index = 0
                
                while current_date <= end_date:
                    # Check if assignment already exists
                    existing = StandbyAssignment.query.filter_by(
                        department_id=department.id,
                        date=current_date
                    ).first()
                    
                    if not existing:
                        # Check for override first
                        override = StandbyOverride.query.filter_by(date=current_date).first()
                        
                        if override:
                            # Use override user if they're still active in this department
                            override_member = StandbyMember.query.filter_by(
                                user_id=override.user_id,
                                active=True
                            ).join(User).filter(User.department_id == department.id).first()
                            
                            if override_member:
                                assignment = StandbyAssignment(
                                    department_id=department.id,
                                    user_id=override.user_id,
                                    date=current_date
                                )
                                db.session.add(assignment)
                                total_assignments += 1
                        else:
                            # Use rotation pattern
                            if active_members:
                                current_member = active_members[member_index % len(active_members)]
                                assignment = StandbyAssignment(
                                    department_id=department.id,
                                    user_id=current_member.user_id,
                                    date=current_date
                                )
                                db.session.add(assignment)
                                total_assignments += 1
                    
                    # Move to next day and next person in rotation
                    current_date += timedelta(days=1)
                    member_index += 1
                
                print(f"  ✓ Generated future assignments for {department.name}")
            
            db.session.commit()
            print(f"\n✓ Successfully generated {total_assignments} future assignments")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error generating future assignments: {e}")
            raise

if __name__ == '__main__':
    print("StandbyAssignment Migration Script")
    print("=" * 50)
    
    try:
        # Step 1: Create the table
        create_standby_assignments_table()
        
        # Step 2: Migrate existing data
        migrate_existing_assignments()
        
        # Step 3: Generate future assignments
        generate_future_assignments()
        
        print("\n🎉 Migration completed successfully!")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        sys.exit(1) 