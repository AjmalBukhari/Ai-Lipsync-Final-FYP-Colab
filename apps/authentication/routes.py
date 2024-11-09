from flask import render_template, redirect, request, url_for, flash, current_app
from flask_login import current_user, login_user, logout_user

from apps import db, login_manager
from apps.authentication import blueprint
from apps.authentication.forms import LoginForm, CreateAccountForm
from apps.authentication.models import Users

from apps.authentication.util import verify_pass, hash_pass
from itsdangerous import URLSafeTimedSerializer

import logging

from pathlib import Path
from datetime import datetime



@blueprint.route('/')
def route_default():
    return redirect(url_for('authentication_blueprint.login'))

# Login & Registration

@blueprint.route('/login', methods=['GET', 'POST'])
def login():
    login_form = LoginForm(request.form)
    if 'login' in request.form:

        username = request.form['username']
        password = request.form['password']

        user = Users.query.filter_by(username=username).first()

        if user and verify_pass(password, user.password):

            login_user(user)

            base_dir = Path("apps") / "user_data"
            user_dir = base_dir / username
            video_dir = user_dir / "video"
            audio_dir = user_dir / "audio"
            output_dir = user_dir / "output"
            process_dir = user_dir / "process"
            trim_dir = user_dir / "trim"
            logs_dir = user_dir / "logs"
            profile_dir = user_dir / "profile"
            dp_dir = profile_dir / "dp"
        
            for directory in [base_dir, user_dir, video_dir, audio_dir, output_dir, process_dir, trim_dir, logs_dir, profile_dir, dp_dir]:
                directory.mkdir(parents=True, exist_ok=True)
            
            log_file = logs_dir / "log.txt"
            if not log_file.exists():
                with open(log_file, 'w') as f:
                    f.write(f"{username} logged in successfully.\n")
            else:
                log_user_action(username, "logged in successfully.\n")

            return redirect(url_for('authentication_blueprint.route_default'))

        return render_template('accounts/login.html', msg='Wrong user or password', form=login_form)

    if not current_user.is_authenticated:
        return render_template('accounts/login.html', form=login_form)
    
    return redirect(url_for('home_blueprint.route_template', template='index'))

def log_user_action(username, action):

    base_dir = Path("apps") / "user_data"
    logs_dir = base_dir / username / "logs"
    log_file = logs_dir / "log.txt"

    logs_dir.mkdir(parents=True, exist_ok=True)

    with open(log_file, 'a') as f:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        f.write(f"{timestamp}, {username}, {action}\n")

@blueprint.route('/register', methods=['GET', 'POST'])
def register():
    create_account_form = CreateAccountForm(request.form)
    if 'register' in request.form:

        username = request.form['username']
        email = request.form['email']

        user = Users.query.filter_by(username=username).first()
        if user:
            return render_template('accounts/register.html',
                                   msg='Username already registered',
                                   success=False,
                                   form=create_account_form)

        user = Users.query.filter_by(email=email).first()
        if user:
            return render_template('accounts/register.html',
                                   msg='Email already registered',
                                   success=False,
                                   form=create_account_form)

        if not current_user.is_authenticated:
            user = Users(**request.form)
            db.session.add(user)
            db.session.commit()
            log_user_action(username, "registred successfully")

        logout_user()
        
        return render_template('accounts/register.html',
                               msg='Account created successfully.',
                               success=True,
                               form=create_account_form)

    else:
        return render_template('accounts/register.html', form=create_account_form)


# Logout

@blueprint.route('/logout')
def logout():

    if current_user.is_authenticated:
        username = current_user.username
        log_user_action(username, "Logged out\n")
        logout_user()
    
    return redirect(url_for('authentication_blueprint.login'))

# Forgot Password

@blueprint.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')

        user = Users.query.filter_by(email=email).first()
        
        if user:
            token = generate_reset_token(user.id)
            flash('Set your new password.', 'success')
            return redirect(url_for('authentication_blueprint.reset_password', token=token))
        else:
            flash('Email not found. Please check and try again.', 'danger')

    return render_template('accounts/forgot_password.html')

# Reset Password

@blueprint.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user_id = verify_reset_token(token)

    if user_id is None:
        flash('The password reset link is invalid or has expired.', 'danger')
        return redirect(url_for('authentication_blueprint.forgot_password'))

    user = Users.query.get(user_id)
    if user is None:
        flash('User not found. Please try again.', 'danger')
        return redirect(url_for('authentication_blueprint.forgot_password'))

    if request.method == 'POST':
        new_password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if new_password is None or confirm_password is None:
            flash('Both password fields are required.', 'danger')
            return redirect(url_for('authentication_blueprint.reset_password', token=token))

        if new_password != confirm_password:
            flash('Passwords do not match. Please try again.', 'danger')
            return redirect(url_for('authentication_blueprint.reset_password', token=token))

        if len(new_password) < 5:  # Basic length check
            flash('Password must be at least 5 characters long.', 'danger')
            return redirect(url_for('authentication_blueprint.reset_password', token=token))
        
        try:
            # Hash the new password using hash_pass
            hashed_password = hash_pass(new_password)
            user.password = hashed_password
            db.session.commit() 
            flash('Password updated successfully. Please login.', 'success')
            return redirect(url_for('authentication_blueprint.login'))
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error hashing password: {e}")
            flash('An internal error occurred. Please try again.', 'danger')
            return redirect(url_for('authentication_blueprint.reset_password', token=token))

    return render_template('accounts/reset_password.html', token=token)


def generate_reset_token(user_id):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serializer.dumps(user_id, salt='password-reset-salt')

def verify_reset_token(token):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        user_id = serializer.loads(token, salt='password-reset-salt', max_age=3600)
        return user_id
    except Exception as e:
        logging.error(f"Token verification error: {e}")
        return None

# Delete User account

@blueprint.route('/delete_account', methods=['POST'])
def delete_account():
    if not current_user.is_authenticated:
        flash('You need to be logged in to delete your account.', 'danger')
        return redirect(url_for('authentication_blueprint.login'))

    try:
        # Delete the current user from the database
        user = Users.query.get(current_user.id)
        if user:
            db.session.delete(user)
            db.session.commit()
            if current_user.is_authenticated:
                username = current_user.username
                log_user_action(username, "Delete Account.")
                logout_user()
            
            flash('Your account has been deleted successfully.', 'success')
            return redirect(url_for('authentication_blueprint.login'))

        else:
            flash('User not found.', 'danger')
            return redirect(url_for('home_blueprint.index'))
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error deleting user account: {e}")
        flash('An error occurred while trying to delete your account. Please try again.', 'danger')
        return redirect(url_for('home_blueprint.index'))


# User Update Profile

@blueprint.route('/update_profile', methods=['POST'])
def update_profile():
    if not current_user.is_authenticated:
        flash('You need to be logged in to update your profile.', 'danger')
        return redirect(url_for('authentication_blueprint.login'))

    try:
        # Update user information
        user = Users.query.get(current_user.id)
        if user:
            user.email = request.form.get('email')
            user.first_name = request.form.get('first_name')
            user.last_name = request.form.get('last_name')
            user.address = request.form.get('address')
            user.city = request.form.get('city')
            user.country = request.form.get('country')
            user.postal_code = request.form.get('postal_code')
            user.about_me = request.form.get('about_me')

            db.session.commit()
            flash('Your profile has been updated successfully.', 'success')
            return redirect(url_for('home_blueprint.route_template', template='user'))
        
        if current_user.is_authenticated:
            username = current_user.username
            log_user_action(username, "update the profile.")

        else:
            flash('User not found.', 'danger')
            return redirect(url_for('home_blueprint.route_template', template='user'))
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error updating user profile: {e}")
        flash('An error occurred while trying to update your profile. Please try again.', 'danger')
        return redirect(url_for('home_blueprint.route_template', template='user'))


# Errors
@login_manager.unauthorized_handler
def unauthorized_handler():
    return render_template('home/page-403.html'), 403

@blueprint.errorhandler(403)
def access_forbidden(error):
    return render_template('home/page-403.html'), 403

@blueprint.errorhandler(404)
def not_found_error(error):
    return render_template('home/page-404.html'), 404

@blueprint.errorhandler(500)
def internal_error(error):
    return render_template('home/page-500.html'), 500
