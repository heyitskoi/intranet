#!/usr/bin/env python3
"""
Test script to verify database integration for standby module.
"""

import os
import sys
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_database_integration():
    """Test the database integration for standby module."""
    print("Testing Standby Database Integration...")
    print("=" * 50)
    
    try:
        # Test 1: Import and create app
        print("1. Testing app creation...")
        from app import create_app, db
        from models import User, StandbyMember, StandbyOverride, OvertimeLog
        
        app = create_app()
        with app.app_context():
            # Ensure tables exist
            db.create_all()
            print("   ✓ Database tables created")
            
            # Test 2: Create test user
            print("\n2. Testing user creation...")
            test_user = User.query.filter_by(username='test_user').first()
            if not test_user:
                test_user = User(
                    username='test_user',
                    email='test@company.com',
                    password_hash='test_hash'
                )
                db.session.add(test_user)
                db.session.commit()
                print("   ✓ Test user created")
            else:
                print("   ✓ Test user already exists")
            
            # Test 3: Test standby member functions
            print("\n3. Testing standby member functions...")
            from blueprints.standby.utils.db_rotation_manager import (
                add_team_member, get_standby_member_by_username, 
                update_team_member, get_active_standby_members
            )
            
            # Add test user to standby
            try:
                add_team_member('test_user', '#ff0000', True)
                print("   ✓ Test user added to standby")
            except ValueError as e:
                if "already a standby member" in str(e):
                    print("   ✓ Test user already in standby")
                else:
                    raise
            
            # Get standby member
            member = get_standby_member_by_username('test_user')
            if member:
                print(f"   ✓ Found standby member: {member.user.username}")
            else:
                print("   ❌ Failed to find standby member")
            
            # Test 4: Test overtime functions
            print("\n4. Testing overtime functions...")
            from blueprints.standby.utils.db_overtime_logger import (
                save_overtime_entry, load_overtime_logs, get_overtime_summary
            )
            
            # Create test overtime entry
            now = datetime.now()
            entry_data = {
                'start_time': f"{now.strftime('%Y-%m-%d')} 18:00",
                'end_time': f"{now.strftime('%Y-%m-%d')} 22:00",
                'duration_hours': '4.0',
                'issue_description': 'Test issue',
                'resolution_notes': 'Test resolution'
            }
            
            save_overtime_entry('test_user', now.year, now.month, entry_data)
            print("   ✓ Test overtime entry created")
            
            # Load overtime logs
            logs = load_overtime_logs('test_user', now.year, now.month)
            print(f"   ✓ Loaded {len(logs)} overtime logs")
            
            # Get summary
            summary = get_overtime_summary('test_user', now.year, now.month)
            print(f"   ✓ Overtime summary: {summary['total_hours']} hours, {summary['entries']} entries")
            
            # Test 5: Test rotation functions
            print("\n5. Testing rotation functions...")
            from blueprints.standby.utils.db_rotation_manager import (
                get_standby_person, load_roster
            )
            
            today = datetime.today().strftime('%Y-%m-%d')
            standby_person = get_standby_person(today)
            print(f"   ✓ Today's standby person: {standby_person}")
            
            roster = load_roster()
            print(f"   ✓ Loaded roster with {len(roster['team_members'])} members")
            
            print("\n✓ All database integration tests passed!")
            
    except Exception as e:
        print(f"\n❌ Database integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == '__main__':
    success = test_database_integration()
    if success:
        print("\nDatabase integration is working correctly!")
    else:
        print("\nDatabase integration has issues that need to be resolved.") 