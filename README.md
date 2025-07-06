# Intranet Application

A comprehensive Flask-based intranet application with authentication, advanced standby management, overtime tracking, and roster functionality.

## Features

- **Authentication System**: User registration and login with role-based access control
- **Advanced Standby Management**: 
  - Automated rotation scheduling with configurable patterns
  - Manual assignment overrides
  - Department-specific standby configurations
  - Historical assignment tracking
  - Real-time dashboard with notifications
- **Overtime Tracking**: Comprehensive overtime logging and reporting
- **Roster System**: Employee roster management with department organization
- **Audit Logging**: Complete audit trail of user actions
- **Database Integration**: SQLite database with migration support and data seeding

## Project Structure

```
intranet/
├── app.py                     # Main Flask application
├── config.py                  # Configuration settings
├── models.py                  # Database models (User, Department, Role, Standby, Overtime, Audit)
├── init_db.py                 # Database initialization
├── seed_database.py           # Database seeding with sample data
├── setup_assignment_system.py # Standby assignment system setup
├── test_assignment_system.py  # Assignment system testing
├── requirements.txt           # Python dependencies
├── IMPLEMENTATION_SUMMARY.md  # Recent implementation details
├── auth/                      # Authentication module
│   ├── __init__.py
│   └── routes.py
├── blueprints/                # Flask blueprints
│   └── standby/               # Standby management system
│       ├── __init__.py        # Main standby routes and logic
│       ├── config.py          # Standby configuration
│       ├── utils/             # Utility functions
│       └── README.md          # Standby system documentation
├── templates/                 # HTML templates
│   ├── base.html
│   ├── login.html
│   ├── register.html
│   └── components/
├── static/                    # Static assets
│   ├── css/
│   ├── js/
│   └── standby/
├── docs/                      # Documentation
│   ├── STANDBY_ASSIGNMENT_SYSTEM.md
│   ├── ROSTER_REFACTOR_SUMMARY.md
│   ├── REFACTORING_SUMMARY.md
│   ├── REFACTORING_GUIDE.md
│   └── STANDBY_DATABASE_INTEGRATION.md
├── tests/                     # Test files
├── migrations/                # Database migrations
├── dev_scripts/               # Development utilities
├── standby_data/              # Standby data storage
└── standby_logs/              # Standby logs
```

## Setup Instructions

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Initialize Database**:
   ```bash
   python init_db.py
   ```

3. **Seed Database with Sample Data**:
   ```bash
   python seed_database.py
   ```

4. **Setup Standby Assignment System**:
   ```bash
   python setup_assignment_system.py
   ```

5. **Run the Application**:
   ```bash
   python app.py
   ```

6. **Access the Application**:
   - Open your browser and go to `http://localhost:5000`
   - Login with default credentials: `admin/admin123`

## Key Features

### Standby Management System
- **Automated Rotation**: Configurable rotation patterns with start dates and shift durations
- **Manual Overrides**: Ability to override automatic assignments for specific dates
- **Department Isolation**: Each department has independent standby schedules
- **Historical Tracking**: Past assignments are preserved and never modified
- **Real-time Dashboard**: Live updates with configurable refresh intervals
- **Notification System**: Automatic notifications with configurable dismissal times

### Overtime Tracking
- **Time Logging**: Track start/end times and calculate duration
- **Issue Tracking**: Log issues and resolution notes
- **Monthly Limits**: Configurable overtime limits with warning thresholds
- **Reporting**: Generate overtime reports by month/year

### User Management
- **Role-based Access**: Different user roles with appropriate permissions
- **Department Organization**: Users organized by departments
- **Audit Logging**: Complete audit trail of all user actions

## Configuration

The application uses `config.py` for configuration settings. Key settings include:
- Database URI
- Secret key for sessions
- Debug mode settings
- Standby configuration (refresh intervals, notification settings)

## Database Models

### Core Models
- **User**: Authentication and user management
- **Department**: Company department organization
- **Role**: User role definitions
- **AuditLog**: User action tracking

### Standby Models
- **StandbyMember**: Team member configuration with colors and rotation order
- **StandbyOverride**: Manual date overrides
- **StandbyAssignment**: Actual assignments for specific dates
- **StandbyDurationConfig**: Department-specific configuration

### Overtime Models
- **OvertimeLog**: Overtime entries with time tracking and issue descriptions

## Testing

### Run Assignment System Tests:
```bash
python test_assignment_system.py
```

### Run General Tests:
```bash
python -m pytest tests/
```

## Development

### Key Development Files
- **`IMPLEMENTATION_SUMMARY.md`**: Recent implementation details and changes
- **`docs/STANDBY_ASSIGNMENT_SYSTEM.md`**: Comprehensive standby system documentation
- **`docs/REFACTORING_GUIDE.md`**: Development guidelines and best practices

### Architecture
- **Flask Blueprints**: Modular organization with standby functionality in separate blueprint
- **SQLAlchemy ORM**: Database models with relationships and constraints
- **Flask-Login**: Authentication and session management
- **Migration System**: Database schema evolution support

### Recent Improvements
- **Assignment System**: Separated rotation configuration from actual assignments
- **Historical Integrity**: Past assignments are never modified when patterns change
- **Performance**: Pre-calculated assignments stored in database
- **Department Isolation**: Independent standby schedules per department

## API Endpoints

### Authentication
- `POST /auth/login` - User login
- `POST /auth/register` - User registration
- `GET /auth/logout` - User logout

### Standby Management
- `GET /standby/roster` - View standby roster
- `GET /standby/roster/duration-config` - Configure rotation settings
- `POST /standby/roster/duration-config` - Update rotation configuration
- `GET /standby/roster/overrides` - View manual overrides
- `POST /standby/roster/overrides` - Create manual overrides

### Dashboard
- `GET /dashboard` - Main dashboard (requires authentication)

## Database Migrations

The application includes migration scripts for database schema evolution:
- `migrations/create_standby_assignments_table.py` - Creates standby assignment table
- `docs/migrate_standby_to_db.py` - Migrates legacy standby data

## Troubleshooting

### Common Issues
1. **Database not found**: Run `python init_db.py` to create the database
2. **No sample data**: Run `python seed_database.py` to populate with test data
3. **Standby system not working**: Run `python setup_assignment_system.py` to initialize the assignment system

### Logs
- Check `standby_logs/` directory for standby system logs
- Application logs are output to console in debug mode

## Contributing

1. Follow the guidelines in `docs/REFACTORING_GUIDE.md`
2. Add tests for new features
3. Update documentation for significant changes
4. Use the existing migration system for database changes

## License

This project is for internal use only. 