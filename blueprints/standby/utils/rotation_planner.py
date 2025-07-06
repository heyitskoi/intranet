import json
from datetime import datetime, timedelta
from models import db, Department, StandbyDurationConfig, StandbyMember, FutureRotationPlan, User, StandbyAssignment
from .assignment_rotation_manager import AssignmentRotationManager


def create_future_rotation_plan(department_id, rotation_order, start_date, created_by_id, notes=None):
    """Create a new future rotation plan."""
    plan = FutureRotationPlan(
        department_id=department_id,
        rotation_order=json.dumps(rotation_order),
        start_date=start_date,
        created_by_id=created_by_id,
        notes=notes
    )
    db.session.add(plan)
    db.session.commit()
    return plan


def get_active_future_rotation_plan(department_id):
    """Get the active future rotation plan for a department."""
    today = datetime.now().date()
    return FutureRotationPlan.query.filter(
        FutureRotationPlan.department_id == department_id,
        FutureRotationPlan.start_date >= today
    ).order_by(FutureRotationPlan.start_date.asc()).first()


def promote_future_rotation_if_due(department_id):
    """Promote a future rotation plan to current if its start date has been reached."""
    today = datetime.now().date()
    plan = FutureRotationPlan.query.filter(
        FutureRotationPlan.department_id == department_id,
        FutureRotationPlan.start_date <= today
    ).order_by(FutureRotationPlan.start_date.asc()).first()
    
    if plan:
        # Apply the planned rotation
        rotation_order = json.loads(plan.rotation_order)
        
        # Update StandbyMember rotation_order
        for i, username in enumerate(rotation_order, 1):
            user = User.query.filter_by(username=username).first()
            if user:
                member = StandbyMember.query.filter_by(user_id=user.id).first()
                if member:
                    member.rotation_order = i
        
        db.session.commit()
        
        # Regenerate assignments
        regenerated_count = AssignmentRotationManager.regenerate_future_assignments(department_id)
        
        # Remove the plan
        db.session.delete(plan)
        db.session.commit()
        
        return True, regenerated_count
    
    return False, 0


def calculate_rotation_cycle_end(department_id):
    """Calculate when the current rotation cycle ends."""
    config = StandbyDurationConfig.query.filter_by(department_id=department_id).first()
    if not config:
        return None
    
    active_members = StandbyMember.query.filter_by(active=True).join(User).filter(
        User.department_id == department_id,
        StandbyMember.rotation_order.isnot(None)
    ).order_by(StandbyMember.rotation_order).all()
    
    if not active_members:
        return None
    
    n_members = len(active_members)
    shift_days = config.standby_shift_days
    today = datetime.now().date()
    
    # Find the last assignment date in the current cycle
    last_assignment = StandbyAssignment.query.filter_by(department_id=department_id).order_by(StandbyAssignment.date.desc()).first()
    
    if last_assignment and last_assignment.date > today:
        start_date = last_assignment.date + timedelta(days=1)
    else:
        start_date = today + timedelta(days=n_members * shift_days)
    
    return start_date


def delete_future_rotation_plan(department_id):
    """Delete any existing future rotation plan for a department."""
    plan = get_active_future_rotation_plan(department_id)
    if plan:
        db.session.delete(plan)
        db.session.commit()
        return True
    return False 