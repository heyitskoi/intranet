#!/usr/bin/env python3
"""
Seed script to populate the database with initial data.
This creates departments, users, roles, and standby configurations.
"""

import os
import sys
from datetime import datetime
from werkzeug.security import generate_password_hash

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from models import User, Department, Role, StandbyMember, StandbyDurationConfig

def seed_database():
    """Seed the database with initial data."""
    app = create_app()
    
    with app.app_context():
        print("Seeding database with initial data...")
        print("=" * 50)
        
        # Create tables
        db.create_all()
        
        # Step 1: Create roles
        print("1. Creating roles...")
        admin_role = Role.query.filter_by(name='Admin').first()
        if not admin_role:
            admin_role = Role(name='Admin')
            db.session.add(admin_role)
            print("   ✓ Created Admin role")
        
        user_role = Role.query.filter_by(name='User').first()
        if not user_role:
            user_role = Role(name='User')
            db.session.add(user_role)
            print("   ✓ Created User role")
        
        db.session.commit()
        
        # Step 2: Create departments
        print("\n2. Creating departments...")
        it_dept = Department.query.filter_by(name='IT').first()
        if not it_dept:
            it_dept = Department(name='IT')
            db.session.add(it_dept)
            print("   ✓ Created IT department")
        
        ops_dept = Department.query.filter_by(name='Operations').first()
        if not ops_dept:
            ops_dept = Department(name='Operations')
            db.session.add(ops_dept)
            print("   ✓ Created Operations department")
        
        db.session.commit()
        
        # Step 3: Create users
        print("\n3. Creating users...")
        users_data = [
            {
                'username': 'admin',
                'email': 'admin@company.com',
                'password': 'admin123',
                'department': it_dept,
                'role': admin_role
            },
            {
                'username': 'john_doe',
                'email': 'john.doe@company.com',
                'password': 'password123',
                'department': it_dept,
                'role': user_role
            },
            {
                'username': 'jane_smith',
                'email': 'jane.smith@company.com',
                'password': 'password123',
                'department': it_dept,
                'role': user_role
            },
            {
                'username': 'bob_wilson',
                'email': 'bob.wilson@company.com',
                'password': 'password123',
                'department': it_dept,
                'role': user_role
            },
            {
                'username': 'alice_jones',
                'email': 'alice.jones@company.com',
                'password': 'password123',
                'department': ops_dept,
                'role': user_role
            },
            {
                'username': 'charlie_brown',
                'email': 'charlie.brown@company.com',
                'password': 'password123',
                'department': ops_dept,
                'role': user_role
            }
        ]
        
        for user_data in users_data:
            existing_user = User.query.filter_by(username=user_data['username']).first()
            if not existing_user:
                user = User(
                    username=user_data['username'],
                    email=user_data['email'],
                    password_hash=generate_password_hash(user_data['password']),
                    department_id=user_data['department'].id,
                    role_id=user_data['role'].id
                )
                db.session.add(user)
                print(f"   ✓ Created user: {user_data['username']}")
        
        db.session.commit()
        
        # Step 4: Create standby members for IT department
        print("\n4. Creating standby members...")
        it_users = User.query.filter_by(department_id=it_dept.id).all()
        
        for i, user in enumerate(it_users):
            if user.username != 'admin':  # Don't add admin to standby
                existing_member = StandbyMember.query.filter_by(user_id=user.id).first()
                if not existing_member:
                    standby_member = StandbyMember(
                        user_id=user.id,
                        color=f'#{hash(user.username) % 0xFFFFFF:06x}',  # Generate color based on username
                        active=True,
                        rotation_order=i + 1
                    )
                    db.session.add(standby_member)
                    print(f"   ✓ Added {user.username} to standby roster")
        
        db.session.commit()
        
        # Step 5: Create standby duration configurations
        print("\n5. Creating standby configurations...")
        
        # IT department configuration
        it_config = StandbyDurationConfig.query.filter_by(department_id=it_dept.id).first()
        if not it_config:
            admin_user = User.query.filter_by(username='admin').first()
            it_config = StandbyDurationConfig(
                department_id=it_dept.id,
                standby_shift_days=1,
                rotation_start_date=datetime(2024, 1, 1).date(),
                monthly_overtime_limit=40.0,
                overtime_warning_threshold=35.0,
                dashboard_refresh_interval=300,
                notification_auto_dismiss=10,
                created_by_id=admin_user.id,
                updated_by_id=admin_user.id
            )
            db.session.add(it_config)
            print("   ✓ Created IT department standby configuration")
        
        # Operations department configuration
        ops_config = StandbyDurationConfig.query.filter_by(department_id=ops_dept.id).first()
        if not ops_config:
            admin_user = User.query.filter_by(username='admin').first()
            ops_config = StandbyDurationConfig(
                department_id=ops_dept.id,
                standby_shift_days=2,
                rotation_start_date=datetime(2024, 1, 1).date(),
                monthly_overtime_limit=50.0,
                overtime_warning_threshold=40.0,
                dashboard_refresh_interval=300,
                notification_auto_dismiss=10,
                created_by_id=admin_user.id,
                updated_by_id=admin_user.id
            )
            db.session.add(ops_config)
            print("   ✓ Created Operations department standby configuration")
        
        db.session.commit()
        
        print("\n🎉 Database seeding completed successfully!")
        print("=" * 50)
        print("\nDefault login credentials:")
        print("Username: admin")
        print("Password: admin123")
        print("\nOther users:")
        for user_data in users_data[1:]:  # Skip admin
            print(f"Username: {user_data['username']}")
            print(f"Password: {user_data['password']}")

if __name__ == '__main__':
    try:
        seed_database()
    except Exception as e:
        print(f"\n❌ Database seeding failed: {e}")
        sys.exit(1) 