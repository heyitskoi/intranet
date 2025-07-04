import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class StandbyConfig:
    """Standby module configuration"""
    
    # Flask settings
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'super-secret-key-change-this')
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    # Data paths - relative to intranet root
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    DATA_DIR = os.path.join(BASE_DIR, 'standby_data')
    LOGS_DIR = os.path.join(BASE_DIR, 'standby_logs')
    ROSTER_FILE = os.path.join(DATA_DIR, 'roster.json')
    
    # Overtime settings
    MONTHLY_OVERTIME_LIMIT = float(os.environ.get('MONTHLY_OVERTIME_LIMIT', '40'))
    OVERTIME_WARNING_THRESHOLD = float(os.environ.get('OVERTIME_WARNING_THRESHOLD', '35'))
    
    # Standby settings
    DEFAULT_ROTATION_DAYS = int(os.environ.get('DEFAULT_ROTATION_DAYS', '7'))
    
    # Dashboard settings
    DASHBOARD_REFRESH_INTERVAL = int(os.environ.get('DASHBOARD_REFRESH_INTERVAL', '300'))  # 5 minutes
    NOTIFICATION_AUTO_DISMISS = int(os.environ.get('NOTIFICATION_AUTO_DISMISS', '10'))  # 10 seconds
    
    # Team settings
    MAX_TEAM_MEMBERS = int(os.environ.get('MAX_TEAM_MEMBERS', '10'))
    
    # Export settings
    EXPORT_FORMATS = ['csv', 'pdf']
    DEFAULT_EXPORT_FORMAT = os.environ.get('DEFAULT_EXPORT_FORMAT', 'csv')
    
    # UI settings
    THEME_COLORS = {
        'primary': '#007bff',
        'success': '#28a745',
        'warning': '#ffc107',
        'danger': '#dc3545',
        'info': '#17a2b8',
        'secondary': '#6c757d'
    }
    
    # Person colors for calendar (fallback if not defined in roster)
    DEFAULT_PERSON_COLORS = {
        'Alice': '#007bff',
        'Bob': '#28a745',
        'Charlie': '#ffc107',
        'Diana': '#dc3545',
        'errol': '#17a2b8'  # Keep for backward compatibility
    }

# Create directories if they don't exist
def ensure_directories():
    """Ensure required directories exist"""
    directories = [StandbyConfig.DATA_DIR, StandbyConfig.LOGS_DIR]
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory) 