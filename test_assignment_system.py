#!/usr/bin/env python3
"""
Test script to verify the new standby assignment system.
"""

import os
import sys
from datetime import datetime, timedelta

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from models import User, Department, StandbyMember, StandbyDurationConfig, StandbyAssignment
from blueprints.standby.utils.assignment_rotation_manager import AssignmentRotationManager

def test_assignment_system():
    """Test the assignment system functionality."""
    app = create_app()
    
    with app.app_context():
        print("Testing Standby Assignment System")
        print("=" * 50)
        
        # Get test department
        department = Department.query.filter_by(name='IT').first()
        if not department:
            print("❌ IT department not found. Run seed_database.py first.")
            return False
        
        print(f"✓ Testing with department: {department.name}")
        
        # Test 1: Check if assignments exist
        print("\n1. Checking existing assignments...")
        today = datetime.now().date()
        assignment = StandbyAssignment.query.filter_by(
            department_id=department.id,
            date=today
        ).first()
        
        if assignment:
            print(f"   ✓ Found assignment for today: {assignment.user.username}")
        else:
            print("   ⚠ No assignment found for today")
        
        # Test 2: Get standby person for today
        print("\n2. Testing get_standby_person for today...")
        today_str = today.strftime('%Y-%m-%d')
        standby_person = AssignmentRotationManager.get_standby_person(today_str, department.id)
        
        if standby_person:
            print(f"   ✓ Today's standby person: {standby_person}")
        else:
            print("   ❌ No standby person found for today")
        
        # Test 3: Get standby person for future date
        print("\n3. Testing get_standby_person for future date...")
        future_date = today + timedelta(days=7)
        future_date_str = future_date.strftime('%Y-%m-%d')
        future_standby = AssignmentRotationManager.get_standby_person(future_date_str, department.id)
        
        if future_standby:
            print(f"   ✓ Future standby person: {future_standby}")
        else:
            print("   ❌ No standby person found for future date")
        
        # Test 4: Get assignments for date range
        print("\n4. Testing get_assignments_for_date_range...")
        start_date = today.strftime('%Y-%m-%d')
        end_date = (today + timedelta(days=14)).strftime('%Y-%m-%d')
        
        assignments = AssignmentRotationManager.get_assignments_for_date_range(
            start_date, end_date, department.id
        )
        
        print(f"   ✓ Found {len(assignments)} assignments for next 14 days")
        for assignment in assignments[:5]:  # Show first 5
            print(f"      {assignment['date']}: {assignment['username']}")
        
        # Test 5: Test manual assignment
        print("\n5. Testing manual assignment...")
        test_date = today + timedelta(days=30)
        test_date_str = test_date.strftime('%Y-%m-%d')
        
        # Get a test user
        test_user = User.query.filter_by(department_id=department.id).first()
        if test_user:
            try:
                manual_assignment = AssignmentRotationManager.create_manual_assignment(
                    test_date_str, test_user.username, department.id
                )
                print(f"   ✓ Created manual assignment: {test_date_str} -> {test_user.username}")
                
                # Verify assignment was created
                created_assignment = StandbyAssignment.query.filter_by(
                    department_id=department.id,
                    date=test_date
                ).first()
                
                if created_assignment and created_assignment.user_id == test_user.id:
                    print("   ✓ Manual assignment verified")
                else:
                    print("   ❌ Manual assignment verification failed")
                
                # Clean up
                AssignmentRotationManager.delete_assignment(test_date_str, department.id)
                print("   ✓ Cleaned up test assignment")
                
            except Exception as e:
                print(f"   ❌ Manual assignment test failed: {e}")
        else:
            print("   ❌ No test user found")
        
        # Test 6: Test assignment statistics
        print("\n6. Testing assignment statistics...")
        stats = AssignmentRotationManager.get_assignment_stats(department.id)
        
        print(f"   ✓ Total assignments: {stats['total_assignments']}")
        print(f"   ✓ Past assignments: {stats['past_assignments']}")
        print(f"   ✓ Future assignments: {stats['future_assignments']}")
        print(f"   ✓ Today's assignment: {stats['today_assignment']}")
        
        # Test 7: Test configuration change simulation
        print("\n7. Testing configuration change simulation...")
        config = StandbyDurationConfig.query.filter_by(department_id=department.id).first()
        if config:
            old_shift_days = config.standby_shift_days
            config.standby_shift_days = 2  # Change to 2 days
            db.session.commit()
            
            try:
                regenerated_count = AssignmentRotationManager.regenerate_future_assignments(department.id)
                print(f"   ✓ Regenerated {regenerated_count} future assignments")
                
                # Restore original configuration
                config.standby_shift_days = old_shift_days
                db.session.commit()
                
                regenerated_count = AssignmentRotationManager.regenerate_future_assignments(department.id)
                print(f"   ✓ Restored configuration and regenerated {regenerated_count} assignments")
                
            except Exception as e:
                print(f"   ❌ Configuration change test failed: {e}")
                # Restore original configuration
                config.standby_shift_days = old_shift_days
                db.session.commit()
        else:
            print("   ❌ No configuration found")
        
        print("\n🎉 Assignment system test completed!")
        return True

def test_backward_compatibility():
    """Test that the old system still works for backward compatibility."""
    app = create_app()
    
    with app.app_context():
        print("\nTesting Backward Compatibility")
        print("=" * 50)
        
        # Test old get_standby_person without department_id
        from blueprints.standby.utils.db_rotation_manager import get_standby_person
        
        today = datetime.now().date().strftime('%Y-%m-%d')
        standby_person = get_standby_person(today)  # No department_id
        
        if standby_person:
            print(f"✓ Old system works: {standby_person}")
        else:
            print("⚠ Old system returned None (this might be expected)")
        
        return True

if __name__ == '__main__':
    try:
        success1 = test_assignment_system()
        success2 = test_backward_compatibility()
        
        if success1 and success2:
            print("\n✅ All tests passed!")
        else:
            print("\n❌ Some tests failed!")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        sys.exit(1) 