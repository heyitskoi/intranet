from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import os
import json
from models import db
from sqlalchemy import and_
# Import database-based utilities (new)
from .utils.db_rotation_manager import (
    get_standby_person, load_roster, add_team_member, remove_team_member, 
    update_team_member, update_rotation_order, add_override, remove_override,
    get_active_standby_members, get_standby_member_by_username, is_user_standby_member
)
from .utils.db_overtime_logger import (
    load_overtime_logs, validate_overtime_entry, save_overtime_entry, update_overtime_entry,
    get_overtime_summary, get_all_overtime_logs, get_recent_overtime_activity,
    delete_overtime_entry, export_overtime_to_csv
)
from .config import StandbyConfig

# Create blueprint
standby_bp = Blueprint('standby', __name__, url_prefix='/standby')

# Initialize config
config = StandbyConfig()

def is_admin_user(user):
    """Check if user has admin role."""
    return user.role and user.role.name == 'Admin'

def admin_required(f):
    """Decorator to require admin access."""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if not is_admin_user(current_user):
            flash('Admin access required.', 'error')
            return redirect(url_for('standby.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def get_current_standby_user():
    """Get the current standby user for today"""
    today = datetime.today().strftime('%Y-%m-%d')
    return get_standby_person(today)

@standby_bp.route('/')
@login_required
def index():
    return redirect(url_for('standby.dashboard'))

@standby_bp.route('/dashboard')
@login_required
def dashboard():
    # Check and promote future rotation if due
    department_id = current_user.department.id if current_user.department else None
    if department_id:
        from .utils.rotation_planner import promote_future_rotation_if_due
        promoted, regenerated_count = promote_future_rotation_if_due(department_id)
        if promoted:
            print(f"Promoted future rotation and regenerated {regenerated_count} assignments")
    
    # Get current standby user
    current_user_name = current_user.username
    today_dt = datetime.today()
    today = today_dt.strftime('%Y-%m-%d')
    next_week_dt = today_dt + timedelta(days=7)
    next_week = next_week_dt.strftime('%Y-%m-%d')
    # Get department ID for rotation calculation
    department_id = current_user.department.id if current_user.department else None
    current_standby = get_standby_person(today, department_id)
    next_standby = get_standby_person(next_week, department_id)
    year = today_dt.year
    month = today_dt.month
    month_name = today_dt.strftime('%B')
    
    # Load and sum overtime logs for this month
    overtime_logs = load_overtime_logs(current_user_name, year, month)
    total_overtime_hours = sum(float(log.get('duration_hours', 0)) for log in overtime_logs)
    
    # Load roster data for team members and overrides
    roster_data = load_roster(department_id)
    team_members = [m for m in roster_data.get('team_members', []) if m.get('active', True)]
    overrides = roster_data.get('overrides', {})
    
    # Sort overrides by date descending, get 5 most recent
    sorted_overrides = sorted(overrides.items(), key=lambda x: x[0], reverse=True)
    recent_overrides = [
        {'date': date, 'person': person}
        for date, person in sorted_overrides[:5]
    ]
    
    # Get recent overtime activity (last 5 entries across all team members)
    recent_overtime = get_recent_overtime_activity(limit=5)
    
    # Generate notifications
    notifications = []
    if current_standby == current_user_name:
        notifications.append("You are currently on standby duty")
    if next_standby == current_user_name:
        notifications.append("You will be on standby next week")
    if total_overtime_hours > config.OVERTIME_WARNING_THRESHOLD:
        notifications.append(f"High overtime this month: {total_overtime_hours:.1f} hours")
    
    # Monthly overtime limit from config
    monthly_overtime_limit = config.MONTHLY_OVERTIME_LIMIT
    
    return render_template(
        'standby/dashboard.html',
        current_user=current_user_name,
        current_standby=current_standby,
        next_standby=next_standby,
        today=today,
        next_week=next_week,
        total_overtime_hours=total_overtime_hours,
        month_name=month_name,
        year=year,
        recent_overrides=recent_overrides,
        recent_overtime=recent_overtime,
        team_members=team_members,
        today_dt=today_dt,
        get_standby_person=get_standby_person,
        timedelta=timedelta,
        notifications=notifications,
        monthly_overtime_limit=monthly_overtime_limit,
        config=config
    )

@standby_bp.route('/calendar')
@login_required
def calendar():
    try:
        # Check and promote future rotation if due
        department_id = current_user.department.id if current_user.department else None
        if department_id:
            from .utils.rotation_planner import promote_future_rotation_if_due
            promoted, regenerated_count = promote_future_rotation_if_due(department_id)
            if promoted:
                print(f"Promoted future rotation and regenerated {regenerated_count} assignments")
        
        # Determine current month and year
        today = datetime.today()
        year = request.args.get('year', today.year, type=int)
        month = request.args.get('month', today.month, type=int)
        
        # Validate year and month
        if year < 1900 or year > 2100:
            year = today.year
        if month < 1 or month > 12:
            month = today.month
        
        # First and last day of the month
        first_day = datetime(year, month, 1)
        if month == 12:
            next_month = datetime(year + 1, 1, 1)
        else:
            next_month = datetime(year, month + 1, 1)
        num_days = (next_month - first_day).days
        
        # Get department ID for rotation calculation
        department_id = current_user.department.id if current_user.department else None
        
        # Load roster data for colors
        roster_data = load_roster(department_id)
        team_members = {m['name']: m.get('color', '#6c757d') for m in roster_data.get('team_members', [])}
        person_colors = {**config.DEFAULT_PERSON_COLORS, **team_members}
        
        events = []
        today_str = today.strftime('%Y-%m-%d')
        
        for i in range(num_days):
            day = first_day + timedelta(days=i)
            date_str = day.strftime('%Y-%m-%d')
            person = get_standby_person(date_str, department_id)
            
            if person:
                # Determine if this is today, past, or future
                is_today = date_str == today_str
                is_past = date_str < today_str
                
                event_data = {
                    'title': person,
                    'start': date_str,
                    'end': date_str,  # single-day event
                    'color': person_colors.get(person, '#6c757d'),
                    'extendedProps': {
                        'isToday': is_today,
                        'isPast': is_past,
                        'isOverride': date_str in roster_data.get('overrides', {})
                    }
                }
                
                # Add special styling for today
                if is_today:
                    event_data['classNames'] = ['fc-event-today']
                
                events.append(event_data)
        
        return render_template('standby/calendar.html', events=events, config=config)
        
    except Exception as e:
        # Log the error for debugging
        print(f"Calendar error: {e}")
        # Return a minimal template with error handling
        return render_template('standby/calendar.html', events=[], config=config)

@standby_bp.route('/api/calendar/<int:year>/<int:month>')
@login_required
def api_calendar(year, month):
    """API endpoint for calendar data"""
    try:
        # Validate year and month
        if year < 1900 or year > 2100 or month < 1 or month > 12:
            return jsonify({'error': 'Invalid year or month'}), 400
        
        # First and last day of the month
        first_day = datetime(year, month, 1)
        if month == 12:
            next_month = datetime(year + 1, 1, 1)
        else:
            next_month = datetime(year, month + 1, 1)
        num_days = (next_month - first_day).days
        
        # Get department ID for rotation calculation
        department_id = current_user.department.id if current_user.department else None
        
        # Load roster data for colors
        roster_data = load_roster(department_id)
        team_members = {m['name']: m.get('color', '#6c757d') for m in roster_data.get('team_members', [])}
        person_colors = {**config.DEFAULT_PERSON_COLORS, **team_members}
        
        events = []
        today = datetime.today()
        today_str = today.strftime('%Y-%m-%d')
        
        for i in range(num_days):
            day = first_day + timedelta(days=i)
            date_str = day.strftime('%Y-%m-%d')
            person = get_standby_person(date_str, department_id)
            
            if person:
                # Determine if this is today, past, or future
                is_today = date_str == today_str
                is_past = date_str < today_str
                
                event_data = {
                    'title': person,
                    'start': date_str,
                    'end': date_str,  # single-day event
                    'color': person_colors.get(person, '#6c757d'),
                    'extendedProps': {
                        'isToday': is_today,
                        'isPast': is_past,
                        'isOverride': date_str in roster_data.get('overrides', {})
                    }
                }
                
                # Add special styling for today
                if is_today:
                    event_data['classNames'] = ['fc-event-today']
                
                events.append(event_data)
        
        return jsonify(events)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@standby_bp.route('/roster', methods=['GET'])
@login_required
def roster():
    # Get users from the same department for dropdown, excluding those who are already standby members
    from models import User, StandbyMember
    
    # Get current user's department
    department_id = current_user.department.id if current_user.department else None
    
    if department_id:
        # Get standby user IDs from the same department
        standby_user_ids = [
            member.user_id for member in StandbyMember.query.join(User).filter(
                User.department_id == department_id
            ).all()
        ]
        
        # Get available users from the same department
        if standby_user_ids:
            all_users = User.query.filter(
                and_(
                    User.department_id == department_id,
                    ~User.id.in_(standby_user_ids)
                )
            ).all()
        else:
            all_users = User.query.filter(User.department_id == department_id).all()
    else:
        # If user has no department, only show users without departments
        standby_user_ids = [
            member.user_id for member in StandbyMember.query.join(User).filter(
                User.department_id.is_(None)
            ).all()
        ]
        
        if standby_user_ids:
            all_users = User.query.filter(
                and_(
                    User.department_id.is_(None),
                    ~User.id.in_(standby_user_ids)
                )
            ).all()
        else:
            all_users = User.query.filter(User.department_id.is_(None)).all()
    
    # Get inactive members for reactivation (from same department)
    inactive_members = []
    if department_id:
        inactive_query = StandbyMember.query.filter_by(active=False).join(User).filter(
            User.department_id == department_id
        )
    else:
        inactive_query = StandbyMember.query.filter_by(active=False).join(User).filter(
            User.department_id.is_(None)
        )
    
    for member in inactive_query.all():
        inactive_members.append({
            'username': member.user.username,
            'color': member.color
        })
    
    roster_data = load_roster(department_id)
    team_members = roster_data.get('team_members', [])
    overrides = roster_data.get('overrides', {})
    rotation = roster_data.get('rotation', [])
    today = datetime.today().strftime('%Y-%m-%d')
    today_date = datetime.today().date()
    
    # Check if user is admin
    is_admin = is_admin_user(current_user)
    
    # Get duration configuration if admin
    duration_config_obj = None
    if is_admin:
        from models import StandbyDurationConfig
        department = current_user.department
        if department:
            duration_config_obj = StandbyDurationConfig.query.filter_by(department_id=department.id).first()
    
    return render_template('standby/roster.html', 
                         team_members=team_members, 
                         overrides=overrides, 
                         rotation=rotation, 
                         all_users=all_users, 
                         inactive_members=inactive_members, 
                         today=today,
                         today_date=today_date,
                         is_admin=is_admin,
                         duration_config=duration_config_obj)

@standby_bp.route('/roster/add_member', methods=['POST'])
@login_required
def add_member():
    name = request.form.get('name')
    color = request.form.get('color', '#007bff')
    active = bool(request.form.get('active'))
    
    try:
        add_team_member(name, color, active)
        flash('Team member added!', 'success')
    except ValueError as e:
        flash(f'Error: {e}', 'warning')
    
    return redirect(url_for('standby.roster'))

@standby_bp.route('/roster/add_override', methods=['POST'])
@login_required
def add_override_route():
    start_date = request.form.get('override_start_date')
    end_date = request.form.get('override_end_date')
    person = request.form.get('override_person')
    
    if not start_date or not end_date or not person:
        flash('Start date, end date, and person are required for override.', 'warning')
        return redirect(url_for('standby.roster'))
    
    try:
        from .utils.assignment_rotation_manager import AssignmentRotationManager
        department_id = current_user.department.id if current_user.department else None
        # Add overrides for each date in the range
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        current = start
        while current <= end:
            date_str = current.strftime('%Y-%m-%d')
            add_override(date_str, person, created_by_username=current_user.username)
            # Also update/create the assignment for the override
            AssignmentRotationManager.create_manual_assignment(date_str, person, department_id)
            current += timedelta(days=1)
        
        flash(f'Override added for {start_date} to {end_date}!', 'success')
    except ValueError as e:
        flash(f'Error: {e}', 'warning')
    
    return redirect(url_for('standby.roster'))

@standby_bp.route('/roster/remove_override', methods=['POST'])
@login_required
def remove_override_route():
    date = request.form.get('date')
    
    try:
        from .utils.assignment_rotation_manager import AssignmentRotationManager
        from models import StandbyOverride, StandbyAssignment
        department_id = current_user.department.id if current_user.department else None
        
        # Get the override to find the original assignment
        override_date = datetime.strptime(date, '%Y-%m-%d').date()
        override = StandbyOverride.query.filter_by(date=override_date).first()
        
        if not override:
            flash(f'No override found for {date}.', 'warning')
            return redirect(url_for('standby.roster'))
        
        # Store the original user ID before removing the override
        original_user_id = override.original_user_id
        
        remove_override(date)
        
        # Restore the original assignment if we have the original user ID
        if department_id and original_user_id:
            # Update or create the assignment with the original user
            existing_assignment = StandbyAssignment.query.filter_by(
                department_id=department_id,
                date=override_date
            ).first()
            
            if existing_assignment:
                existing_assignment.user_id = original_user_id
            else:
                # Create new assignment with original user
                assignment = StandbyAssignment(
                    department_id=department_id,
                    user_id=original_user_id,
                    date=override_date
                )
                db.session.add(assignment)
            
            db.session.commit()
            flash(f'Override for {date} removed and original assignment restored.', 'success')
        else:
            # If we don't have the original user ID, regenerate based on rotation
            if department_id:
                AssignmentRotationManager._generate_assignment_for_date(override_date, department_id)
            flash(f'Override for {date} removed.', 'success')
        
    except ValueError as e:
        flash(f'Error: {e}', 'warning')
    
    return redirect(url_for('standby.roster'))

@standby_bp.route('/roster/toggle_member', methods=['POST'])
@login_required
def toggle_member():
    name = request.form.get('name')
    
    try:
        member = get_standby_member_by_username(name)
        if member:
            update_team_member(name, active=not member.active)
            status = 'activated' if not member.active else 'deactivated'
            flash(f'{name} {status}.', 'success')
        else:
            flash(f'Team member {name} not found.', 'warning')
    except ValueError as e:
        flash(f'Error: {e}', 'warning')
    
    return redirect(url_for('standby.roster'))

@standby_bp.route('/roster/toggle_rotation', methods=['POST'])
@login_required
def toggle_rotation():
    name = request.form.get('name')
    add_to_rotation = request.form.get('add_to_rotation', 'false').lower() == 'true'
    
    try:
        from models import User, StandbyMember
        user = User.query.filter_by(username=name).first()
        if user:
            standby_member = StandbyMember.query.filter_by(user_id=user.id).first()
            if standby_member and standby_member.active:
                # Get department ID for assignment regeneration
                department_id = user.department.id if user.department else None
                
                if add_to_rotation:
                    # Add to rotation
                    max_order = db.session.query(db.func.max(StandbyMember.rotation_order)).scalar()
                    new_order = (max_order or 0) + 1
                    standby_member.rotation_order = new_order
                    db.session.commit()
                    
                    # Regenerate future assignments
                    if department_id:
                        try:
                            from .utils.assignment_rotation_manager import AssignmentRotationManager
                            regenerated_count = AssignmentRotationManager.regenerate_future_assignments(department_id)
                            print(f"Regenerated {regenerated_count} future assignments after adding {name} to rotation")
                        except Exception as e:
                            print(f"Warning: Failed to regenerate future assignments: {e}")
                    
                    return jsonify({'success': True, 'message': f'{name} added to rotation'})
                else:
                    # Remove from rotation
                    standby_member.rotation_order = None
                    db.session.commit()
                    
                    # Regenerate future assignments
                    if department_id:
                        try:
                            from .utils.assignment_rotation_manager import AssignmentRotationManager
                            regenerated_count = AssignmentRotationManager.regenerate_future_assignments(department_id)
                            print(f"Regenerated {regenerated_count} future assignments after removing {name} from rotation")
                        except Exception as e:
                            print(f"Warning: Failed to regenerate future assignments: {e}")
                    
                    return jsonify({'success': True, 'message': f'{name} removed from rotation'})
            else:
                return jsonify({'success': False, 'message': f'{name} is not an active standby member'}), 400
        else:
            return jsonify({'success': False, 'message': f'User {name} not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@standby_bp.route('/roster/update_rotation', methods=['POST'])
@login_required
def update_rotation():
    # Always get the current rotation order from the form
    rotation = request.form.getlist('rotation[]')

    # Handle add person (only if not already in rotation)
    add_person = request.form.get('add')
    if add_person:
        if add_person not in rotation:
            try:
                # Add to rotation by updating the member's rotation_order
                from models import User, StandbyMember
                user = User.query.filter_by(username=add_person).first()
                if user:
                    standby_member = StandbyMember.query.filter_by(user_id=user.id).first()
                    if standby_member and standby_member.active:
                        # Find the next available rotation order
                        max_order = db.session.query(db.func.max(StandbyMember.rotation_order)).scalar()
                        new_order = (max_order or 0) + 1
                        standby_member.rotation_order = new_order
                        db.session.commit()
                        flash(f'{add_person} added to rotation!', 'success')
                    else:
                        flash(f'{add_person} is not an active standby member.', 'warning')
                else:
                    flash(f'User {add_person} not found.', 'warning')
            except Exception as e:
                flash(f'Error adding {add_person} to rotation: {e}', 'warning')
        else:
            flash(f'{add_person} is already in rotation.', 'warning')
        return redirect(url_for('standby.roster'))

    # Handle move action
    move = request.form.get('move')
    if move:
        direction, index = move.split(':')
        index = int(index)
        if direction == 'up' and index > 0:
            rotation[index], rotation[index - 1] = rotation[index - 1], rotation[index]
            flash(f"Moved {rotation[index]} up!", 'success')
        elif direction == 'down' and index < len(rotation) - 1:
            rotation[index], rotation[index + 1] = rotation[index + 1], rotation[index]
            flash(f"Moved {rotation[index]} down!", 'success')
        
        # Update rotation order in database
        try:
            update_rotation_order(rotation)
        except Exception as e:
            flash(f'Error updating rotation: {e}', 'warning')
        return redirect(url_for('standby.roster'))

    # Handle removal
    remove = request.form.get('remove')
    if remove:
        if remove in rotation:
            try:
                # Remove from rotation by setting rotation_order to None
                from models import User, StandbyMember
                user = User.query.filter_by(username=remove).first()
                if user:
                    standby_member = StandbyMember.query.filter_by(user_id=user.id).first()
                    if standby_member:
                        standby_member.rotation_order = None
                        db.session.commit()
                        flash(f'Removed {remove} from rotation!', 'success')
                    else:
                        flash(f'{remove} not found in standby members.', 'warning')
                else:
                    flash(f'User {remove} not found.', 'warning')
            except Exception as e:
                flash(f'Error removing {remove} from rotation: {e}', 'warning')
        else:
            flash(f'{remove} not found in rotation.', 'warning')
        return redirect(url_for('standby.roster'))

    # Save on explicit save click
    if request.form.get('save'):
        try:
            update_rotation_order(rotation)
            flash('Rotation updated!', 'success')
        except Exception as e:
            flash(f'Error updating rotation: {e}', 'warning')
        return redirect(url_for('standby.roster'))

    # Default: just redirect
    return redirect(url_for('standby.roster'))

@standby_bp.route('/roster/duration-config', methods=['GET', 'POST'])
@login_required
@admin_required
def duration_config():
    """Manage standby duration configuration for the department."""
    from models import StandbyDurationConfig, Department
    from .utils.assignment_rotation_manager import AssignmentRotationManager
    
    # Get current user's department
    department = current_user.department
    if not department:
        flash('You must be assigned to a department to configure standby settings.', 'error')
        return redirect(url_for('standby.roster'))
    
    # Get or create configuration for this department
    config_obj = StandbyDurationConfig.query.filter_by(department_id=department.id).first()
    
    if request.method == 'POST':
        try:
            # Store old values for comparison
            old_rotation_start_date = None
            old_standby_shift_days = None
            
            if config_obj:
                old_rotation_start_date = config_obj.rotation_start_date
                old_standby_shift_days = config_obj.standby_shift_days
            
            if not config_obj:
                # Create new configuration
                config_obj = StandbyDurationConfig(
                    department_id=department.id,
                    created_by_id=current_user.id,
                    updated_by_id=current_user.id
                )
                db.session.add(config_obj)
            
            # Update configuration values
            new_standby_shift_days = int(request.form.get('standby_shift_days', 1))
            config_obj.standby_shift_days = new_standby_shift_days
            config_obj.monthly_overtime_limit = float(request.form.get('monthly_overtime_limit', 40.0))
            config_obj.overtime_warning_threshold = float(request.form.get('overtime_warning_threshold', 35.0))
            config_obj.dashboard_refresh_interval = int(request.form.get('dashboard_refresh_interval', 300))
            config_obj.notification_auto_dismiss = int(request.form.get('notification_auto_dismiss', 10))
            config_obj.updated_by_id = current_user.id
            
            # Handle rotation start date
            rotation_start_date = request.form.get('rotation_start_date')
            if rotation_start_date:
                new_rotation_start_date = datetime.strptime(rotation_start_date, '%Y-%m-%d').date()
                config_obj.rotation_start_date = new_rotation_start_date
            
            db.session.commit()
            
            # Check if rotation pattern changed and regenerate future assignments
            pattern_changed = False
            start_date_changed = False
            shift_days_changed = False
            
            if old_rotation_start_date and old_rotation_start_date != config_obj.rotation_start_date:
                pattern_changed = True
                start_date_changed = True
            if old_standby_shift_days and old_standby_shift_days != new_standby_shift_days:
                pattern_changed = True
                shift_days_changed = True
            
            if pattern_changed:
                try:
                    # Check if rotation start date is in the future
                    today = datetime.now().date()
                    start_date_in_future = config_obj.rotation_start_date > today
                    
                    regenerated_count = AssignmentRotationManager.regenerate_future_assignments(department.id)
                    
                    if start_date_changed:
                        if start_date_in_future:
                            flash(f'Configuration updated! Calendar updated with {regenerated_count} future assignments. Dashboard will update when rotation start date ({config_obj.rotation_start_date.strftime("%B %d, %Y")}) is reached.', 'success')
                        else:
                            flash(f'Configuration updated! Calendar and dashboard updated with {regenerated_count} assignments. Rotation start date changed to {config_obj.rotation_start_date.strftime("%B %d, %Y")}.', 'success')
                    elif shift_days_changed:
                        flash(f'Configuration updated! Standby shift duration changed to {new_standby_shift_days} days. Regenerated {regenerated_count} future assignments.', 'success')
                    else:
                        flash(f'Configuration updated! Regenerated {regenerated_count} future assignments.', 'success')
                        
                except Exception as e:
                    flash(f'Configuration saved but failed to regenerate assignments: {e}', 'warning')
            else:
                flash('Standby duration configuration updated successfully!', 'success')
            
        except ValueError as e:
            flash(f'Invalid input: {e}', 'error')
        except Exception as e:
            flash(f'Error saving configuration: {e}', 'error')
            db.session.rollback()
    
    return render_template('standby/duration_config.html', 
                         config=config_obj,
                         department=department)

@standby_bp.route('/save-rotation', methods=['POST'])
@login_required
def save_rotation():
    """Save rotation order via JSON API with intelligent calendar/dashboard updates"""
    try:
        # Get JSON data from request
        data = request.get_json()
        if not data or 'rotation' not in data:
            return jsonify({'success': False, 'message': 'Invalid request data'}), 400
        
        rotation = data['rotation']
        apply_mode = data.get('apply_mode', 'immediate')  # 'immediate' or 'after_cycle'
        
        # Validate rotation data
        if not isinstance(rotation, list):
            return jsonify({'success': False, 'message': 'Rotation must be a list'}), 400
        
        # Get department ID for the current user
        department_id = current_user.department.id if current_user.department else None
        if not department_id:
            return jsonify({'success': False, 'message': 'User not associated with a department'}), 400
        
        # Import rotation planner utilities
        from .utils.rotation_planner import (
            create_future_rotation_plan, 
            calculate_rotation_cycle_end,
            delete_future_rotation_plan
        )
        
        if apply_mode == 'after_cycle':
            # Calculate when the current cycle ends
            start_date = calculate_rotation_cycle_end(department_id)
            if not start_date:
                return jsonify({'success': False, 'message': 'Unable to calculate rotation cycle end date'}), 400
            
            # Delete any existing future rotation plan
            delete_future_rotation_plan(department_id)
            
            # Save the plan
            create_future_rotation_plan(
                department_id=department_id,
                rotation_order=rotation,
                start_date=start_date,
                created_by_id=current_user.id
            )
            
            return jsonify({
                'success': True,
                'message': f'Planned rotation will take effect on {start_date.strftime("%Y-%m-%d")}.',
                'rotation': rotation,
                'calendar_updated': False,
                'dashboard_updated': False,
                'start_date_in_future': True,
                'planned_rotation': True
            })
        else:
            # Immediate application - existing logic
            # Get current rotation configuration
            from models import StandbyDurationConfig
            config = StandbyDurationConfig.query.filter_by(department_id=department_id).first()
            
            # Check if rotation start date is in the future
            today = datetime.now().date()
            start_date_in_future = False
            
            if config and config.rotation_start_date:
                start_date_in_future = config.rotation_start_date > today
            
            # Update rotation order in database
            update_rotation_order(rotation)
            
            # Delete any existing future rotation plan since we're applying immediately
            delete_future_rotation_plan(department_id)
            
            # Determine what to update based on start date
            update_info = {
                'calendar_updated': False,
                'dashboard_updated': False,
                'message': 'Rotation saved successfully'
            }
            
            if start_date_in_future:
                # Only update calendar (future assignments)
                try:
                    from .utils.assignment_rotation_manager import AssignmentRotationManager
                    regenerated_count = AssignmentRotationManager.regenerate_future_assignments(department_id)
                    update_info['calendar_updated'] = True
                    update_info['message'] = f'Rotation saved! Calendar updated with {regenerated_count} future assignments. Dashboard will update when rotation start date is reached.'
                except Exception as e:
                    update_info['message'] = f'Rotation saved but failed to update calendar: {str(e)}'
            else:
                # Update both calendar and dashboard (affects current assignments)
                try:
                    from .utils.assignment_rotation_manager import AssignmentRotationManager
                    regenerated_count = AssignmentRotationManager.regenerate_future_assignments(department_id)
                    update_info['calendar_updated'] = True
                    update_info['dashboard_updated'] = True
                    update_info['message'] = f'Rotation saved! Calendar and dashboard updated with {regenerated_count} assignments.'
                except Exception as e:
                    update_info['message'] = f'Rotation saved but failed to update assignments: {str(e)}'
            
            return jsonify({
                'success': True, 
                'message': update_info['message'],
                'rotation': rotation,
                'calendar_updated': update_info['calendar_updated'],
                'dashboard_updated': update_info['dashboard_updated'],
                'start_date_in_future': start_date_in_future,
                'planned_rotation': False
            })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error saving rotation: {str(e)}'}), 500

@standby_bp.route('/overtime', methods=['GET', 'POST'])
@login_required
def overtime():
    now = datetime.now()
    year, month = now.year, now.month
    
    # Get department ID for roster filtering
    department_id = current_user.department.id if current_user.department else None
    roster_data = load_roster(department_id)
    team_members = [m for m in roster_data.get('team_members', []) if m.get('active', True)]

    # For GET
    selected_person = request.args.get('person')
    if selected_person is None:
        today_str = now.strftime('%Y-%m-%d')
        selected_person = get_standby_person(today_str, department_id)

    if request.method == 'POST':
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        issue_description = request.form.get('issue_description', '')
        resolution_notes = request.form.get('resolution_notes', '')

        # Get current standby user
        current_user_name = current_user.username
        
        # Use current user for the overtime entry
        person = current_user_name

        valid, duration_or_msg = validate_overtime_entry(start_time, end_time)
        if valid:
            entry = {
                'person': person,
                'start_time': start_time,
                'end_time': end_time,
                'duration_hours': f"{duration_or_msg:.2f}",
                'issue_description': issue_description,
                'resolution_notes': resolution_notes
            }
            save_overtime_entry(person, year, month, entry)
            flash('Overtime entry saved!', 'success')
        else:
            flash(duration_or_msg, 'danger')

        return redirect(url_for('standby.overtime', person=person))

    # Updated logic for 'All Team Members'
    if selected_person == '':
        # Get all overtime logs for the month
        overtime_logs = get_all_overtime_logs(year, month)
    else:
        overtime_logs = load_overtime_logs(selected_person, year, month)

    # Calculate total hours
    total_hours = 0.0
    for log in overtime_logs:
        if log.get('duration_hours'):
            try:
                total_hours += float(log['duration_hours'])
            except (ValueError, TypeError):
                pass
    
    # Get current standby user
    current_user_name = current_user.username
    
    return render_template('standby/overtime.html',
                           overtime_logs=overtime_logs,
                           team_members=team_members,
                           selected_person=selected_person,
                           total_hours=total_hours,
                           current_user=current_user_name)

# API endpoints
@standby_bp.route('/api/current-standby')
@login_required
def api_current_standby():
    """API endpoint to get current standby person"""
    try:
        today = datetime.today().strftime('%Y-%m-%d')
        department_id = current_user.department.id if current_user.department else None
        current_standby = get_standby_person(today, department_id)
        return jsonify({
            'current_standby': current_standby,
            'date': today
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@standby_bp.route('/api/total-hours')
@login_required
def api_total_hours():
    """API endpoint to get total overtime hours for current month"""
    try:
        now = datetime.now()
        year, month = now.year, now.month
        
        # Get current standby user
        current_user_name = current_user.username
        
        # Load overtime logs for current user and month
        overtime_logs = load_overtime_logs(current_user_name, year, month)
        total_hours = sum(float(log.get('duration_hours', 0)) for log in overtime_logs)
        
        return jsonify({
            'total_hours': round(total_hours, 1),
            'month': month,
            'year': year,
            'user': current_user_name
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@standby_bp.route('/api/upcoming-rotation')
@login_required
def api_upcoming_rotation():
    """API endpoint to get the upcoming planned rotation"""
    try:
        department_id = current_user.department.id if current_user.department else None
        if not department_id:
            return jsonify({'upcoming': None})
        
        from .utils.rotation_planner import get_active_future_rotation_plan
        plan = get_active_future_rotation_plan(department_id)
        
        if not plan:
            return jsonify({'upcoming': None})
        
        return jsonify({
            'upcoming': {
                'rotation_order': plan.get_rotation_list(),
                'start_date': plan.start_date.isoformat(),
                'notes': plan.notes,
                'created_by': plan.created_by.username if plan.created_by else None
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@standby_bp.route('/roster/edit_member', methods=['POST'])
@login_required
def edit_member():
    name_original = request.form.get('name_original')
    name = request.form.get('name')
    color = request.form.get('color')
    active = bool(request.form.get('active'))
    
    try:
        # Update the team member using database functions
        update_team_member(name_original, color=color, active=active)
        
        # If the name was changed, we need to handle that separately
        if name != name_original:
            # For now, we'll just update the color and active status
            # Name changes would require more complex logic to handle rotation updates
            flash(f'Team member {name_original} updated! (Note: Name changes are not yet supported)', 'success')
        else:
            flash(f'Team member {name_original} updated!', 'success')
            
    except ValueError as e:
        flash(f'Error: {e}', 'warning')
    
    return redirect(url_for('standby.roster'))

@standby_bp.route('/api/roster-notifications')
@login_required
def api_roster_notifications():
    """API endpoint to get roster-related notifications"""
    try:
        # Get department ID for roster filtering
        department_id = current_user.department.id if current_user.department else None
        roster_data = load_roster(department_id)
        team_members = roster_data.get('team_members', [])
        overrides = roster_data.get('overrides', {})
        
        # Count inactive members
        inactive_count = sum(1 for member in team_members if not member.get('active', True))
        
        # Count recent overrides (last 7 days)
        today = datetime.today()
        recent_overrides = 0
        for date_str in overrides.keys():
            try:
                override_date = datetime.strptime(date_str, '%Y-%m-%d')
                if (today - override_date).days <= 7:
                    recent_overrides += 1
            except ValueError:
                continue
        
        # Count rotation changes (if any)
        rotation_changes = 0  # This could be enhanced with a change log
        
        total_notifications = inactive_count + recent_overrides + rotation_changes
        
        return jsonify({
            'count': total_notifications,
            'inactive_members': inactive_count,
            'recent_overrides': recent_overrides,
            'rotation_changes': rotation_changes
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@standby_bp.route('/api/overtime-notifications')
@login_required
def api_overtime_notifications():
    """API endpoint to get overtime-related notifications"""
    try:
        now = datetime.now()
        year, month = now.year, now.month
        
        # Get current standby user
        current_user_name = current_user.username
        
        # Load overtime logs for current user and month
        overtime_logs = load_overtime_logs(current_user_name, year, month)
        
        # Count recent overtime entries (last 24 hours)
        yesterday = now - timedelta(days=1)
        recent_entries = 0
        high_hours_warning = 0
        
        total_hours = 0
        for log in overtime_logs:
            try:
                hours = float(log.get('duration_hours', 0))
                total_hours += hours
                
                # Check for recent entries
                start_time_str = log.get('start_time', '')
                if start_time_str:
                    start_time = datetime.strptime(start_time_str, '%Y-%m-%d %H:%M')
                    if start_time >= yesterday:
                        recent_entries += 1
            except (ValueError, TypeError):
                continue
        
        # Check for high hours warning
        if total_hours > config.OVERTIME_WARNING_THRESHOLD:
            high_hours_warning = 1
        
        total_notifications = recent_entries + high_hours_warning
        
        return jsonify({
            'count': total_notifications,
            'recent_entries': recent_entries,
            'high_hours_warning': high_hours_warning,
            'total_hours': round(total_hours, 1)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@standby_bp.route('/overtime/edit/<person>/<int:year>/<int:month>/<entry_id>', methods=['GET', 'POST'])
@login_required
def edit_overtime_entry(person, year, month, entry_id):
    if request.method == 'GET':
        logs = load_overtime_logs(person, year, month)
        log = next((l for l in logs if l.get('id') == entry_id), None)
        if log:
            return jsonify(log)
        else:
            return jsonify({'error': 'Log not found'}), 404
    elif request.method == 'POST':
        # Get updated fields from form
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        issue_description = request.form.get('issue_description', '')
        resolution_notes = request.form.get('resolution_notes', '')
        valid, duration_or_msg = validate_overtime_entry(start_time, end_time)
        if not valid:
            flash(duration_or_msg, 'danger')
            return redirect(url_for('standby.overtime', person=person))
        updated_entry = {
            'start_time': start_time,
            'end_time': end_time,
            'duration_hours': f"{duration_or_msg:.2f}",
            'issue_description': issue_description,
            'resolution_notes': resolution_notes
        }
        updated = update_overtime_entry(person, year, month, entry_id, updated_entry)
        if updated:
            flash('Overtime entry updated!', 'success')
        else:
            flash('Log not found.', 'danger')
        return redirect(url_for('standby.overtime', person=person))

@standby_bp.route('/roster/remove_member', methods=['POST'])
@login_required
def remove_member():
    name = request.form.get('name')
    if not name:
        flash('No member specified.', 'danger')
        return redirect(url_for('standby.roster'))
    try:
        from models import User, StandbyMember
        user = User.query.filter_by(username=name).first()
        if user:
            standby_member = StandbyMember.query.filter_by(user_id=user.id).first()
            if standby_member:
                # Remove the member from the team (delete or deactivate)
                db.session.delete(standby_member)
                db.session.commit()
                flash(f'{name} removed from the team.', 'success')
            else:
                flash(f'{name} is not a standby member.', 'warning')
        else:
            flash(f'User {name} not found.', 'warning')
    except Exception as e:
        flash(f'Error removing {name}: {e}', 'danger')
    return redirect(url_for('standby.roster'))
