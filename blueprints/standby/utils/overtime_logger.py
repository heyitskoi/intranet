import os
import csv
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import uuid
from ..config import StandbyConfig

config = StandbyConfig()

FIELDNAMES = [
    'id',
    'person',
    'start_time',
    'end_time',
    'duration_hours',
    'issue_description',
    'resolution_notes'
]

def get_log_path(person, year, month):
    """Get the path for a person's overtime log file"""
    # Ensure logs directory exists
    os.makedirs(config.LOGS_DIR, exist_ok=True)
    
    # Create person directory
    person_dir = os.path.join(config.LOGS_DIR, person)
    os.makedirs(person_dir, exist_ok=True)
    
    # Return file path
    return os.path.join(person_dir, f"{year:04d}-{month:02d}.csv")

def load_overtime_logs(person, year, month):
    """Load overtime logs for a specific person and month"""
    log_path = get_log_path(person, year, month)
    
    if not os.path.exists(log_path):
        return []
    
    logs = []
    try:
        with open(log_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                logs.append(row)
    except Exception as e:
        print(f"Error loading logs from {log_path}: {e}")
        return []
    
    return logs

def validate_overtime_entry(start_str, end_str):
    """Validate overtime entry times and calculate duration"""
    try:
        start_time = datetime.strptime(start_str, '%Y-%m-%d %H:%M')
        end_time = datetime.strptime(end_str, '%Y-%m-%d %H:%M')
        
        if end_time <= start_time:
            return False, "End time must be after start time"
        
        duration = end_time - start_time
        duration_hours = duration.total_seconds() / 3600
        
        if duration_hours > 24:
            return False, "Overtime entry cannot exceed 24 hours"
        
        return True, duration_hours
        
    except ValueError as e:
        return False, f"Invalid time format: {e}"

def save_overtime_entry(person, year, month, entry):
    """Save an overtime entry to CSV file"""
    log_path = get_log_path(person, year, month)
    
    # Add unique ID if not present
    if 'id' not in entry:
        entry['id'] = str(uuid.uuid4())
    
    # Ensure person field is set
    if 'person' not in entry:
        entry['person'] = person
    
    # Check if file exists to determine if we need to write headers
    file_exists = os.path.exists(log_path)
    
    # Define fieldnames
    fieldnames = ['id', 'person', 'start_time', 'end_time', 'duration_hours', 'issue_description', 'resolution_notes']
    
    try:
        with open(log_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            # Write headers if file is new
            if not file_exists:
                writer.writeheader()
            
            # Write the entry
            writer.writerow(entry)
            
    except Exception as e:
        print(f"Error saving overtime entry: {e}")
        raise

def update_overtime_entry(person, year, month, entry_id, updated_entry):
    """Update an existing overtime entry"""
    log_path = get_log_path(person, year, month)
    
    if not os.path.exists(log_path):
        return False
    
    logs = load_overtime_logs(person, year, month)
    
    # Find and update the entry
    for i, log in enumerate(logs):
        if log.get('id') == entry_id:
            # Update the entry
            logs[i].update(updated_entry)
            logs[i]['id'] = entry_id  # Ensure ID is preserved
            
            # Rewrite the entire file
            fieldnames = ['id', 'person', 'start_time', 'end_time', 'duration_hours', 'issue_description', 'resolution_notes']
            
            with open(log_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for log_entry in logs:
                    writer.writerow(log_entry)
            
            return True
    
    return False

def export_logs_to_pdf(person, year, month, output_pdf_path):
    """Export overtime logs to PDF format"""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        
        # Load logs
        logs = load_overtime_logs(person, year, month)
        
        if not logs:
            return False, "No logs found for the specified period"
        
        # Create PDF document
        doc = SimpleDocTemplate(output_pdf_path, pagesize=letter)
        story = []
        
        # Add title
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=30
        )
        
        title = Paragraph(f"Overtime Report - {person} ({year}-{month:02d})", title_style)
        story.append(title)
        story.append(Spacer(1, 20))
        
        # Prepare table data
        table_data = [['Date', 'Start Time', 'End Time', 'Hours', 'Issue', 'Resolution']]
        
        total_hours = 0
        for log in logs:
            start_time = log.get('start_time', '')
            end_time = log.get('end_time', '')
            duration = log.get('duration_hours', '0')
            issue = log.get('issue_description', '')
            resolution = log.get('resolution_notes', '')
            
            # Extract date from start time
            try:
                date_obj = datetime.strptime(start_time, '%Y-%m-%d %H:%M')
                date_str = date_obj.strftime('%Y-%m-%d')
                time_str = date_obj.strftime('%H:%M')
            except:
                date_str = start_time.split(' ')[0] if ' ' in start_time else start_time
                time_str = start_time.split(' ')[1] if ' ' in start_time else ''
            
            table_data.append([date_str, time_str, end_time.split(' ')[1] if ' ' in end_time else end_time, 
                             duration, issue[:50], resolution[:50]])
            
            try:
                total_hours += float(duration)
            except:
                pass
        
        # Add total row
        table_data.append(['', '', 'TOTAL:', f"{total_hours:.2f}", '', ''])
        
        # Create table
        table = Table(table_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(table)
        
        # Build PDF
        doc.build(story)
        return True, f"PDF exported successfully to {output_pdf_path}"
        
    except ImportError:
        return False, "reportlab library not installed. Install with: pip install reportlab"
    except Exception as e:
        return False, f"Error creating PDF: {e}"

def archive_old_csvs(person, current_year, current_month):
    """Archive old CSV files (older than 6 months)"""
    try:
        person_dir = os.path.join(config.LOGS_DIR, person)
        if not os.path.exists(person_dir):
            return
        
        archive_dir = os.path.join(person_dir, '_archive')
        os.makedirs(archive_dir, exist_ok=True)
        
        # Calculate cutoff date (6 months ago)
        cutoff_date = datetime(current_year, current_month, 1)
        for _ in range(6):
            if cutoff_date.month == 1:
                cutoff_date = datetime(cutoff_date.year - 1, 12, 1)
            else:
                cutoff_date = datetime(cutoff_date.year, cutoff_date.month - 1, 1)
        
        # Check each CSV file
        for filename in os.listdir(person_dir):
            if filename.endswith('.csv') and filename != '_archive':
                try:
                    # Parse date from filename (YYYY-MM.csv)
                    year, month = map(int, filename.replace('.csv', '').split('-'))
                    file_date = datetime(year, month, 1)
                    
                    if file_date < cutoff_date:
                        # Move to archive
                        old_path = os.path.join(person_dir, filename)
                        new_path = os.path.join(archive_dir, filename)
                        os.rename(old_path, new_path)
                        print(f"Archived {filename} for {person}")
                        
                except ValueError:
                    # Skip files that don't match the expected format
                    continue
                    
    except Exception as e:
        print(f"Error archiving files for {person}: {e}") 