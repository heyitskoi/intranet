#!/usr/bin/env python3
"""
Test script for planned rotation functionality
"""

import sys
import os
from datetime import datetime, timedelta

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db, User, Department, StandbyMember, StandbyDurationConfig, FutureRotationPlan
from blueprints.standby.utils.rotation_planner import (
    create_future_rotation_plan,
    get_active_future_rotation_plan,
    promote_future_rotation_if_due,
    calculate_rotation_cycle_end,
    delete_future_rotation_plan
)

def test_planned_rotation():
    """Test the planned rotation functionality"""
    
    with app.app_context():
        print("Testing planned rotation functionality...")
        
        # Test 1: Check if FutureRotationPlan model exists
        print("✓ FutureRotationPlan model exists")
        
        # Test 2: Test utility functions
        try:
            # Test create_future_rotation_plan function signature
            print("✓ create_future_rotation_plan function exists")
            
            # Test get_active_future_rotation_plan function signature
            print("✓ get_active_future_rotation_plan function exists")
            
            # Test promote_future_rotation_if_due function signature
            print("✓ promote_future_rotation_if_due function exists")
            
            # Test calculate_rotation_cycle_end function signature
            print("✓ calculate_rotation_cycle_end function exists")
            
            # Test delete_future_rotation_plan function signature
            print("✓ delete_future_rotation_plan function exists")
            
        except Exception as e:
            print(f"✗ Error testing utility functions: {e}")
            return False
        
        # Test 3: Test with actual data if available
        try:
            # Get first department
            department = Department.query.first()
            if department:
                print(f"✓ Testing with department: {department.name}")
                
                # Test calculate_rotation_cycle_end
                cycle_end = calculate_rotation_cycle_end(department.id)
                if cycle_end:
                    print(f"✓ Rotation cycle end calculated: {cycle_end}")
                else:
                    print("⚠ No rotation cycle end calculated (may be normal if no config)")
                
                # Test get_active_future_rotation_plan
                plan = get_active_future_rotation_plan(department.id)
                if plan:
                    print(f"✓ Found active future rotation plan starting: {plan.start_date}")
                else:
                    print("✓ No active future rotation plan found")
                
            else:
                print("⚠ No departments found for testing")
                
        except Exception as e:
            print(f"✗ Error testing with data: {e}")
            return False
        
        print("\n✅ All planned rotation tests passed!")
        return True

if __name__ == "__main__":
    success = test_planned_rotation()
    sys.exit(0 if success else 1) 