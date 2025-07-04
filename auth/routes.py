"""Routes for authentication blueprint."""

from flask import render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required
from werkzeug.security import check_password_hash

from models import User
from . import auth_bp


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
