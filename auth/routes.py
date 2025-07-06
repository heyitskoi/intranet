"""Routes for authentication blueprint."""

from flask import render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required
from werkzeug.security import check_password_hash, generate_password_hash

from models import User, Department, Role
from . import auth_bp


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Display and process the registration form."""
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        department_id = request.form.get('department_id')
        role_id = request.form.get('role_id')
        
        # Validation
        errors = []
        
        if not username or not email or not password:
            errors.append('All fields are required.')
        
        if password != confirm_password:
            errors.append('Passwords do not match.')
        
        if len(password) < 6:
            errors.append('Password must be at least 6 characters long.')
        
        # Check if user already exists
        if User.query.filter_by(username=username).first():
            errors.append('Username already exists.')
        
        if User.query.filter_by(email=email).first():
            errors.append('Email already exists.')
        
        # Validate department and role
        if department_id:
            department = Department.query.get(department_id)
            if not department:
                errors.append('Invalid department selected.')
        
        if role_id:
            role = Role.query.get(role_id)
            if not role:
                errors.append('Invalid role selected.')
        
        if errors:
            for error in errors:
                flash(error, 'danger')
            return redirect(url_for('auth.register'))
        
        # Create new user
        try:
            new_user = User(
                username=username,
                email=email,
                password_hash=generate_password_hash(password),
                department_id=department_id if department_id else None,
                role_id=role_id if role_id else None
            )
            
            from models import db
            db.session.add(new_user)
            db.session.commit()
            
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Registration failed: {str(e)}', 'danger')
            return redirect(url_for('auth.register'))
    
    # GET request - show registration form
    departments = Department.query.all()
    roles = Role.query.all()
    return render_template('register.html', departments=departments, roles=roles)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Display and process the login form."""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash('Logged in successfully.', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))

        flash('Invalid email or password.', 'danger')
        return redirect(url_for('auth.login'))

    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """Log the user out and redirect to login."""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
