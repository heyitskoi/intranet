#!/usr/bin/env python3
"""
Test script to verify standby module file structure and basic functionality
"""

import os
import sys
import json
from datetime import datetime

def test_file_structure():
    """Test that all required files and directories exist"""
    print("Testing Standby Module File Structure...")
    print("=" * 50)
    
    required_files = [
        "blueprints/standby/__init__.py",
        "blueprints/standby/config.py",
        "blueprints/standby/utils/rotation_manager.py",
        "blueprints/standby/utils/overtime_logger.py",
        "templates/standby/base.html",
        "templates/standby/dashboard.html",
        "templates/standby/calendar.html",
        "templates/standby/overtime.html",
        "templates/standby/roster.html",
        "static/standby/css/calendar.css",
        "static/standby/css/sidebar.css",
        "static/standby/js/calendar-utils.js",
        "static/standby/js/sidebar-utils.js",
        "blueprints/standby/README.md"
    ]
    
    all_exist = True
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✓ {file_path}")
        else:
            print(f"❌ {file_path} - MISSING")
            all_exist = False
    
    return all_exist

def test_config_structure():
    """Test the configuration structure"""
    print("\nTesting Configuration Structure...")
    print("=" * 50)
    
    try:
        # Test config file exists and is valid Python
        config_path = "blueprints/standby/config.py"
        if not os.path.exists(config_path):
            print(f"❌ Config file missing: {config_path}")
            return False
        
        # Read and check config content
        with open(config_path, 'r') as f:
            content = f.read()
        
        if "class StandbyConfig" in content:
            print("✓ StandbyConfig class found")
        else:
            print("❌ StandbyConfig class not found")
            return False
        
        if "ensure_directories" in content:
            print("✓ ensure_directories function found")
        else:
            print("❌ ensure_directories function not found")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Config test failed: {e}")
        return False

def test_utils_structure():
    """Test the utility functions structure"""
    print("\nTesting Utils Structure...")
    print("=" * 50)
    
    utils_files = [
        "blueprints/standby/utils/rotation_manager.py",
        "blueprints/standby/utils/overtime_logger.py"
    ]
    
    all_valid = True
    for file_path in utils_files:
        if not os.path.exists(file_path):
            print(f"❌ {file_path} - MISSING")
            all_valid = False
            continue
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            if "from ..config import StandbyConfig" in content:
                print(f"✓ {file_path} - Config import found")
            else:
                print(f"⚠ {file_path} - Config import not found (may be OK)")
            
        except Exception as e:
            print(f"❌ {file_path} - Error reading: {e}")
            all_valid = False
    
    return all_valid

def test_blueprint_structure():
    """Test the blueprint structure"""
    print("\nTesting Blueprint Structure...")
    print("=" * 50)
    
    try:
        with open("blueprints/standby/__init__.py", 'r') as f:
            content = f.read()
        
        checks = [
            ("Blueprint import", "from flask import Blueprint"),
            ("standby_bp definition", "standby_bp = Blueprint"),
            ("URL prefix", "url_prefix='/standby'"),
            ("Dashboard route", "@standby_bp.route('/dashboard')"),
            ("Calendar route", "@standby_bp.route('/calendar')"),
            ("Roster route", "@standby_bp.route('/roster'"),
            ("Overtime route", "@standby_bp.route('/overtime'"),
            ("Login required", "@login_required"),
        ]
        
        all_found = True
        for check_name, check_text in checks:
            if check_text in content:
                print(f"✓ {check_name}")
            else:
                print(f"❌ {check_name} - {check_text}")
                all_found = False
        
        return all_found
        
    except Exception as e:
        print(f"❌ Blueprint test failed: {e}")
        return False

def test_template_structure():
    """Test the template structure"""
    print("\nTesting Template Structure...")
    print("=" * 50)
    
    template_files = [
        "templates/standby/base.html",
        "templates/standby/dashboard.html",
        "templates/standby/calendar.html",
        "templates/standby/overtime.html",
        "templates/standby/roster.html"
    ]
    
    all_valid = True
    for file_path in template_files:
        if not os.path.exists(file_path):
            print(f"❌ {file_path} - MISSING")
            all_valid = False
            continue
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            if "{% extends" in content:
                print(f"✓ {file_path} - Template syntax found")
            else:
                print(f"⚠ {file_path} - Template syntax not found")
            
        except Exception as e:
            print(f"❌ {file_path} - Error reading: {e}")
            all_valid = False
    
    return all_valid

def test_static_files():
    """Test the static files structure"""
    print("\nTesting Static Files Structure...")
    print("=" * 50)
    
    static_files = [
        "static/standby/css/calendar.css",
        "static/standby/css/sidebar.css",
        "static/standby/js/calendar-utils.js",
        "static/standby/js/sidebar-utils.js"
    ]
    
    all_exist = True
    for file_path in static_files:
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            print(f"✓ {file_path} ({size} bytes)")
        else:
            print(f"❌ {file_path} - MISSING")
            all_exist = False
    
    return all_exist

def main():
    """Run all tests"""
    print("Standby Module Structure Test")
    print("=" * 50)
    
    tests = [
        ("File Structure", test_file_structure),
        ("Configuration", test_config_structure),
        ("Utils Structure", test_utils_structure),
        ("Blueprint Structure", test_blueprint_structure),
        ("Template Structure", test_template_structure),
        ("Static Files", test_static_files),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All structure tests passed!")
        print("\nNext steps:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Run: python app.py")
        print("3. Visit: http://localhost:5000/standby/")
        print("4. Login and test the standby functionality")
    else:
        print(f"\n❌ {total - passed} tests failed. Please fix the issues above.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 