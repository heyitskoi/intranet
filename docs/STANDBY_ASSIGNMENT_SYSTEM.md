# Standby Assignment System

This document describes the new standby assignment system that separates rotation pattern configuration from actual assignments.

## Overview

The new system addresses the problem where changing rotation configuration would rewrite the entire history. Now:

- **Rotation pattern configuration** is stored separately and defines how assignments should be generated
- **Actual assignments** are stored in the `StandbyAssignment` table and represent who is actually assigned for each date
- **Past assignments** are frozen and never change
- **Future assignments** are generated based on the pattern but can be manually overridden

## Database Schema

### New Table: StandbyAssignment

```sql
CREATE TABLE standby_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    department_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    date DATE NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (department_id) REFERENCES departments (id),
    FOREIGN KEY (user_id) REFERENCES users (id),
    UNIQUE (department_id, date)
);
```

### Key Features

- **Department-specific**: Each department has its own assignments
- **Date-based**: One assignment per department per date
- **Immutable**: Once created, assignments for past dates never change
- **Unique constraint**: Prevents duplicate assignments for the same department/date

## How It Works

### 1. Assignment Generation

When requesting a standby person for a date:

1. **Check existing assignment**: Look for an assignment in the `StandbyAssignment` table
2. **If found**: Return the assigned person
3. **If not found and future date**: Generate assignment using rotation pattern
4. **If not found and past date**: Return None (no assignment exists)

### 2. Rotation Pattern

The rotation pattern is calculated using:
- `rotation_start_date`: When the pattern begins
- `standby_shift_days`: How many days each person works
- Active standby members in rotation order

```python
# Calculate which person should be on standby
days_since_start = (date - rotation_start_date).days
person_index = (days_since_start // standby_shift_days) % len(active_members)
```

### 3. Configuration Changes

When rotation configuration changes:

1. **Past assignments**: Remain unchanged
2. **Future assignments**: Are regenerated based on new pattern
3. **Overrides**: Are preserved and take precedence

## Usage

### Basic Usage

```python
from blueprints.standby.utils.assignment_rotation_manager import AssignmentRotationManager

# Get standby person for a date
standby_person = AssignmentRotationManager.get_standby_person('2024-01-15', department_id=1)

# Get assignments for a date range
assignments = AssignmentRotationManager.get_assignments_for_date_range(
    '2024-01-01', '2024-01-31', department_id=1
)

# Get user's assignments
user_assignments = AssignmentRotationManager.get_user_assignments('john_doe')
```

### Regenerating Future Assignments

When rotation pattern changes:

```python
# Regenerate all future assignments
regenerated_count = AssignmentRotationManager.regenerate_future_assignments(department_id=1)

# Regenerate from a specific date
from datetime import date
regenerated_count = AssignmentRotationManager.regenerate_future_assignments(
    department_id=1, 
    from_date=date(2024, 2, 1)
)
```

### Manual Assignments

```python
# Create manual assignment
assignment = AssignmentRotationManager.create_manual_assignment(
    '2024-01-15', 'john_doe', department_id=1
)

# Delete assignment
deleted = AssignmentRotationManager.delete_assignment('2024-01-15', department_id=1)
```

## Migration

### Step 1: Run Migration Script

```bash
python migrations/create_standby_assignments_table.py
```

This script will:
- Create the `StandbyAssignment` table
- Migrate existing rotation data for the past 30 days
- Generate assignments for the next 90 days

### Step 2: Update Application Code

The application automatically uses the new system when `department_id` is provided to `get_standby_person()`.

### Step 3: Test

Verify the system works correctly:
- Past assignments remain unchanged
- Future assignments are generated correctly
- Configuration changes only affect future dates

## Benefits

### 1. Historical Integrity
- Past assignments are never modified
- Audit trail is preserved
- Historical reports remain accurate

### 2. Flexible Configuration
- Rotation pattern can be changed without affecting history
- Future assignments are automatically regenerated
- Manual overrides are preserved

### 3. Better Performance
- Assignments are pre-calculated and stored
- No need to recalculate rotation for every request
- Efficient queries using indexes

### 4. Department Isolation
- Each department has independent assignments
- No cross-department interference
- Department-specific configuration

## Configuration

### StandbyDurationConfig

The configuration table controls how assignments are generated:

- `standby_shift_days`: Days per person in rotation
- `rotation_start_date`: When rotation pattern begins
- `monthly_overtime_limit`: Overtime limit per month
- `overtime_warning_threshold`: Warning threshold for overtime

### Changing Configuration

When configuration changes:
1. Update the configuration record
2. System automatically detects changes
3. Future assignments are regenerated
4. Past assignments remain unchanged

## Troubleshooting

### Common Issues

1. **No assignments generated**: Check if department has active standby members
2. **Wrong rotation order**: Verify `rotation_order` in `StandbyMember` table
3. **Configuration not applied**: Ensure `StandbyDurationConfig` exists for department

### Debugging

```python
# Check assignment statistics
stats = AssignmentRotationManager.get_assignment_stats(department_id=1)
print(stats)

# Check specific date assignment
assignment = StandbyAssignment.query.filter_by(
    department_id=1, 
    date=date(2024, 1, 15)
).first()
```

## API Endpoints

The system provides several API endpoints:

- `GET /standby/api/current-standby`: Get current standby person
- `GET /standby/api/assignments/<start_date>/<end_date>`: Get assignments for date range
- `POST /standby/api/assignments`: Create manual assignment
- `DELETE /standby/api/assignments/<date>`: Delete assignment

## Future Enhancements

Potential improvements:
- Bulk assignment operations
- Assignment templates
- Advanced rotation patterns
- Assignment analytics
- Integration with calendar systems 