from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import os
import json
from .utils.rotation_manager import get_standby_person, load_roster, save_roster
from .utils.overtime_logger import load_overtime_logs, validate_overtime_entry, save_overtime_entry, update_overtime_entry
from .config import StandbyConfig

# Create blueprint
standby_bp = Blueprint('standby', __name__, url_prefix='/standby')

# Initialize config
config = StandbyConfig()

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
    # Get current standby user
    current_user_name = current_user.username
    today_dt = datetime.today()
    today = today_dt.strftime('%Y-%m-%d')
    next_week_dt = today_dt + timedelta(days=7)
    next_week = next_week_dt.strftime('%Y-%m-%d')
    current_standby = get_standby_person(today)
    next_standby = get_standby_person(next_week)
    year = today_dt.year
    month = today_dt.month
    month_name = today_dt.strftime('%B')
    
    # Load and sum overtime logs for this month
    overtime_logs = load_overtime_logs(current_user_name, year, month)
    total_overtime_hours = sum(float(log.get('duration_hours', 0)) for log in overtime_logs)
    
    # Load roster data for team members and overrides
    roster_data = load_roster()
    team_members = [m for m in roster_data.get('team_members', []) if m.get('active', True)]
    overrides = roster_data.get('overrides', {})
    
    # Sort overrides by date descending, get 5 most recent
    sorted_overrides = sorted(overrides.items(), key=lambda x: x[0], reverse=True)
    recent_overrides = [
        {'date': date, 'person': person}
        for date, person in sorted_overrides[:5]
    ]
    
    # Get recent overtime activity (last 5 entries across all team members)
    recent_overtime = []
    for member in team_members:
        member_logs = load_overtime_logs(member['name'], year, month)
        recent_overtime.extend(member_logs[:2])  # Get 2 most recent per member

    # Add year and month fields to each log in recent_overtime
    for log in recent_overtime:
        start_time = log.get('start_time', '')
        if start_time:
            date_part = start_time.split('T')[0] if 'T' in start_time else start_time.split(' ')[0]
            parts = date_part.split('-')
            if len(parts) == 3:
                log['year'] = parts[0]
                log['month'] = int(parts[1])
            else:
                log['year'] = ''
                log['month'] = ''
        else:
            log['year'] = ''
            log['month'] = ''

    # Sort by start time and get 5 most recent
    recent_overtime.sort(key=lambda x: x.get('start_time', ''), reverse=True)
    recent_overtime = recent_overtime[:5]
    
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
        
        # Load roster data for colors
        roster_data = load_roster()
        team_members = {m['name']: m.get('color', '#6c757d') for m in roster_data.get('team_members', [])}
        person_colors = {**config.DEFAULT_PERSON_COLORS, **team_members}
        
        events = []
        today_str = today.strftime('%Y-%m-%d')
        
        for i in range(num_days):
            day = first_day + timedelta(days=i)
            date_str = day.strftime('%Y-%m-%d')
            person = get_standby_person(date_str)
            
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
        
        # Load roster data for colors
        roster_data = load_roster()
        team_members = {m['name']: m.get('color', '#6c757d') for m in roster_data.get('team_members', [])}
        person_colors = {**config.DEFAULT_PERSON_COLORS, **team_members}
        
        events = []
        today = datetime.today()
        today_str = today.strftime('%Y-%m-%d')
        
        for i in range(num_days):
            day = first_day + timedelta(days=i)
            date_str = day.strftime('%Y-%m-%d')
            person = get_standby_person(date_str)
            
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
    roster_data = load_roster()
    team_members = roster_data.get('team_members', [])
    overrides = roster_data.get('overrides', {})
    rotation = roster_data.get('rotation', [])
    today = datetime.today().strftime('%Y-%m-%d')
    return render_template('standby/roster.html', team_members=team_members, overrides=overrides, rotation=rotation, today=today)

@standby_bp.route('/roster/add_member', methods=['POST'])
@login_required
def add_member():
    roster_data = load_roster()
    team_members = roster_data.get('team_members', [])
    name = request.form.get('name')
    color = request.form.get('color')
    active = bool(request.form.get('active'))
    # Prevent duplicate names
    if any(m.get('name') == name for m in team_members):
        flash('Member with this name already exists.', 'warning')
        return redirect(url_for('standby.roster'))
    team_members.append({'name': name, 'color': color, 'active': active})
    roster_data['team_members'] = team_members
    save_roster(roster_data)
    flash('Team member added!', 'success')
    return redirect(url_for('standby.roster'))

@standby_bp.route('/roster/add_override', methods=['POST'])
@login_required
def add_override():
    roster_data = load_roster()
    overrides = roster_data.get('overrides', {})
    start_date = request.form.get('override_start_date')
    end_date = request.form.get('override_end_date')
    person = request.form.get('override_person')
    
    if not start_date or not end_date or not person:
        flash('Start date, end date, and person are required for override.', 'warning')
        return redirect(url_for('standby.roster'))
    
    # Add overrides for each date in the range
    from datetime import datetime, timedelta
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    
    current = start
    while current <= end:
        date_str = current.strftime('%Y-%m-%d')
        overrides[date_str] = person
        current += timedelta(days=1)
    
    roster_data['overrides'] = overrides
    save_roster(roster_data)
    flash(f'Override added for {start_date} to {end_date}!', 'success')
    return redirect(url_for('standby.roster'))

@standby_bp.route('/roster/remove_override', methods=['POST'])
@login_required
def remove_override():
    roster_data = load_roster()
    date = request.form.get('date')
    overrides = roster_data.get('overrides', {})
    if date in overrides:
        overrides.pop(date)
        roster_data['overrides'] = overrides
        save_roster(roster_data)
        flash(f'Override for {date} removed.', 'success')
    else:
        flash('Override not found.', 'warning')
    return redirect(url_for('standby.roster'))

@standby_bp.route('/roster/toggle_member', methods=['POST'])
@login_required
def toggle_member():
    roster_data = load_roster()
    name = request.form.get('name')
    for member in roster_data.get('team_members', []):
        if member.get('name') == name:
            member['active'] = not member.get('active', True)
            break
    save_roster(roster_data)
    flash(f'{name} status toggled.', 'success')
    return redirect(url_for('standby.roster'))

@standby_bp.route('/roster/update_rotation', methods=['POST'])
@login_required
def update_rotation():
    roster_data = load_roster()
    # Always get the current rotation order from the form
    rotation = request.form.getlist('rotation[]')

    # Handle add person (only if not already in rotation)
    add_person = request.form.get('add')
    if add_person:
        if add_person not in rotation:
            rotation.append(add_person)
            roster_data['rotation'] = rotation
            save_roster(roster_data)
            flash(f'{add_person} added to rotation!', 'success')
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
        roster_data['rotation'] = rotation
        save_roster(roster_data)
        return redirect(url_for('standby.roster'))

    # Handle removal
    remove = request.form.get('remove')
    if remove:
        if remove in rotation:
            rotation.remove(remove)
            roster_data['rotation'] = rotation
            save_roster(roster_data)
            flash(f'Removed {remove} from rotation!', 'success')
        else:
            flash(f'{remove} not found in rotation.', 'warning')
        return redirect(url_for('standby.roster'))

    # Save on explicit save click
    if request.form.get('save'):
        roster_data['rotation'] = rotation
        save_roster(roster_data)
        flash('Rotation updated!', 'success')
        return redirect(url_for('standby.roster'))

    # Default: just redirect
    return redirect(url_for('standby.roster'))

@standby_bp.route('/overtime', methods=['GET', 'POST'])
@login_required
def overtime():
    now = datetime.now()
    year, month = now.year, now.month
    roster_data = load_roster()
    team_members = [m for m in roster_data.get('team_members', []) if m.get('active', True)]

    # For GET
    selected_person = request.args.get('person')
    if selected_person is None:
        today_str = now.strftime('%Y-%m-%d')
        selected_person = get_standby_person(today_str)

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
        # Combine logs for all active team members
        overtime_logs = []
        for member in team_members:
            member_logs = load_overtime_logs(member['name'], year, month)
            for log in member_logs:
                # Ensure the person field is set (for display)
                if not log.get('person'):
                    log['person'] = member['name']
                overtime_logs.append(log)
        # Sort logs by start_time descending
        overtime_logs.sort(key=lambda x: x.get('start_time', ''), reverse=True)
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
    
    # Add year and month fields to each log for template use
    for log in overtime_logs:
        start_time = log.get('start_time', '')
        if start_time:
            # Support both 'YYYY-MM-DD HH:MM' and 'YYYY-MM-DDTHH:MM' formats
            date_part = start_time.split('T')[0] if 'T' in start_time else start_time.split(' ')[0]
            parts = date_part.split('-')
            if len(parts) == 3:
                log['year'] = parts[0]
                log['month'] = int(parts[1])
            else:
                log['year'] = ''
                log['month'] = ''
        else:
            log['year'] = ''
            log['month'] = ''
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
        current_standby = get_standby_person(today)
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

@standby_bp.route('/roster/edit_member', methods=['POST'])
@login_required
def edit_member():
    roster_data = load_roster()
    name_original = request.form.get('name_original')
    name = request.form.get('name')
    color = request.form.get('color')
    active = bool(request.form.get('active'))
    
    # Find and update the member
    for member in roster_data.get('team_members', []):
        if member.get('name') == name_original:
            member['name'] = name
            member['color'] = color
            member['active'] = active
            break
    
    save_roster(roster_data)
    flash(f'Team member {name_original} updated!', 'success')
    return redirect(url_for('standby.roster'))

@standby_bp.route('/api/roster-notifications')
@login_required
def api_roster_notifications():
    """API endpoint to get roster-related notifications"""
    try:
        roster_data = load_roster()
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
