from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.auth import auth_bp
from app.models import User


@auth_bp.route('/')
def index():
    return redirect(url_for('auth.login'))


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(get_dashboard_url(current_user.role))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password) and user.is_active:
            login_user(user, remember=bool(request.form.get('remember')))
            next_page = request.args.get('next')
            flash('Login successful!', 'success')
            return redirect(next_page or get_dashboard_url(user.role))
        else:
            flash('Invalid username or password.', 'danger')

    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


def get_dashboard_url(role):
    if role == 'admin':
        return url_for('admin.dashboard')
    elif role == 'teacher':
        return url_for('teacher.dashboard')
    elif role == 'student':
        return url_for('student.dashboard')
    return url_for('auth.login')
