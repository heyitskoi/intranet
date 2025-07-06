#!/usr/bin/env python3
"""
Setup script for the new standby assignment system.
This script runs all necessary steps in the correct order.
"""

import os
import sys
import subprocess

def run_command(command, description):
    """Run a command and handle errors."""
    print(f"\n{description}...")
    print(f"Running: {command}")
    print("-" * 50)
    
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running command: {e}")
        print(f"Error output: {e.stderr}")
        return False

def main():
    """Main setup function."""
    print("Standby Assignment System Setup")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not os.path.exists('app.py'):
        print("❌ Error: app.py not found. Please run this script from the project root directory.")
        sys.exit(1)
    
    print("✓ Found app.py, proceeding with setup...")
    
    # Step 1: Seed the database
    print("\nStep 1: Seeding database with initial data...")
    if not run_command("python seed_database.py", "Seeding database"):
        print("❌ Database seeding failed. Please check the error above.")
        sys.exit(1)
    
    # Step 2: Run the migration script
    print("\nStep 2: Creating StandbyAssignment table and migrating data...")
    if not run_command("python migrations/create_standby_assignments_table.py", "Running migration"):
        print("❌ Migration failed. Please check the error above.")
        sys.exit(1)
    
    # Step 3: Test the system
    print("\nStep 3: Testing the assignment system...")
    if not run_command("python test_assignment_system.py", "Testing system"):
        print("❌ System test failed. Please check the error above.")
        sys.exit(1)
    
    print("\n🎉 Setup completed successfully!")
    print("=" * 50)
    print("\nNext steps:")
    print("1. Start the Flask application: python app.py")
    print("2. Login with admin/admin123")
    print("3. Navigate to /standby/roster/duration-config to test configuration changes")
    print("4. Check that past assignments remain unchanged when you modify settings")
    
    print("\nDocumentation:")
    print("- See docs/STANDBY_ASSIGNMENT_SYSTEM.md for detailed information")
    print("- The system automatically uses assignments when department_id is provided")
    print("- Configuration changes only affect future dates")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Setup failed with error: {e}")
        sys.exit(1) 