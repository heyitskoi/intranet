import json
import os
from datetime import datetime, timedelta
from ..config import StandbyConfig

config = StandbyConfig()

def load_roster():
    """Load roster data from JSON file"""
    if os.path.exists(config.ROSTER_FILE):
        with open(config.ROSTER_FILE, 'r') as f:
            return json.load(f)
    else:
        # Create default roster if file doesn't exist
        default_roster = {
            "team_members": [
                {"name": "Alice", "color": "#007bff", "active": True},
                {"name": "Bob", "color": "#28a745", "active": True},
                {"name": "Charlie", "color": "#ffc107", "active": True}
            ],
            "rotation": ["Alice", "Bob", "Charlie"],
            "overrides": {}
        }
        save_roster(default_roster)
        return default_roster

def is_active(person_name):
    """Check if a person is active in the roster"""
    roster = load_roster()
    for member in roster.get('team_members', []):
        if member.get('name') == person_name:
            return member.get('active', True)
    return False

def get_standby_person(date: str):
    """Get the standby person for a specific date"""
    roster = load_roster()
    rotation = roster.get('rotation', [])
    overrides = roster.get('overrides', {})
    
    # Check if there's an override for this date
    if date in overrides:
        override_person = overrides[date]
        # Verify the override person is active
        if is_active(override_person):
            return override_person
        # If override person is inactive, fall back to rotation
    
    # If no override or override person is inactive, use rotation
    if not rotation:
        return None
    
    # Calculate which person should be on standby based on rotation
    # Start date is hardcoded for now - you might want to make this configurable
    start_date = datetime(2024, 1, 1)  # January 1, 2024
    target_date = datetime.strptime(date, '%Y-%m-%d')
    
    # Calculate days since start
    days_since_start = (target_date - start_date).days
    
    # Find active person in rotation
    active_rotation = [person for person in rotation if is_active(person)]
    if not active_rotation:
        return None
    
    # Calculate which person should be on standby
    person_index = days_since_start % len(active_rotation)
    return active_rotation[person_index]

def test_rotation_manager():
    """Test the rotation manager functionality"""
    print("Testing rotation manager...")
    
    # Test loading roster
    roster = load_roster()
    print(f"Loaded roster with {len(roster.get('team_members', []))} members")
    
    # Test getting standby person for today
    today = datetime.today().strftime('%Y-%m-%d')
    standby_person = get_standby_person(today)
    print(f"Today's standby person: {standby_person}")
    
    # Test getting standby person for next week
    next_week = (datetime.today() + timedelta(days=7)).strftime('%Y-%m-%d')
    next_standby = get_standby_person(next_week)
    print(f"Next week's standby person: {next_standby}")

def save_roster(roster):
    """Save roster data to JSON file"""
    # Ensure directory exists
    os.makedirs(os.path.dirname(config.ROSTER_FILE), exist_ok=True)
    
    with open(config.ROSTER_FILE, 'w') as f:
        json.dump(roster, f, indent=2)

if __name__ == "__main__":
    test_rotation_manager() 