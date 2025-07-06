"""
Enhanced roster manager for standby module.
Provides modern database operations with better performance, security, and UX.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from sqlalchemy import and_, or_, desc, asc
from sqlalchemy.orm import joinedload
from flask import current_app
from models import db, User, StandbyMember, StandbyOverride, AuditLog
from flask_login import current_user


class EnhancedRosterManager:
    """Enhanced roster management with database-first operations."""
    
    @staticmethod
    def get_roster_summary() -> Dict:
        """Get roster summary with counts and statistics."""
        try:
            total_members = StandbyMember.query.count()
            active_members = StandbyMember.query.filter_by(active=True).count()
            in_rotation = StandbyMember.query.filter(
                and_(StandbyMember.active == True, StandbyMember.rotation_order.isnot(None))
            ).count()
            
            # Get recent activity
            recent_overrides = StandbyOverride.query.filter(
                StandbyOverride.date >= datetime.now().date() - timedelta(days=7)
            ).count()
            
            return {
                'total_members': total_members,
                'active_members': active_members,
                'inactive_members': total_members - active_members,
                'in_rotation': in_rotation,
                'recent_overrides': recent_overrides,
                'last_updated': datetime.now().isoformat()
            }
        except Exception as e:
            current_app.logger.error(f"Error getting roster summary: {e}")
            return {}
    
    @staticmethod
    def get_team_members_paginated(page: int = 1, per_page: int = 20, 
                                 search: str = None, status: str = None) -> Tuple[List, int]:
        """Get paginated team members with optional filtering."""
        try:
            query = StandbyMember.query.join(User).options(joinedload(StandbyMember.user))
            
            # Apply filters
            if search:
                query = query.filter(
                    or_(
                        User.username.ilike(f'%{search}%'),
                        User.email.ilike(f'%{search}%')
                    )
                )
            
            if status == 'active':
                query = query.filter(StandbyMember.active == True)
            elif status == 'inactive':
                query = query.filter(StandbyMember.active == False)
            elif status == 'in_rotation':
                query = query.filter(
                    and_(StandbyMember.active == True, StandbyMember.rotation_order.isnot(None))
                )
            
            # Get total count for pagination
            total = query.count()
            
            # Apply pagination and ordering
            members = query.order_by(StandbyMember.rotation_order.asc().nullslast(), 
                                   User.username.asc())\
                          .offset((page - 1) * per_page)\
                          .limit(per_page)\
                          .all()
            
            return members, total
            
        except Exception as e:
            current_app.logger.error(f"Error getting paginated team members: {e}")
            return [], 0
    
    @staticmethod
    def get_rotation_order() -> List[Dict]:
        """Get current rotation order with member details."""
        try:
            members = StandbyMember.query.filter(
                and_(StandbyMember.active == True, StandbyMember.rotation_order.isnot(None))
            ).join(User).order_by(StandbyMember.rotation_order.asc()).all()
            
            return [
                {
                    'id': member.id,
                    'username': member.user.username,
                    'email': member.user.email,
                    'color': member.color,
                    'rotation_order': member.rotation_order,
                    'last_standby': EnhancedRosterManager._get_last_standby_date(member.user_id)
                }
                for member in members
            ]
        except Exception as e:
            current_app.logger.error(f"Error getting rotation order: {e}")
            return []
    
    @staticmethod
    def add_member_to_roster(username: str, color: str = '#007bff', 
                           active: bool = True, add_to_rotation: bool = False) -> bool:
        """Add a user to the standby roster."""
        try:
            # Validate user exists
            user = User.query.filter_by(username=username).first()
            if not user:
                raise ValueError(f"User '{username}' not found")
            
            # Check if already in roster
            existing = StandbyMember.query.filter_by(user_id=user.id).first()
            if existing:
                raise ValueError(f"User '{username}' is already in the roster")
            
            # Determine rotation order if adding to rotation
            rotation_order = None
            if add_to_rotation:
                max_order = db.session.query(db.func.max(StandbyMember.rotation_order)).scalar()
                rotation_order = (max_order or 0) + 1
            
            # Create standby member
            member = StandbyMember(
                user_id=user.id,
                color=color,
                active=active,
                rotation_order=rotation_order
            )
            
            db.session.add(member)
            
            # Log the action
            EnhancedRosterManager._log_audit_action(
                'add_member', 
                f"Added {username} to standby roster",
                {'username': username, 'color': color, 'active': active, 'rotation_order': rotation_order}
            )
            
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error adding member to roster: {e}")
            raise
    
    @staticmethod
    def update_member(username: str, **kwargs) -> bool:
        """Update standby member properties."""
        try:
            member = StandbyMember.query.join(User).filter(User.username == username).first()
            if not member:
                raise ValueError(f"Standby member '{username}' not found")
            
            # Track changes for audit
            changes = {}
            for key, value in kwargs.items():
                if hasattr(member, key) and getattr(member, key) != value:
                    changes[key] = {'old': getattr(member, key), 'new': value}
                    setattr(member, key, value)
            
            if changes:
                member.updated_at = datetime.utcnow()
                
                # Log the action
                EnhancedRosterManager._log_audit_action(
                    'update_member',
                    f"Updated {username} in standby roster",
                    {'username': username, 'changes': changes}
                )
                
                db.session.commit()
            
            return True
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating member: {e}")
            raise
    
    @staticmethod
    def remove_member_from_roster(username: str) -> bool:
        """Remove a user from the standby roster."""
        try:
            member = StandbyMember.query.join(User).filter(User.username == username).first()
            if not member:
                raise ValueError(f"Standby member '{username}' not found")
            
            # Log before deletion
            EnhancedRosterManager._log_audit_action(
                'remove_member',
                f"Removed {username} from standby roster",
                {'username': username, 'member_id': member.id}
            )
            
            db.session.delete(member)
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error removing member: {e}")
            raise
    
    @staticmethod
    def update_rotation_order(new_order: List[str]) -> bool:
        """Update the rotation order with proper reordering."""
        try:
            # Validate all usernames exist in roster
            members = StandbyMember.query.join(User).filter(
                User.username.in_(new_order)
            ).all()
            
            if len(members) != len(new_order):
                missing = set(new_order) - {m.user.username for m in members}
                raise ValueError(f"Users not found in roster: {missing}")
            
            # Update rotation order
            for i, username in enumerate(new_order, 1):
                member = next(m for m in members if m.user.username == username)
                member.rotation_order = i
                member.updated_at = datetime.utcnow()
            
            # Log the action
            EnhancedRosterManager._log_audit_action(
                'update_rotation',
                f"Updated rotation order: {', '.join(new_order)}",
                {'new_order': new_order}
            )
            
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating rotation order: {e}")
            raise
    
    @staticmethod
    def add_override(date: str, username: str, reason: str = None) -> bool:
        """Add a date override."""
        try:
            # Validate user exists in roster
            member = StandbyMember.query.join(User).filter(User.username == username).first()
            if not member:
                raise ValueError(f"User '{username}' not found in roster")
            
            # Parse date
            try:
                override_date = datetime.strptime(date, '%Y-%m-%d').date()
            except ValueError:
                raise ValueError(f"Invalid date format: {date}")
            
            # Check if override already exists
            existing = StandbyOverride.query.filter_by(date=override_date).first()
            if existing:
                raise ValueError(f"Override already exists for {date}")
            
            # Create override
            override = StandbyOverride(
                date=override_date,
                user_id=member.user_id,
                reason=reason,
                created_by_id=current_user.id
            )
            
            db.session.add(override)
            
            # Log the action
            EnhancedRosterManager._log_audit_action(
                'add_override',
                f"Added override for {date}: {username}",
                {'date': date, 'username': username, 'reason': reason}
            )
            
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error adding override: {e}")
            raise
    
    @staticmethod
    def get_overrides_paginated(page: int = 1, per_page: int = 20, 
                              start_date: str = None, end_date: str = None) -> Tuple[List, int]:
        """Get paginated overrides with optional date filtering."""
        try:
            query = StandbyOverride.query.join(User, StandbyOverride.user_id == User.id)\
                                        .options(joinedload(StandbyOverride.user))
            
            # Apply date filters
            if start_date:
                start = datetime.strptime(start_date, '%Y-%m-%d').date()
                query = query.filter(StandbyOverride.date >= start)
            
            if end_date:
                end = datetime.strptime(end_date, '%Y-%m-%d').date()
                query = query.filter(StandbyOverride.date <= end)
            
            # Get total count
            total = query.count()
            
            # Apply pagination and ordering
            overrides = query.order_by(desc(StandbyOverride.date))\
                            .offset((page - 1) * per_page)\
                            .limit(per_page)\
                            .all()
            
            return overrides, total
            
        except Exception as e:
            current_app.logger.error(f"Error getting paginated overrides: {e}")
            return [], 0
    
    @staticmethod
    def remove_override(date: str) -> bool:
        """Remove a date override."""
        try:
            override_date = datetime.strptime(date, '%Y-%m-%d').date()
            override = StandbyOverride.query.filter_by(date=override_date).first()
            
            if not override:
                raise ValueError(f"No override found for {date}")
            
            # Log before deletion
            EnhancedRosterManager._log_audit_action(
                'remove_override',
                f"Removed override for {date}",
                {'date': date, 'override_id': override.id}
            )
            
            db.session.delete(override)
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error removing override: {e}")
            raise
    
    @staticmethod
    def get_available_users_for_roster(department_id: int = None) -> List[Dict]:
        """Get users not currently in the roster for dropdown, filtered by department."""
        try:
            from flask_login import current_user
            
            # Get current user's department if not specified
            if department_id is None:
                department_id = current_user.department.id if current_user.department else None
            
            # Get users not in standby roster, filtered by department
            subquery = db.session.query(StandbyMember.user_id)
            
            if department_id:
                # Filter by specific department
                available_users = User.query.filter(
                    and_(
                        User.department_id == department_id,
                        ~User.id.in_(subquery)
                    )
                ).order_by(User.username.asc()).all()
            else:
                # If no department, only show users without departments
                available_users = User.query.filter(
                    and_(
                        User.department_id.is_(None),
                        ~User.id.in_(subquery)
                    )
                ).order_by(User.username.asc()).all()
            
            return [
                {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'department': user.department.name if user.department else None
                }
                for user in available_users
            ]
        except Exception as e:
            current_app.logger.error(f"Error getting available users: {e}")
            return []
    
    @staticmethod
    def get_standby_person_for_date(date: str) -> Optional[Dict]:
        """Get the standby person for a specific date."""
        try:
            target_date = datetime.strptime(date, '%Y-%m-%d').date()
            
            # Check for override first
            override = StandbyOverride.query.join(User).filter_by(date=target_date).first()
            if override:
                return {
                    'username': override.user.username,
                    'email': override.user.email,
                    'color': override.user.standby_member.color if override.user.standby_member else '#6c757d',
                    'type': 'override',
                    'reason': override.reason
                }
            
            # Calculate from rotation
            rotation_members = StandbyMember.query.filter(
                and_(StandbyMember.active == True, StandbyMember.rotation_order.isnot(None))
            ).join(User).order_by(StandbyMember.rotation_order.asc()).all()
            
            if not rotation_members:
                return None
            
            # Calculate days since epoch for consistent rotation
            epoch = datetime(2020, 1, 1).date()
            days_since_epoch = (target_date - epoch).days
            
            # Get person based on rotation
            member_index = days_since_epoch % len(rotation_members)
            member = rotation_members[member_index]
            
            return {
                'username': member.user.username,
                'email': member.user.email,
                'color': member.color,
                'type': 'rotation',
                'rotation_order': member.rotation_order
            }
            
        except Exception as e:
            current_app.logger.error(f"Error getting standby person for date: {e}")
            return None
    
    @staticmethod
    def _get_last_standby_date(user_id: int) -> Optional[str]:
        """Get the last date this user was on standby."""
        try:
            # This would need to be implemented based on your overtime logging
            # For now, return None
            return None
        except Exception as e:
            current_app.logger.error(f"Error getting last standby date: {e}")
            return None
    
    @staticmethod
    def _log_audit_action(action: str, description: str, details: Dict) -> None:
        """Log audit action for tracking changes."""
        try:
            if current_user.is_authenticated:
                audit_log = AuditLog(
                    user_id=current_user.id,
                    action=action,
                    description=description,
                    details=details,
                    timestamp=datetime.utcnow()
                )
                db.session.add(audit_log)
        except Exception as e:
            current_app.logger.error(f"Error logging audit action: {e}")


# Convenience functions for backward compatibility
def get_roster_summary():
    return EnhancedRosterManager.get_roster_summary()

def get_team_members_paginated(page=1, per_page=20, search=None, status=None):
    return EnhancedRosterManager.get_team_members_paginated(page, per_page, search, status)

def get_rotation_order():
    return EnhancedRosterManager.get_rotation_order()

def add_member_to_roster(username, color='#007bff', active=True, add_to_rotation=False):
    return EnhancedRosterManager.add_member_to_roster(username, color, active, add_to_rotation)

def update_member(username, **kwargs):
    return EnhancedRosterManager.update_member(username, **kwargs)

def remove_member_from_roster(username):
    return EnhancedRosterManager.remove_member_from_roster(username)

def update_rotation_order(new_order):
    return EnhancedRosterManager.update_rotation_order(new_order)

def add_override(date, username, reason=None):
    return EnhancedRosterManager.add_override(date, username, reason)

def get_overrides_paginated(page=1, per_page=20, start_date=None, end_date=None):
    return EnhancedRosterManager.get_overrides_paginated(page, per_page, start_date, end_date)

def remove_override(date):
    return EnhancedRosterManager.remove_override(date)

def get_available_users_for_roster(department_id=None):
    return EnhancedRosterManager.get_available_users_for_roster(department_id)

def get_standby_person_for_date(date):
    return EnhancedRosterManager.get_standby_person_for_date(date) 