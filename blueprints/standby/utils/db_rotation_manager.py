"""
Database-based rotation manager for standby module.
Replaces the file-based rotation_manager.py
"""

from datetime import datetime, timedelta
from models import db, User, StandbyMember, StandbyOverride
from sqlalchemy import and_


def load_roster(department_id: int = None):
    """Load roster data from database and return in legacy format for compatibility."""
    # Get standby members filtered by department
    if department_id:
        standby_members = StandbyMember.query.join(User).filter(
            User.department_id == department_id
        ).order_by(StandbyMember.rotation_order).all()
    else:
        # If no department specified, get members without departments
        standby_members = StandbyMember.query.join(User).filter(
            User.department_id.is_(None)
        ).order_by(StandbyMember.rotation_order).all()
    
    # Get overrides filtered by department
    if department_id:
        overrides = StandbyOverride.query.join(User, StandbyOverride.user_id == User.id).filter(
            User.department_id == department_id
        ).all()
    else:
        overrides = StandbyOverride.query.join(User, StandbyOverride.user_id == User.id).filter(
            User.department_id.is_(None)
        ).all()
    
    # Convert to legacy format
    team_members = []
    rotation = []
    
    for member in standby_members:
        team_members.append({
            'name': member.user.username,
            'color': member.color,
            'active': member.active
        })
        
        # Only add to rotation if they're active and have a rotation order
        if member.active and member.rotation_order is not None:
            rotation.append(member.user.username)
    
    # Convert overrides to legacy format
    overrides_dict = {}
    for override in overrides:
        overrides_dict[override.date.strftime('%Y-%m-%d')] = override.user.username
    
    return {
        'team_members': team_members,
        'rotation': rotation,
        'overrides': overrides_dict
    }


def get_standby_person(date: str, department_id: int = None):
    """Get the standby person for a specific date using database."""
    # Use the new assignment-based system if department_id is provided
    if department_id:
        from .assignment_rotation_manager import AssignmentRotationManager
        return AssignmentRotationManager.get_standby_person(date, department_id)
    
    # Fallback to old logic for backward compatibility
    try:
        target_date = datetime.strptime(date, '%Y-%m-%d').date()
    except ValueError:
        return None
    
    # Check for override first
    if department_id:
        override = StandbyOverride.query.filter_by(date=target_date).join(User, StandbyOverride.user_id == User.id).filter(
            User.department_id == department_id
        ).first()
    else:
        override = StandbyOverride.query.filter_by(date=target_date).join(User, StandbyOverride.user_id == User.id).filter(
            User.department_id.is_(None)
        ).first()
    
    if override:
        # Verify the override person is still active
        standby_member = StandbyMember.query.filter_by(user_id=override.user_id, active=True).first()
        if standby_member:
            return override.user.username
    
    # If no override or override person is inactive, use rotation
    if department_id:
        active_members = StandbyMember.query.filter_by(active=True).join(User).filter(
            User.department_id == department_id
        ).order_by(StandbyMember.rotation_order).all()
    else:
        active_members = StandbyMember.query.filter_by(active=True).join(User).filter(
            User.department_id.is_(None)
        ).order_by(StandbyMember.rotation_order).all()
    
    if not active_members:
        return None
    
    # Get department configuration for rotation start date
    from models import StandbyDurationConfig
    start_date = datetime(2024, 1, 1).date()  # Default fallback
    
    if department_id:
        config = StandbyDurationConfig.query.filter_by(department_id=department_id).first()
        if config and config.rotation_start_date:
            start_date = config.rotation_start_date
    
    # Calculate days since start
    days_since_start = (target_date - start_date).days
    
    if days_since_start < 0:
        return None
    
    # Calculate which person should be on standby
    person_index = days_since_start % len(active_members)
    return active_members[person_index].user.username


def add_team_member(username: str, color: str = '#007bff', active: bool = True):
    """Add a new team member to the standby roster."""
    # Find user
    user = User.query.filter_by(username=username).first()
    if not user:
        raise ValueError(f"User '{username}' not found in database")
    
    # Check if already a standby member
    existing = StandbyMember.query.filter_by(user_id=user.id).first()
    if existing:
        # If they exist but are inactive, reactivate them
        if not existing.active:
            existing.active = True
            existing.color = color
            db.session.commit()
            return existing
        else:
            raise ValueError(f"User '{username}' is already an active standby member")
    
    # Add to standby members
    standby_member = StandbyMember(
        user_id=user.id,
        color=color,
        active=active
    )
    db.session.add(standby_member)
    db.session.commit()
    
    return standby_member


def remove_team_member(username: str):
    """Remove a team member from the standby roster."""
    user = User.query.filter_by(username=username).first()
    if not user:
        raise ValueError(f"User '{username}' not found")
    
    standby_member = StandbyMember.query.filter_by(user_id=user.id).first()
    if not standby_member:
        raise ValueError(f"User '{username}' is not a standby member")
    
    db.session.delete(standby_member)
    db.session.commit()


def update_team_member(username: str, **kwargs):
    """Update a team member's properties."""
    user = User.query.filter_by(username=username).first()
    if not user:
        raise ValueError(f"User '{username}' not found")
    
    standby_member = StandbyMember.query.filter_by(user_id=user.id).first()
    if not standby_member:
        raise ValueError(f"User '{username}' is not a standby member")
    
    # Update allowed fields
    allowed_fields = ['color', 'active', 'rotation_order']
    for field, value in kwargs.items():
        if field in allowed_fields:
            setattr(standby_member, field, value)
    
    db.session.commit()
    return standby_member


def update_rotation_order(usernames: list):
    """Update the rotation order of team members."""
    # Get the department ID from the first user (assuming all users are in the same department)
    department_id = None
    if usernames:
        first_user = User.query.filter_by(username=usernames[0]).first()
        if first_user and first_user.department:
            department_id = first_user.department.id
    
    # Update rotation order
    for i, username in enumerate(usernames, 1):
        user = User.query.filter_by(username=username).first()
        if user:
            standby_member = StandbyMember.query.filter_by(user_id=user.id).first()
            if standby_member:
                standby_member.rotation_order = i
    
    db.session.commit()
    
    # Regenerate future assignments if department_id is available
    if department_id:
        try:
            from .assignment_rotation_manager import AssignmentRotationManager
            regenerated_count = AssignmentRotationManager.regenerate_future_assignments(department_id)
            print(f"Regenerated {regenerated_count} future assignments after rotation order change")
        except Exception as e:
            print(f"Warning: Failed to regenerate future assignments: {e}")
            # Don't fail the operation if assignment regeneration fails


def add_override(date: str, username: str, reason: str = None, created_by_username: str = None):
    """Add a date override."""
    try:
        override_date = datetime.strptime(date, '%Y-%m-%d').date()
    except ValueError:
        raise ValueError(f"Invalid date format: {date}")
    
    # Find user
    user = User.query.filter_by(username=username).first()
    if not user:
        raise ValueError(f"User '{username}' not found")
    
    # Find created_by user
    created_by_user = None
    if created_by_username:
        created_by_user = User.query.filter_by(username=created_by_username).first()
        if not created_by_user:
            raise ValueError(f"Created by user '{created_by_username}' not found")
    else:
        # Use the same user if not specified
        created_by_user = user
    
    # Check if override already exists
    existing = StandbyOverride.query.filter_by(date=override_date).first()
    if existing:
        raise ValueError(f"Override already exists for {date}")
    
    # Determine who was originally assigned for this date
    original_user_id = None
    try:
        # Check if there's an existing assignment
        from .assignment_rotation_manager import AssignmentRotationManager
        department_id = user.department.id if user.department else None
        
        if department_id:
            from models import StandbyAssignment
            existing_assignment = StandbyAssignment.query.filter_by(
                department_id=department_id,
                date=override_date
            ).first()
            
            if existing_assignment:
                original_user_id = existing_assignment.user_id
            else:
                # Calculate what the assignment would be based on rotation
                original_person = get_standby_person(date, department_id)
                if original_person:
                    original_user = User.query.filter_by(username=original_person).first()
                    if original_user:
                        original_user_id = original_user.id
    except Exception as e:
        # If we can't determine the original assignment, continue without it
        print(f"Warning: Could not determine original assignment for {date}: {e}")
    
    # Create override
    override = StandbyOverride(
        date=override_date,
        user_id=user.id,
        original_user_id=original_user_id,
        reason=reason,
        created_by_id=created_by_user.id
    )
    db.session.add(override)
    db.session.commit()
    
    return override


def remove_override(date: str):
    """Remove a date override."""
    try:
        override_date = datetime.strptime(date, '%Y-%m-%d').date()
    except ValueError:
        raise ValueError(f"Invalid date format: {date}")
    
    override = StandbyOverride.query.filter_by(date=override_date).first()
    if not override:
        raise ValueError(f"No override found for {date}")
    
    db.session.delete(override)
    db.session.commit()


def get_active_standby_members():
    """Get all active standby members with their user info."""
    return StandbyMember.query.filter_by(active=True).join(User).order_by(StandbyMember.rotation_order).all()


def get_standby_member_by_username(username: str):
    """Get standby member by username."""
    user = User.query.filter_by(username=username).first()
    if not user:
        return None
    
    return StandbyMember.query.filter_by(user_id=user.id).first()


def get_overrides_for_date_range(start_date: str, end_date: str):
    """Get all overrides within a date range."""
    try:
        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()
    except ValueError:
        raise ValueError("Invalid date format")
    
    return StandbyOverride.query.filter(
        and_(
            StandbyOverride.date >= start,
            StandbyOverride.date <= end
        )
    ).join(User, StandbyOverride.user_id == User.id).order_by(StandbyOverride.date).all()


def is_user_standby_member(username: str):
    """Check if a user is a standby member."""
    user = User.query.filter_by(username=username).first()
    if not user:
        return False
    
    return StandbyMember.query.filter_by(user_id=user.id).first() is not None


def get_standby_members_for_calendar():
    """Get standby members formatted for calendar display."""
    members = get_active_standby_members()
    return {
        member.user.username: {
            'name': member.user.username,
            'color': member.color,
            'active': member.active,
            'rotation_order': member.rotation_order
        }
        for member in members
    } 