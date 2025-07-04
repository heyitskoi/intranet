# Standby Management Module

This module integrates the standby-overtime app functionality into the main intranet application as a blueprint.

## Overview

The standby module provides:
- **Standby Rotation Management**: Automatic rotation scheduling with overrides
- **Overtime Logging**: Track and manage overtime hours
- **Calendar View**: Visual calendar showing standby assignments
- **Team Management**: Add/remove team members and manage roster

## Integration Details

### URL Structure
- **Dashboard**: `/standby/dashboard`
- **Calendar**: `/standby/calendar`
- **Roster Management**: `/standby/roster`
- **Overtime Logging**: `/standby/overtime`

### Authentication
All standby routes require authentication via Flask-Login. Users must be logged in to access any standby functionality.

### Data Storage
- **Roster Data**: `standby_data/roster.json`
- **Overtime Logs**: `standby_logs/{username}/{YYYY-MM}.csv`
- **Archived Logs**: `standby_logs/{username}/_archive/`

## Configuration

The module uses environment variables for configuration:

```bash
# Overtime Settings
MONTHLY_OVERTIME_LIMIT=40
OVERTIME_WARNING_THRESHOLD=35

# Dashboard Settings
DASHBOARD_REFRESH_INTERVAL=300
NOTIFICATION_AUTO_DISMISS=10

# Team Settings
MAX_TEAM_MEMBERS=10
```

## File Structure

```
blueprints/standby/
├── __init__.py          # Main blueprint with routes
├── config.py            # Configuration settings
├── utils/               # Utility functions
│   ├── rotation_manager.py
│   ├── overtime_logger.py
│   ├── clean_overtime_csv.py
│   └── fix_overtime_csv.py
└── README.md           # This file

templates/standby/
├── base.html           # Base template for standby pages
├── dashboard.html      # Dashboard view
├── calendar.html       # Calendar view
├── roster.html         # Roster management
└── overtime.html       # Overtime logging

static/standby/
├── css/                # Standby-specific styles
└── js/                 # Standby-specific scripts
```

## Key Features

### 1. Standby Rotation
- Automatic weekly rotation based on team roster
- Support for overrides (sick leave, vacation, etc.)
- Visual calendar showing current and upcoming assignments

### 2. Overtime Management
- Log overtime with start/end times
- Automatic duration calculation
- Optional issue description and resolution notes
- CSV export for HR reporting
- Automatic archiving of old logs

### 3. Team Management
- Add/remove team members
- Set custom colors for calendar display
- Toggle member active/inactive status
- Manage rotation order

### 4. Dashboard
- Current standby person display
- Next week's standby preview
- Overtime statistics
- Recent activity feed
- Quick action buttons

## Usage

### For Users
1. Navigate to `/standby/dashboard` to see your standby overview
2. Use `/standby/overtime` to log overtime hours
3. Check `/standby/calendar` to see the full schedule
4. Visit `/standby/roster` to manage team members (if you have permissions)

### For Administrators
1. Manage team roster at `/standby/roster`
2. Add overrides for planned absences
3. Monitor overtime usage across the team
4. Export reports for HR

## API Endpoints

The module provides several API endpoints for dynamic updates:

- `GET /standby/api/current-standby` - Get current standby person
- `GET /standby/api/total-hours` - Get current user's overtime hours

## Dependencies

The module requires these additional packages:
- `pandas>=2.0.0` - For data manipulation
- `reportlab>=4.0.0` - For PDF export functionality

## Testing

Run the integration test to verify everything works:

```bash
python test_standby_integration.py
```

## Migration from Standalone App

If you're migrating from the standalone standby-overtime app:

1. **Data Migration**: Copy your existing `data/roster.json` to `standby_data/roster.json`
2. **Logs Migration**: Copy your existing `logs/` directory to `standby_logs/`
3. **User Mapping**: Ensure usernames in the intranet match the names in your roster

## Troubleshooting

### Common Issues

1. **Permission Errors**: Ensure the `standby_data` and `standby_logs` directories are writable
2. **Import Errors**: Make sure all dependencies are installed (`pip install -r requirements.txt`)
3. **Template Errors**: Verify all template files are in the correct location

### Debug Mode

Enable debug mode to see detailed error messages:

```bash
export FLASK_DEBUG=true
python app.py
```

## Future Enhancements

Potential improvements for the standby module:
- Email/Slack notifications for standby changes
- Integration with external calendar systems
- Advanced reporting and analytics
- Mobile-responsive improvements
- Multi-department support 