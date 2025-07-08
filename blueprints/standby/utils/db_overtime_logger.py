"""
Database-based overtime logger for standby module.
Replaces the file-based overtime_logger.py
"""

from datetime import datetime, timedelta
from models import db, User, OvertimeLog
from sqlalchemy import and_, func
import uuid


def load_overtime_logs(username: str, year: int, month: int):
    """Load overtime logs for a specific user and month from database."""
    user = User.query.filter_by(username=username).first()
    if not user:
        return []
    
    # Get logs for the specified year and month
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)
    
    logs = OvertimeLog.query.filter(
        and_(
            OvertimeLog.user_id == user.id,
            OvertimeLog.start_time >= start_date,
            OvertimeLog.start_time < end_date
        )
    ).order_by(OvertimeLog.start_time.desc()).all()
    
    # Convert to legacy format for compatibility
    result = []
    for log in logs:
        result.append({
            'id': str(log.id),
            'person': log.user.username,
            'start_time': log.start_time.strftime('%Y-%m-%d %H:%M'),
            'end_time': log.end_time.strftime('%Y-%m-%d %H:%M'),
            'duration_hours': str(log.duration_hours),
            'issue_description': log.issue_description or '',
            'resolution_notes': log.resolution_notes or '',
            'year': str(log.year),
            'month': str(log.month)
        })
    
    return result


def parse_datetime(dt_str):
    """Parse a datetime string in either 'YYYY-MM-DDTHH:MM' or 'YYYY-MM-DD HH:MM' format."""
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"Invalid time format: {dt_str}")


def validate_overtime_entry(start_str: str, end_str: str):
    """Validate overtime entry times and calculate duration."""
    try:
        start_time = parse_datetime(start_str)
        end_time = parse_datetime(end_str)
        
        if end_time <= start_time:
            return False, "End time must be after start time"
        
        duration = end_time - start_time
        duration_hours = duration.total_seconds() / 3600
        
        if duration_hours > 24:
            return False, "Overtime entry cannot exceed 24 hours"
        
        return True, duration_hours
        
    except ValueError as e:
        return False, f"Invalid time format: {e}"


def save_overtime_entry(username: str, year: int, month: int, entry_data: dict):
    """Save an overtime entry to database."""
    user = User.query.filter_by(username=username).first()
    if not user:
        raise ValueError(f"User '{username}' not found")
    
    # Parse times
    start_time = parse_datetime(entry_data['start_time'])
    end_time = parse_datetime(entry_data['end_time'])
    
    # Create overtime log entry
    overtime_log = OvertimeLog(
        user_id=user.id,
        start_time=start_time,
        end_time=end_time,
        duration_hours=float(entry_data['duration_hours']),
        issue_description=entry_data.get('issue_description', ''),
        resolution_notes=entry_data.get('resolution_notes', '')
    )
    
    db.session.add(overtime_log)
    db.session.commit()
    
    return overtime_log


def update_overtime_entry(username: str, year: int, month: int, entry_id: str, updated_data: dict):
    """Update an existing overtime entry."""
    user = User.query.filter_by(username=username).first()
    if not user:
        return False
    
    # Find the entry
    overtime_log = OvertimeLog.query.filter_by(id=int(entry_id), user_id=user.id).first()
    if not overtime_log:
        return False
    
    # Update fields
    if 'start_time' in updated_data:
        overtime_log.start_time = parse_datetime(updated_data['start_time'])
    if 'end_time' in updated_data:
        overtime_log.end_time = parse_datetime(updated_data['end_time'])
    if 'duration_hours' in updated_data:
        overtime_log.duration_hours = float(updated_data['duration_hours'])
    if 'issue_description' in updated_data:
        overtime_log.issue_description = updated_data['issue_description']
    if 'resolution_notes' in updated_data:
        overtime_log.resolution_notes = updated_data['resolution_notes']
    
    db.session.commit()
    return True


def delete_overtime_entry(username: str, entry_id: str):
    """Delete an overtime entry."""
    user = User.query.filter_by(username=username).first()
    if not user:
        return False
    
    overtime_log = OvertimeLog.query.filter_by(id=int(entry_id), user_id=user.id).first()
    if not overtime_log:
        return False
    
    db.session.delete(overtime_log)
    db.session.commit()
    return True


def get_overtime_summary(username: str, year: int, month: int):
    """Get overtime summary for a user in a specific month."""
    user = User.query.filter_by(username=username).first()
    if not user:
        return {'total_hours': 0, 'entries': 0}
    
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)
    
    # Get total hours and count
    result = db.session.query(
        func.sum(OvertimeLog.duration_hours).label('total_hours'),
        func.count(OvertimeLog.id).label('entries')
    ).filter(
        and_(
            OvertimeLog.user_id == user.id,
            OvertimeLog.start_time >= start_date,
            OvertimeLog.start_time < end_date
        )
    ).first()
    
    return {
        'total_hours': float(result.total_hours or 0),
        'entries': int(result.entries or 0)
    }


def get_all_overtime_logs(year: int, month: int, username: str = None):
    """Get all overtime logs for a month, optionally filtered by user."""
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)
    
    query = OvertimeLog.query.filter(
        and_(
            OvertimeLog.start_time >= start_date,
            OvertimeLog.start_time < end_date
        )
    ).join(User).order_by(OvertimeLog.start_time.desc())
    
    if username:
        query = query.filter(User.username == username)
    
    logs = query.all()
    
    # Convert to legacy format
    result = []
    for log in logs:
        result.append({
            'id': str(log.id),
            'person': log.user.username,
            'start_time': log.start_time.strftime('%Y-%m-%d %H:%M'),
            'end_time': log.end_time.strftime('%Y-%m-%d %H:%M'),
            'duration_hours': str(log.duration_hours),
            'issue_description': log.issue_description or '',
            'resolution_notes': log.resolution_notes or '',
            'year': str(log.year),
            'month': str(log.month)
        })
    
    return result


def get_recent_overtime_activity(limit: int = 10):
    """Get recent overtime activity across all users."""
    logs = OvertimeLog.query.join(User).order_by(OvertimeLog.start_time.desc()).limit(limit).all()
    
    result = []
    for log in logs:
        result.append({
            'id': str(log.id),
            'person': log.user.username,
            'start_time': log.start_time.strftime('%Y-%m-%d %H:%M'),
            'end_time': log.end_time.strftime('%Y-%m-%d %H:%M'),
            'duration_hours': str(log.duration_hours),
            'issue_description': log.issue_description or '',
            'resolution_notes': log.resolution_notes or '',
            'year': str(log.year),
            'month': str(log.month)
        })
    
    return result


def export_overtime_to_csv(username: str, year: int, month: int):
    """Export overtime logs to CSV format."""
    import csv
    import io
    
    logs = load_overtime_logs(username, year, month)
    
    output = io.StringIO()
    fieldnames = ['id', 'person', 'start_time', 'end_time', 'duration_hours', 'issue_description', 'resolution_notes']
    
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    
    for log in logs:
        writer.writerow(log)
    
    return output.getvalue()


def archive_old_overtime_logs(months_to_keep: int = 6):
    """Archive old overtime logs (older than specified months)."""
    cutoff_date = datetime.now() - timedelta(days=months_to_keep * 30)
    
    # Get old logs
    old_logs = OvertimeLog.query.filter(OvertimeLog.start_time < cutoff_date).all()
    
    # For now, we'll just delete them. In a production system, you might want to:
    # 1. Move them to an archive table
    # 2. Export them to files
    # 3. Compress them
    
    count = len(old_logs)
    for log in old_logs:
        db.session.delete(log)
    
    db.session.commit()
    
    return count


def get_overtime_statistics(username: str = None, year: int = None, month: int = None):
    """Get overtime statistics."""
    query = OvertimeLog.query.join(User)
    
    if username:
        user = User.query.filter_by(username=username).first()
        if user:
            query = query.filter(OvertimeLog.user_id == user.id)
    
    if year and month:
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        query = query.filter(
            and_(
                OvertimeLog.start_time >= start_date,
                OvertimeLog.start_time < end_date
            )
        )
    
    # Get statistics
    stats = db.session.query(
        func.sum(OvertimeLog.duration_hours).label('total_hours'),
        func.count(OvertimeLog.id).label('total_entries'),
        func.avg(OvertimeLog.duration_hours).label('avg_hours_per_entry')
    ).filter(query.whereclause).first()
    
    return {
        'total_hours': float(stats.total_hours or 0),
        'total_entries': int(stats.total_entries or 0),
        'avg_hours_per_entry': float(stats.avg_hours_per_entry or 0)
    } 