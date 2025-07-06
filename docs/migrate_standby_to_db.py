#!/usr/bin/env python3
"""
Migration script to move standby module data from files to database.
This script will:
1. Import existing roster.json data into StandbyMember table
2. Import existing overtime CSV files into OvertimeLog table
3. Import existing overrides into StandbyOverride table
4. Create missing users if they don't exist in the database
"""

import os
import json
import csv
from datetime import datetime
from app import create_app, db
from models import User, StandbyMember, StandbyOverride, OvertimeLog

def migrate_standby_data():
    """Migrate all standby data from files to database."""
    app = create_app()
    
    with app.app_context():
        print("Starting standby data migration...")
        print("=" * 50)
        
        # Ensure tables exist
        db.create_all()
        
        # Step 1: Migrate roster data
        migrate_roster_data()
        
        # Step 2: Migrate overtime logs
        migrate_overtime_logs()
        
        # Step 3: Migrate overrides
        migrate_overrides()
        
        print("\nMigration completed successfully!")
        print("=" * 50)

def migrate_roster_data():
    """Migrate roster.json to StandbyMember table."""
    print("\n1. Migrating roster data...")
    
    roster_file = 'standby_data/roster.json'
    if not os.path.exists(roster_file):
        print(f"   ⚠ Roster file not found: {roster_file}")
        return
    
    try:
        with open(roster_file, 'r') as f:
            roster_data = json.load(f)
        
        team_members = roster_data.get('team_members', [])
        rotation = roster_data.get('rotation', [])
        
        print(f"   Found {len(team_members)} team members")
        
        for i, member_data in enumerate(team_members):
            name = member_data.get('name')
            color = member_data.get('color', '#007bff')
            active = member_data.get('active', True)
            
            # Find or create user
            user = User.query.filter_by(username=name).first()
            if not user:
                print(f"   Creating user: {name}")
                user = User(
                    username=name,
                    email=f"{name.lower()}@company.com",  # Placeholder email
                    password_hash="migrated_user"  # Will need to be reset
                )
                db.session.add(user)
                db.session.flush()  # Get the user ID
            
            # Check if standby member already exists
            existing_member = StandbyMember.query.filter_by(user_id=user.id).first()
            if existing_member:
                print(f"   Updating existing standby member: {name}")
                existing_member.color = color
                existing_member.active = active
                # Set rotation order if in rotation
                if name in rotation:
                    existing_member.rotation_order = rotation.index(name) + 1
            else:
                print(f"   Creating standby member: {name}")
                rotation_order = rotation.index(name) + 1 if name in rotation else None
                standby_member = StandbyMember(
                    user_id=user.id,
                    color=color,
                    active=active,
                    rotation_order=rotation_order
                )
                db.session.add(standby_member)
        
        db.session.commit()
        print(f"   ✓ Successfully migrated {len(team_members)} team members")
        
    except Exception as e:
        db.session.rollback()
        print(f"   ❌ Error migrating roster data: {e}")
        raise

def migrate_overtime_logs():
    """Migrate overtime CSV files to OvertimeLog table."""
    print("\n2. Migrating overtime logs...")
    
    logs_dir = 'standby_logs'
    if not os.path.exists(logs_dir):
        print(f"   ⚠ Logs directory not found: {logs_dir}")
        return
    
    total_migrated = 0
    
    for username in os.listdir(logs_dir):
        user_dir = os.path.join(logs_dir, username)
        if not os.path.isdir(user_dir) or username == '_archive':
            continue
        
        print(f"   Processing user: {username}")
        
        # Find or create user
        user = User.query.filter_by(username=username).first()
        if not user:
            print(f"     Creating user: {username}")
            user = User(
                username=username,
                email=f"{username.lower()}@company.com",
                password_hash="migrated_user"
            )
            db.session.add(user)
            db.session.flush()
        
        # Process CSV files
        for filename in os.listdir(user_dir):
            if not filename.endswith('.csv'):
                continue
            
            try:
                # Parse year and month from filename (YYYY-MM.csv)
                year, month = map(int, filename.replace('.csv', '').split('-'))
                csv_path = os.path.join(user_dir, filename)
                
                print(f"     Processing: {filename}")
                
                with open(csv_path, 'r', newline='', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        # Skip if already exists (check by start_time and user_id)
                        start_time_str = row.get('start_time', '')
                        if start_time_str:
                            try:
                                start_time = datetime.strptime(start_time_str, '%Y-%m-%d %H:%M')
                                
                                # Check if this entry already exists
                                existing = OvertimeLog.query.filter_by(
                                    user_id=user.id,
                                    start_time=start_time
                                ).first()
                                
                                if existing:
                                    continue  # Skip if already migrated
                                
                                # Parse end time
                                end_time_str = row.get('end_time', '')
                                end_time = datetime.strptime(end_time_str, '%Y-%m-%d %H:%M')
                                
                                # Create overtime log entry
                                overtime_log = OvertimeLog(
                                    user_id=user.id,
                                    start_time=start_time,
                                    end_time=end_time,
                                    duration_hours=float(row.get('duration_hours', 0)),
                                    issue_description=row.get('issue_description', ''),
                                    resolution_notes=row.get('resolution_notes', '')
                                )
                                db.session.add(overtime_log)
                                total_migrated += 1
                                
                            except ValueError as e:
                                print(f"       ⚠ Skipping invalid entry: {e}")
                                continue
                
            except Exception as e:
                print(f"     ❌ Error processing {filename}: {e}")
                continue
        
        db.session.commit()
    
    print(f"   ✓ Successfully migrated {total_migrated} overtime entries")

def migrate_overrides():
    """Migrate overrides from roster.json to StandbyOverride table."""
    print("\n3. Migrating overrides...")
    
    roster_file = 'standby_data/roster.json'
    if not os.path.exists(roster_file):
        print(f"   ⚠ Roster file not found: {roster_file}")
        return
    
    try:
        with open(roster_file, 'r') as f:
            roster_data = json.load(f)
        
        overrides = roster_data.get('overrides', {})
        print(f"   Found {len(overrides)} overrides")
        
        # Get a default user for created_by (use first admin or first user)
        created_by_user = User.query.filter_by(role_id=1).first() or User.query.first()
        if not created_by_user:
            print("   ❌ No users found for created_by reference")
            return
        
        for date_str, username in overrides.items():
            try:
                # Parse date
                override_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                
                # Find user
                user = User.query.filter_by(username=username).first()
                if not user:
                    print(f"   ⚠ User not found for override: {username}")
                    continue
                
                # Check if override already exists
                existing_override = StandbyOverride.query.filter_by(date=override_date).first()
                if existing_override:
                    print(f"   ⚠ Override already exists for {date_str}")
                    continue
                
                # Create override
                override = StandbyOverride(
                    date=override_date,
                    user_id=user.id,
                    created_by_id=created_by_user.id
                )
                db.session.add(override)
                print(f"   Created override: {date_str} -> {username}")
                
            except ValueError as e:
                print(f"   ⚠ Invalid date format: {date_str}")
                continue
        
        db.session.commit()
        print(f"   ✓ Successfully migrated {len(overrides)} overrides")
        
    except Exception as e:
        db.session.rollback()
        print(f"   ❌ Error migrating overrides: {e}")
        raise

def create_backup():
    """Create backup of original files before migration."""
    print("\nCreating backup of original files...")
    
    import shutil
    from datetime import datetime
    
    backup_dir = f"standby_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(backup_dir, exist_ok=True)
    
    # Backup roster file
    if os.path.exists('standby_data/roster.json'):
        shutil.copy2('standby_data/roster.json', f"{backup_dir}/roster.json")
    
    # Backup logs directory
    if os.path.exists('standby_logs'):
        shutil.copytree('standby_logs', f"{backup_dir}/standby_logs")
    
    print(f"   ✓ Backup created in: {backup_dir}")

if __name__ == '__main__':
    print("Standby Data Migration Tool")
    print("This will migrate your existing file-based standby data to the database.")
    print("A backup will be created before migration.")
    
    response = input("\nDo you want to proceed? (y/N): ")
    if response.lower() in ['y', 'yes']:
        try:
            create_backup()
            migrate_standby_data()
            print("\nMigration completed! You can now delete the backup directory if everything looks good.")
        except Exception as e:
            print(f"\nMigration failed: {e}")
            print("Check the backup directory for your original files.")
    else:
        print("Migration cancelled.") 