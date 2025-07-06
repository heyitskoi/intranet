# Standby Module Database Integration

This document describes the database integration for the standby module, which replaces the previous file-based storage system with a proper database solution.

## Overview

The standby module has been upgraded to use the main application database instead of file-based storage (JSON and CSV files). This provides:

- **Better data integrity** with ACID compliance
- **Improved performance** with indexed queries
- **Automatic archival** and data management
- **User integration** with existing authentication system
- **Better scalability** for larger teams

## New Database Models

### StandbyMember
Represents a user who is part of the standby rotation.

```python
class StandbyMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    color = db.Column(db.String(7), nullable=False, default='#007bff')
    active = db.Column(db.Boolean, default=True, nullable=False)
    rotation_order = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### StandbyOverride
Represents date overrides for the standby rotation.

```python
class StandbyOverride(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reason = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
```

### OvertimeLog
Represents overtime log entries.

```python
class OvertimeLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    duration_hours = db.Column(db.Float, nullable=False)
    issue_description = db.Column(db.Text, nullable=True)
    resolution_notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

## Migration Process

### Step 1: Run Database Migration

First, ensure your database is up to date with the new models:

```bash
# Create the new tables
flask shell -c "from app import db; db.create_all()"
```

### Step 2: Migrate Existing Data

If you have existing file-based data, run the migration script:

```bash
python migrate_standby_to_db.py
```

This script will:
- Create a backup of your existing files
- Import roster data from `standby_data/roster.json`
- Import overtime logs from `standby_logs/` directory
- Import overrides from the roster file
- Create missing users if they don't exist

### Step 3: Verify Migration

Test the database integration:

```bash
python test_db_integration.py
```

## New Features

### User Integration
- Standby members are now linked to existing users in the database
- Only registered users can be added to the standby roster
- User authentication is integrated with the standby system

### Enhanced Roster Management
- Add users from the existing user database
- Automatic validation of user existence
- Better error handling and user feedback

### Improved Overtime Logging
- Database-backed overtime entries
- Automatic archival of old entries
- Better querying and reporting capabilities
- Support for complex filters and searches

### Better Data Management
- Automatic timestamps for all entries
- Audit trail for changes
- Referential integrity with foreign keys
- Transaction support for data consistency

## Updated API

### Rotation Management
```python
# Add a team member
add_team_member(username, color='#007bff', active=True)

# Remove a team member
remove_team_member(username)

# Update team member properties
update_team_member(username, color='#ff0000', active=False)

# Update rotation order
update_rotation_order(['user1', 'user2', 'user3'])

# Add date override
add_override('2024-01-15', 'username', reason='Vacation')

# Remove date override
remove_override('2024-01-15')
```

### Overtime Management
```python
# Save overtime entry
save_overtime_entry(username, year, month, entry_data)

# Load overtime logs
load_overtime_logs(username, year, month)

# Get overtime summary
get_overtime_summary(username, year, month)

# Get all overtime logs for a month
get_all_overtime_logs(year, month, username=None)

# Get recent activity
get_recent_overtime_activity(limit=10)

# Export to CSV
export_overtime_to_csv(username, year, month)
```

## Configuration

The database integration uses the same configuration as the main application. No additional configuration is required.

## Benefits

### Performance
- **Faster queries**: Database indexes provide faster lookups
- **Reduced I/O**: No file system operations for data access
- **Better caching**: Database connection pooling and query caching

### Reliability
- **Data integrity**: ACID compliance ensures data consistency
- **Backup support**: Database backups include all standby data
- **Transaction support**: Rollback capability for failed operations

### Scalability
- **Concurrent access**: Multiple users can access data simultaneously
- **Large datasets**: Efficient handling of large amounts of overtime data
- **Future growth**: Easy to add new features and data types

### Maintenance
- **Automatic archival**: Old data can be automatically archived
- **Data cleanup**: Easy to remove old or invalid entries
- **Audit trail**: Track changes and user actions

## Troubleshooting

### Common Issues

1. **User not found errors**
   - Ensure the user exists in the main user database
   - Check that the username matches exactly

2. **Migration errors**
   - Verify file permissions for the backup directory
   - Check that the database is accessible
   - Review the migration log for specific errors

3. **Performance issues**
   - Check database indexes are created
   - Monitor query performance
   - Consider archiving old data

### Debugging

Enable debug logging in your Flask app to see detailed database operations:

```python
app.config['SQLALCHEMY_ECHO'] = True
```

## Future Enhancements

### Planned Features
- **Advanced reporting**: SQL-based reports and analytics
- **Data export**: Additional export formats (PDF, Excel)
- **Bulk operations**: Import/export of large datasets
- **Audit logging**: Detailed change tracking
- **API endpoints**: RESTful API for external integrations

### Performance Optimizations
- **Query optimization**: Index tuning and query optimization
- **Caching**: Redis-based caching for frequently accessed data
- **Pagination**: Efficient handling of large result sets
- **Background tasks**: Async processing for heavy operations

## Support

For issues with the database integration:

1. Check the migration logs
2. Run the test script to verify functionality
3. Review the database schema and relationships
4. Check for any error messages in the application logs

The database integration maintains backward compatibility with the existing API, so existing code should continue to work with minimal changes. 