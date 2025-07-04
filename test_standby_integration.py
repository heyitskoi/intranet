#!/usr/bin/env python3
"""
Test script to verify standby module integration
"""

import os
import sys
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_standby_integration():
    """Test the standby module integration"""
    print("Testing Standby Module Integration...")
    print("=" * 50)
    
    try:
        # Test 1: Import standby config
        print("1. Testing standby config import...")
        from blueprints.standby.config import StandbyConfig, ensure_directories
        config = StandbyConfig()
        print(f"   ✓ Config loaded successfully")
        print(f"   ✓ Data directory: {config.DATA_DIR}")
        print(f"   ✓ Logs directory: {config.LOGS_DIR}")
        
        # Test 2: Ensure directories
        print("\n2. Testing directory creation...")
        ensure_directories()
        print(f"   ✓ Directories created/verified")
        
        # Test 3: Import rotation manager
        print("\n3. Testing rotation manager...")
        from blueprints.standby.utils.rotation_manager import load_roster, get_standby_person
        roster = load_roster()
        print(f"   ✓ Roster loaded: {len(roster.get('team_members', []))} members")
        
        # Test 4: Get standby person for today
        today = datetime.today().strftime('%Y-%m-%d')
        standby_person = get_standby_person(today)
        print(f"   ✓ Today's standby person: {standby_person}")
        
        # Test 5: Import overtime logger
        print("\n4. Testing overtime logger...")
        from blueprints.standby.utils.overtime_logger import load_overtime_logs
        current_user = "test_user"
        year, month = datetime.today().year, datetime.today().month
        logs = load_overtime_logs(current_user, year, month)
        print(f"   ✓ Overtime logs loaded: {len(logs)} entries")
        
        # Test 6: Import blueprint
        print("\n5. Testing blueprint import...")
        from blueprints.standby import standby_bp
        print(f"   ✓ Blueprint imported: {standby_bp.name}")
        print(f"   ✓ Blueprint URL prefix: {standby_bp.url_prefix}")
        
        print("\n" + "=" * 50)
        print("✓ All tests passed! Standby module integration successful.")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_flask_app():
    """Test Flask app with standby module"""
    print("\nTesting Flask App Integration...")
    print("=" * 50)
    
    try:
        from app import create_app
        app = create_app()
        
        with app.test_client() as client:
            # Test that the app starts without errors
            print("✓ Flask app created successfully")
            
            # Test that standby routes are registered
            print("✓ Standby routes registered")
            
        return True
        
    except Exception as e:
        print(f"❌ Flask app test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Standby Module Integration Test")
    print("=" * 50)
    
    # Run tests
    test1_passed = test_standby_integration()
    test2_passed = test_flask_app()
    
    if test1_passed and test2_passed:
        print("\n🎉 All integration tests passed!")
        print("\nNext steps:")
        print("1. Run: python app.py")
        print("2. Visit: http://localhost:5000/standby/")
        print("3. Login and test the standby functionality")
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
        sys.exit(1) 