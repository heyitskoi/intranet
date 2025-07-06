# Calendar Query Examples

This document provides comprehensive examples for the enhanced standby calendar system that handles past assignments, future calculated slots, and overrides.

## SQLAlchemy Query Examples

### 1. Combined Past/Future Query for Date Range

```python
from datetime import datetime, timedelta
from sqlalchemy import and_, or_
from models import StandbyAssignment, StandbyOverride, StandbyDurationConfig, StandbyMember, User

def get_calendar_slots_for_range(start_date: str, end_date: str, department_id: int):
    """
    Get all calendar slots for a date range, combining stored assignments and calculated slots.
    
    Args:
        start_date: Start date in 'YYYY-MM-DD' format
        end_date: End date in 'YYYY-MM-DD' format
        department_id: Department ID to filter by
    
    Returns:
        List of calendar slot dictionaries
    """
    try:
        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()
    except ValueError:
        raise ValueError("Invalid date format")
    
    today = datetime.now().date()
    
    # Query existing assignments
    assignments = (
        StandbyAssignment.query
        .filter(
            and_(
                StandbyAssignment.department_id == department_id,
                StandbyAssignment.date >= start,
                StandbyAssignment.date <= end
            )
        )
        .join(User)
        .all()
    )
    assignment_map = {a.date: a for a in assignments}
    
    # Query overrides
    overrides = (
        StandbyOverride.query
        .filter(
            and_(
                StandbyOverride.date >= start,
                StandbyOverride.date <= end
            )
        )
        .join(User)
        .all()
    )
    override_map = {o.date: o for o in overrides}
    
    # Get department configuration for calculations
    config = StandbyDurationConfig.query.filter_by(department_id=department_id).first()
    
    # Get active members for rotation calculation
    active_members = (
        StandbyMember.query.filter_by(active=True)
        .join(User)
        .filter(User.department_id == department_id)
        .order_by(StandbyMember.rotation_order)
        .all()
    )
    
    # Build calendar slots
    calendar_slots = []
    current_date = start
    
    while current_date <= end:
        slot = {
            'date': current_date,
            'username': None,
            'source': 'none',
            'is_override': False,
            'is_past': current_date < today,
            'is_today': current_date == today,
            'override_reason': None
        }
        
        # Priority 1: Override (highest priority)
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
    
    return calendar_slots
```

### 2. Query for Past Assignments Only

```python
def get_past_assignments(department_id: int, days_back: int = 30):
    """
    Get all past assignments for the last N days.
    
    Args:
        department_id: Department ID to filter by
        days_back: Number of days to look back
    
    Returns:
        List of past assignment dictionaries
    """
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days_back)
    
    assignments = (
        StandbyAssignment.query
        .filter(
            and_(
                StandbyAssignment.department_id == department_id,
                StandbyAssignment.date >= start_date,
                StandbyAssignment.date <= end_date
            )
        )
        .join(User)
        .order_by(StandbyAssignment.date.desc())
        .all()
    )
    
    return [
        {
            'date': assignment.date.strftime('%Y-%m-%d'),
            'username': assignment.user.username,
            'created_at': assignment.created_at.isoformat()
        }
        for assignment in assignments
    ]
```

### 3. Query for Future Calculated Slots

```python
def get_future_calculated_slots(department_id: int, days_ahead: int = 90):
    """
    Get calculated future assignments that don't have stored assignments.
    
    Args:
        department_id: Department ID to filter by
        days_ahead: Number of days to look ahead
    
    Returns:
        List of calculated slot dictionaries
    """
    start_date = datetime.now().date() + timedelta(days=1)
    end_date = start_date + timedelta(days=days_ahead)
    
    # Get existing future assignments
    existing_assignments = (
        StandbyAssignment.query
        .filter(
            and_(
                StandbyAssignment.department_id == department_id,
                StandbyAssignment.date >= start_date,
                StandbyAssignment.date <= end_date
            )
        )
        .all()
    )
    existing_dates = {a.date for a in existing_assignments}
    
    # Get configuration and active members
    config = StandbyDurationConfig.query.filter_by(department_id=department_id).first()
    active_members = (
        StandbyMember.query.filter_by(active=True)
        .join(User)
        .filter(User.department_id == department_id)
        .order_by(StandbyMember.rotation_order)
        .all()
    )
    
    calculated_slots = []
    current_date = start_date
    
    while current_date <= end_date:
        if current_date not in existing_dates:
            if config and active_members and current_date >= config.rotation_start_date:
                days_since_start = (current_date - config.rotation_start_date).days
                if days_since_start >= 0:
                    idx = (days_since_start // config.standby_shift_days) % len(active_members)
                    calculated_slots.append({
                        'date': current_date.strftime('%Y-%m-%d'),
                        'username': active_members[idx].user.username,
                        'source': 'calculated'
                    })
        
        current_date += timedelta(days=1)
    
    return calculated_slots
```

### 4. Query for Overrides with Reasons

```python
def get_overrides_with_reasons(department_id: int, start_date: str, end_date: str):
    """
    Get all overrides with their reasons for a date range.
    
    Args:
        department_id: Department ID to filter by
        start_date: Start date in 'YYYY-MM-DD' format
        end_date: End date in 'YYYY-MM-DD' format
    
    Returns:
        List of override dictionaries with reasons
    """
    try:
        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()
    except ValueError:
        raise ValueError("Invalid date format")
    
    overrides = (
        StandbyOverride.query
        .filter(
            and_(
                StandbyOverride.date >= start,
                StandbyOverride.date <= end
            )
        )
        .join(User)
        .filter(User.department_id == department_id)
        .order_by(StandbyOverride.date)
        .all()
    )
    
    return [
        {
            'date': override.date.strftime('%Y-%m-%d'),
            'username': override.user.username,
            'reason': override.reason,
            'created_at': override.created_at.isoformat(),
            'created_by': override.created_by.username
        }
        for override in overrides
    ]
```

## Jinja Template Examples

### 1. Calendar Display with Slot Types

```jinja2
<!-- Calendar Legend -->
<div class="calendar-legend mb-3">
    <div class="row">
        <div class="col-md-8">
            <div class="d-flex flex-wrap gap-2">
                <span class="badge bg-success">● Past Assignment</span>
                <span class="badge bg-info text-dark">● Future Calculated</span>
                <span class="badge bg-warning text-dark">● Override</span>
                <span class="badge bg-secondary">● No Assignment</span>
            </div>
        </div>
        <div class="col-md-4 text-end">
            <small class="text-muted">
                <strong>Today:</strong> {{ today.strftime('%B %d, %Y') }}
            </small>
        </div>
    </div>
</div>

<!-- Calendar Grid -->
<div class="calendar-grid">
    {% for slot in calendar_slots %}
        <div class="calendar-day 
                    {% if slot.is_today %}today{% endif %}
                    {% if slot.is_past %}past{% endif %}
                    {% if slot.source == 'override' %}override{% endif %}
                    {% if slot.source == 'db' %}stored{% endif %}
                    {% if slot.source == 'calculated' %}calculated{% endif %}">
            
            <div class="date-header">
                {{ slot.date.strftime('%d') }}
                {% if slot.is_today %}
                    <span class="badge bg-danger">Today</span>
                {% endif %}
            </div>
            
            <div class="assignment-info">
                {% if slot.username %}
                    <div class="username">{{ slot.username }}</div>
                    <div class="source-badge">
                        {% if slot.source == 'override' %}
                            <span class="badge bg-warning text-dark">Override</span>
                            {% if slot.override_reason %}
                                <small class="text-muted d-block">{{ slot.override_reason }}</small>
                            {% endif %}
                        {% elif slot.source == 'db' %}
                            {% if slot.is_past %}
                                <span class="badge bg-success">Past</span>
                            {% else %}
                                <span class="badge bg-primary">Stored</span>
                            {% endif %}
                        {% elif slot.source == 'calculated' %}
                            <span class="badge bg-info text-dark">Calculated</span>
                        {% endif %}
                    </div>
                {% else %}
                    <div class="no-assignment">—</div>
                    <span class="badge bg-secondary">None</span>
                {% endif %}
            </div>
        </div>
    {% endfor %}
</div>
```

### 2. Summary Statistics Display

```jinja2
<!-- Calendar Summary -->
<div class="calendar-summary mb-4">
    <div class="row">
        <div class="col-md-3">
            <div class="card text-center">
                <div class="card-body">
                    <h5 class="card-title text-success">{{ calendar_slots|selectattr('source', 'equalto', 'db')|selectattr('is_past', 'equalto', true)|list|length }}</h5>
                    <p class="card-text">Past Assignments</p>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card text-center">
                <div class="card-body">
                    <h5 class="card-title text-primary">{{ calendar_slots|selectattr('source', 'equalto', 'db')|selectattr('is_past', 'equalto', false)|list|length }}</h5>
                    <p class="card-text">Future Stored</p>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card text-center">
                <div class="card-body">
                    <h5 class="card-title text-info">{{ calendar_slots|selectattr('source', 'equalto', 'calculated')|list|length }}</h5>
                    <p class="card-text">Future Calculated</p>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card text-center">
                <div class="card-body">
                    <h5 class="card-title text-warning">{{ calendar_slots|selectattr('source', 'equalto', 'override')|list|length }}</h5>
                    <p class="card-text">Overrides</p>
                </div>
            </div>
        </div>
    </div>
</div>
```

### 3. Override Management Form

```jinja2
<!-- Override Management -->
<div class="override-management mb-4">
    <h4>Manage Overrides</h4>
    
    <!-- Add Override Form -->
    <form method="POST" action="{{ url_for('standby.add_override_route') }}" class="mb-3">
        <div class="row">
            <div class="col-md-3">
                <label for="override_date" class="form-label">Date</label>
                <input type="date" class="form-control" id="override_date" name="date" required>
            </div>
            <div class="col-md-3">
                <label for="override_user" class="form-label">User</label>
                <select class="form-select" id="override_user" name="username" required>
                    <option value="">Select user...</option>
                    {% for member in active_members %}
                        <option value="{{ member.user.username }}">{{ member.user.username }}</option>
                    {% endfor %}
                </select>
            </div>
            <div class="col-md-4">
                <label for="override_reason" class="form-label">Reason (optional)</label>
                <input type="text" class="form-control" id="override_reason" name="reason" placeholder="Why is this override needed?">
            </div>
            <div class="col-md-2">
                <label class="form-label">&nbsp;</label>
                <button type="submit" class="btn btn-warning w-100">Add Override</button>
            </div>
        </div>
    </form>
    
    <!-- Current Overrides List -->
    <div class="current-overrides">
        <h5>Current Overrides</h5>
        {% set overrides = calendar_slots|selectattr('source', 'equalto', 'override')|list %}
        {% if overrides %}
            <div class="table-responsive">
                <table class="table table-sm">
                    <thead>
                        <tr>
                            <th>Date</th>
                            <th>User</th>
                            <th>Reason</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for slot in overrides %}
                            <tr>
                                <td>{{ slot.date.strftime('%Y-%m-%d') }}</td>
                                <td>{{ slot.username }}</td>
                                <td>{{ slot.override_reason or 'No reason provided' }}</td>
                                <td>
                                    <form method="POST" action="{{ url_for('standby.remove_override_route') }}" class="d-inline">
                                        <input type="hidden" name="date" value="{{ slot.date.strftime('%Y-%m-%d') }}">
                                        <button type="submit" class="btn btn-sm btn-outline-danger" 
                                                onclick="return confirm('Remove this override?')">
                                            Remove
                                        </button>
                                    </form>
                                </td>
                            </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        {% else %}
            <p class="text-muted">No overrides currently set.</p>
        {% endif %}
    </div>
</div>
```

## Key Features Implemented

1. **Past Assignment Preservation**: Past assignments are never modified when configuration changes
2. **Future Assignment Calculation**: Future slots without stored assignments are calculated based on rotation pattern
3. **Override Priority**: Overrides take highest priority and are preserved during regeneration
4. **Clear Visual Indicators**: Different colors and badges for different slot types
5. **Comprehensive Queries**: Separate queries for different data types with proper joins
6. **Responsive Template**: Jinja templates that handle all slot types gracefully

## Usage Notes

- Past assignments are immutable and represent what actually happened
- Future calculated slots show what the rotation pattern predicts
- Overrides can be added for any future date and take priority
- Configuration changes only affect future assignments, never past ones
- The system provides clear visual feedback about slot sources and types 