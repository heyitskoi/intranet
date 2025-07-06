"""
Assignment-based rotation manager for standby module.
Uses StandbyAssignment table to store actual assignments separately from rotation pattern.
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict
from sqlalchemy import and_, or_
from models import db, User, StandbyMember, StandbyOverride, StandbyAssignment, StandbyDurationConfig


class AssignmentRotationManager:
    """Manages standby assignments using the StandbyAssignment table."""
    
    @staticmethod
    def get_standby_person(date: str, department_id: int = None) -> Optional[str]:
        """
        Get the standby person for a specific date.
        For past dates: uses existing assignments.
        For future dates: generates assignment if needed.
        """
        try:
            target_date = datetime.strptime(date, '%Y-%m-%d').date()
        except ValueError:
            return None
        
        if not department_id:
            return None
        
        # First, check for existing assignment
        assignment = StandbyAssignment.query.filter_by(
            department_id=department_id,
            date=target_date
        ).join(User).first()
        
        if assignment:
            return assignment.user.username
        
        # If no assignment exists, check if it's a future date
        today = datetime.now().date()
        
        if target_date > today:
            # Generate assignment for future date
            AssignmentRotationManager._generate_assignment_for_date(target_date, department_id)
            
            # Fetch the newly created assignment
            assignment = StandbyAssignment.query.filter_by(
                department_id=department_id,
                date=target_date
            ).join(User).first()
            
            if assignment:
                return assignment.user.username
        
        return None
    
    @staticmethod
    def _generate_assignment_for_date(date: datetime.date, department_id: int) -> Optional[StandbyAssignment]:
        """Generate an assignment for a specific date using the rotation pattern."""
        try:
            # Check for override first
            override = StandbyOverride.query.filter_by(date=date).first()
            
            if override:
                # Verify the override person is still active in this department
                override_member = StandbyMember.query.filter_by(
                    user_id=override.user_id,
                    active=True
                ).join(User).filter(User.department_id == department_id).first()
                
                if override_member:
                    assignment = StandbyAssignment(
                        department_id=department_id,
                        user_id=override.user_id,
                        date=date
                    )
                    db.session.add(assignment)
                    db.session.commit()
                    return assignment
            
            # Use rotation pattern - only get active members who are in rotation
            active_members = StandbyMember.query.filter_by(active=True).join(User).filter(
                and_(
                    User.department_id == department_id,
                    StandbyMember.rotation_order.isnot(None)
                )
            ).order_by(StandbyMember.rotation_order).all()
            
            if not active_members:
                return None
            
            # Get department configuration
            config = StandbyDurationConfig.query.filter_by(department_id=department_id).first()
            if not config:
                return None
            
            # Calculate which person should be on standby
            days_since_start = (date - config.rotation_start_date).days
            
            if days_since_start < 0:
                return None
            
            # Calculate person index based on rotation pattern
            person_index = (days_since_start // config.standby_shift_days) % len(active_members)
            current_member = active_members[person_index]
            
            assignment = StandbyAssignment(
                department_id=department_id,
                user_id=current_member.user_id,
                date=date
            )
            db.session.add(assignment)
            db.session.commit()
            
            return assignment
            
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def regenerate_future_assignments(department_id: int, from_date: datetime.date = None) -> int:
        """
        Regenerate assignments for future dates when rotation pattern changes.
        Keeps existing assignments for past dates and respects overrides.
        """
        try:
            if from_date is None:
                from_date = datetime.now().date() + timedelta(days=1)
            
            # Only delete future assignments that are not overrides
            # First, get all overrides for future dates
            future_overrides = StandbyOverride.query.filter(
                StandbyOverride.date >= from_date
            ).all()
            override_dates = {o.date for o in future_overrides}
            
            # Delete existing future assignments that are not overrides
            deleted_count = StandbyAssignment.query.filter(
                and_(
                    StandbyAssignment.department_id == department_id,
                    StandbyAssignment.date >= from_date,
                    ~StandbyAssignment.date.in_(override_dates) if override_dates else True
                )
            ).delete()
            
            # Generate new assignments for the next 90 days
            end_date = from_date + timedelta(days=90)
            generated_count = 0
            
            current_date = from_date
            while current_date <= end_date:
                # Skip if assignment already exists (for overrides)
                existing = StandbyAssignment.query.filter_by(
                    department_id=department_id,
                    date=current_date
                ).first()
                
                if not existing:
                    assignment = AssignmentRotationManager._generate_assignment_for_date(
                        current_date, department_id
                    )
                    if assignment:
                        generated_count += 1
                
                current_date += timedelta(days=1)
            
            db.session.commit()
            return generated_count
            
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def get_assignments_for_date_range(
        start_date: str, 
        end_date: str, 
        department_id: int
    ) -> List[Dict]:
        """Get all assignments within a date range."""
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            raise ValueError("Invalid date format")
        
        assignments = StandbyAssignment.query.filter(
            and_(
                StandbyAssignment.department_id == department_id,
                StandbyAssignment.date >= start,
                StandbyAssignment.date <= end
            )
        ).join(User).order_by(StandbyAssignment.date).all()
        
        result = []
        for assignment in assignments:
            result.append({
                'date': assignment.date.strftime('%Y-%m-%d'),
                'username': assignment.user.username,
                'user_id': assignment.user_id,
                'created_at': assignment.created_at.isoformat()
            })
        
        return result
    
    @staticmethod
    def get_user_assignments(
        username: str, 
        start_date: str = None, 
        end_date: str = None
    ) -> List[Dict]:
        """Get all assignments for a specific user."""
        user = User.query.filter_by(username=username).first()
        if not user:
            return []
        
        query = StandbyAssignment.query.filter_by(user_id=user.id)
        
        if start_date:
            try:
                start = datetime.strptime(start_date, '%Y-%m-%d').date()
                query = query.filter(StandbyAssignment.date >= start)
            except ValueError:
                pass
        
        if end_date:
            try:
                end = datetime.strptime(end_date, '%Y-%m-%d').date()
                query = query.filter(StandbyAssignment.date <= end)
            except ValueError:
                pass
        
        assignments = query.order_by(StandbyAssignment.date).all()
        
        result = []
        for assignment in assignments:
            result.append({
                'date': assignment.date.strftime('%Y-%m-%d'),
                'department_id': assignment.department_id,
                'created_at': assignment.created_at.isoformat()
            })
        
        return result
    
    @staticmethod
    def create_manual_assignment(
        date: str, 
        username: str, 
        department_id: int
    ) -> StandbyAssignment:
        """Create a manual assignment for a specific date."""
        try:
            target_date = datetime.strptime(date, '%Y-%m-%d').date()
        except ValueError:
            raise ValueError(f"Invalid date format: {date}")
        
        user = User.query.filter_by(username=username).first()
        if not user:
            raise ValueError(f"User '{username}' not found")
        
        # Check if assignment already exists
        existing = StandbyAssignment.query.filter_by(
            department_id=department_id,
            date=target_date
        ).first()
        
        if existing:
            # Update existing assignment
            existing.user_id = user.id
            db.session.commit()
            return existing
        
        # Create new assignment
        assignment = StandbyAssignment(
            department_id=department_id,
            user_id=user.id,
            date=target_date
        )
        db.session.add(assignment)
        db.session.commit()
        
        return assignment
    
    @staticmethod
    def delete_assignment(date: str, department_id: int) -> bool:
        """Delete an assignment for a specific date."""
        try:
            target_date = datetime.strptime(date, '%Y-%m-%d').date()
        except ValueError:
            raise ValueError(f"Invalid date format: {date}")
        
        assignment = StandbyAssignment.query.filter_by(
            department_id=department_id,
            date=target_date
        ).first()
        
        if not assignment:
            return False
        
        db.session.delete(assignment)
        db.session.commit()
        return True
    
    @staticmethod
    def get_assignment_stats(department_id: int) -> Dict:
        """Get statistics about assignments for a department."""
        today = datetime.now().date()
        
        # Total assignments
        total_assignments = StandbyAssignment.query.filter_by(
            department_id=department_id
        ).count()
        
        # Past assignments
        past_assignments = StandbyAssignment.query.filter(
            and_(
                StandbyAssignment.department_id == department_id,
                StandbyAssignment.date < today
            )
        ).count()
        
        # Future assignments
        future_assignments = StandbyAssignment.query.filter(
            and_(
                StandbyAssignment.department_id == department_id,
                StandbyAssignment.date > today
            )
        ).count()
        
        # Today's assignment
        today_assignment = StandbyAssignment.query.filter(
            and_(
                StandbyAssignment.department_id == department_id,
                StandbyAssignment.date == today
            )
        ).join(User).first()
        
        return {
            'total_assignments': total_assignments,
            'past_assignments': past_assignments,
            'future_assignments': future_assignments,
            'today_assignment': today_assignment.user.username if today_assignment else None,
            'last_updated': datetime.now().isoformat()
        } 