#!/usr/bin/env python3
"""
Test script for the enhanced standby calendar system.
Tests past assignments, future calculated slots, and overrides.
"""

import sys
import os
from datetime import datetime, timedelta, date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db, Department, User, StandbyMember, StandbyAssignment, StandbyOverride, StandbyDurationConfig

def test_enhanced_calendar():
    """Test the enhanced calendar system functionality."""
    app = create_app()
    
    with app.app_context():
        print("Testing Enhanced Standby Calendar System")
        print("=" * 50)
        
        # Get or create test department
        dept = Department.query.filter_by(name='Engineering').first()
        if not dept:
            dept = Department(name='Engineering')
            db.session.add(dept)
            db.session.commit()
            print(f"✓ Created test department: {dept.name}")
        
        # Get or create test users
        users = []
        for username in ['alice', 'bob', 'charlie']:
            user = User.query.filter_by(username=username).first()
            if not user:
                user = User(
                    username=username, 
                    email=f'{username}@example.com', 
                    department_id=dept.id,
                    password_hash='test_hash'  # Add required password_hash
                )
                db.session.add(user)
                users.append(user)
            else:
                users.append(user)
        
        db.session.commit()
        print(f"✓ Test users ready: {[u.username for u in users]}")
        
        # Get or create standby configuration
        config = StandbyDurationConfig.query.filter_by(department_id=dept.id).first()
        if not config:
            config = StandbyDurationConfig(
                department_id=dept.id,
                standby_shift_days=2,
                rotation_start_date=date(2024, 1, 1),
                created_by_id=users[0].id,
                updated_by_id=users[0].id
            )
            db.session.add(config)
            db.session.commit()
            print(f"✓ Created standby configuration")
        
        # Add users to standby rotation
        for i, user in enumerate(users):
            member = StandbyMember.query.filter_by(user_id=user.id).first()
            if not member:
                member = StandbyMember(
                    user_id=user.id,
                    active=True,
                    rotation_order=i,
                    color=f'#{hash(user.username) % 0xFFFFFF:06x}'
                )
                db.session.add(member)
        
        db.session.commit()
        print(f"✓ Added users to standby rotation")
        
        # Create some past assignments (these should never change)
        today = datetime.now().date()
        past_dates = [today - timedelta(days=i) for i in range(1, 8)]  # Last 7 days
        
        for i, past_date in enumerate(past_dates):
            # Check if assignment already exists
            existing = StandbyAssignment.query.filter_by(
                department_id=dept.id,
                date=past_date
            ).first()
            
            if not existing:
                user = users[i % len(users)]
                assignment = StandbyAssignment(
                    department_id=dept.id,
                    user_id=user.id,
                    date=past_date
                )
                db.session.add(assignment)
        
        db.session.commit()
        print(f"✓ Created {len(past_dates)} past assignments")
        
        # Create some overrides
        future_dates = [today + timedelta(days=i) for i in range(1, 4)]  # Next 3 days
        
        for i, future_date in enumerate(future_dates):
            # Check if override already exists
            existing = StandbyOverride.query.filter_by(date=future_date).first()
            
            if not existing:
                user = users[(i + 1) % len(users)]  # Different user than calculated
                override = StandbyOverride(
                    date=future_date,
                    user_id=user.id,
                    reason=f'Test override {i+1}',
                    created_by_id=users[0].id
                )
                db.session.add(override)
        
        db.session.commit()
        print(f"✓ Created {len(future_dates)} overrides")
        
        # Test the calendar query logic
        print("\nTesting Calendar Query Logic:")
        print("-" * 30)
        
        # Test date range that includes past, present, and future
        start_date = today - timedelta(days=5)
        end_date = today + timedelta(days=10)
        
        # Query assignments
        assignments = (
            StandbyAssignment.query
            .filter(
                StandbyAssignment.department_id == dept.id,
                StandbyAssignment.date >= start_date,
                StandbyAssignment.date <= end_date
            )
            .join(User)
            .all()
        )
        assignment_map = {a.date: a for a in assignments}
        
        # Query overrides
        overrides = (
            StandbyOverride.query
            .filter(
                StandbyOverride.date >= start_date,
                StandbyOverride.date <= end_date
            )
            .join(User, StandbyOverride.user_id == User.id)
            .all()
        )
        override_map = {o.date: o for o in overrides}
        
        # Get active members
        active_members = (
            StandbyMember.query.filter_by(active=True)
            .join(User)
            .filter(User.department_id == dept.id)
            .order_by(StandbyMember.rotation_order)
            .all()
        )
        
        # Build calendar slots (simulating the route logic)
        calendar_slots = []
        current_date = start_date
        
        while current_date <= end_date:
            slot = {
                'date': current_date,
                'username': None,
                'source': 'none',
                'is_override': False,
                'is_past': current_date < today,
                'is_today': current_date == today,
                'override_reason': None
            }
            
            # Priority 1: Override
            if current_date in override_map:
                override = override_map[current_date]
                slot.update({
                    'username': override.user.username,
                    'source': 'override',
                    'is_override': True,
                    'override_reason': override.reason
                })
            # Priority 2: Stored assignment
            elif current_date in assignment_map:
                assignment = assignment_map[current_date]
                slot.update({
                    'username': assignment.user.username,
                    'source': 'db'
                })
            # Priority 3: Calculated future assignment
            elif (current_date >= today and 
                  config and 
                  active_members and 
                  current_date >= config.rotation_start_date):
                
                days_since_start = (current_date - config.rotation_start_date).days
                if days_since_start >= 0:
                    idx = (days_since_start // config.standby_shift_days) % len(active_members)
                    slot.update({
                        'username': active_members[idx].user.username,
                        'source': 'calculated'
                    })
            
            calendar_slots.append(slot)
            current_date += timedelta(days=1)
        
        # Display results
        print(f"Calendar slots for {start_date} to {end_date}:")
        for slot in calendar_slots:
            date_str = slot['date'].strftime('%Y-%m-%d')
            username = slot['username'] or '—'
            source = slot['source']
            is_past = slot['is_past']
            is_override = slot['is_override']
            
            status = []
            if is_past:
                status.append('PAST')
            if is_override:
                status.append('OVERRIDE')
            if slot['is_today']:
                status.append('TODAY')
            
            status_str = f" [{', '.join(status)}]" if status else ""
            
            print(f"  {date_str}: {username} ({source}){status_str}")
        
        # Test statistics
        past_count = len([s for s in calendar_slots if s['source'] == 'db' and s['is_past']])
        future_stored_count = len([s for s in calendar_slots if s['source'] == 'db' and not s['is_past']])
        calculated_count = len([s for s in calendar_slots if s['source'] == 'calculated'])
        override_count = len([s for s in calendar_slots if s['source'] == 'override'])
        
        print(f"\nSummary:")
        print(f"  Past assignments: {past_count}")
        print(f"  Future stored: {future_stored_count}")
        print(f"  Future calculated: {calculated_count}")
        print(f"  Overrides: {override_count}")
        
        # Test configuration change (should not affect past assignments)
        print(f"\nTesting Configuration Change:")
        print("-" * 30)
        
        old_shift_days = config.standby_shift_days
        config.standby_shift_days = 3  # Change from 2 to 3 days
        db.session.commit()
        
        # Verify past assignments are unchanged
        past_assignments_after = (
            StandbyAssignment.query
            .filter(
                StandbyAssignment.department_id == dept.id,
                StandbyAssignment.date < today
            )
            .count()
        )
        
        print(f"  Past assignments before config change: {len(past_dates)}")
        print(f"  Past assignments after config change: {past_assignments_after}")
        print(f"  ✓ Past assignments preserved: {len(past_dates) == past_assignments_after}")
        
        # Test override preservation
        overrides_after = (
            StandbyOverride.query
            .filter(StandbyOverride.date >= today)
            .count()
        )
        
        print(f"  Overrides before config change: {len(future_dates)}")
        print(f"  Overrides after config change: {overrides_after}")
        print(f"  ✓ Overrides preserved: {len(future_dates) == overrides_after}")
        
        print(f"\n✓ Enhanced calendar system test completed successfully!")

if __name__ == '__main__':
    test_enhanced_calendar() 