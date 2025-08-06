import os
import secrets
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from ..extensions import db, oauth
from ..models import User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('main.dashboard'))
        else:
            flash('Invalid credentials. Please try again.', 'danger')
    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        user_by_username = User.query.filter_by(username=username).first()
        if user_by_username:
            flash('Username already exists. Please choose another.', 'warning')
            return redirect(url_for('auth.register'))

        user_by_email = User.query.filter_by(email=email).first()
        if user_by_email:
            flash('Email address is already registered. Please log in.', 'warning')
            return redirect(url_for('auth.login'))

        if password != confirm_password:
            flash('Passwords do not match. Please try again.', 'danger')
            return redirect(url_for('auth.register'))
            
        new_user = User(
            username=username, 
            email=email, 
            password=generate_password_hash(password, method='pbkdf2:sha256')
        )
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('register.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@auth_bp.route('/login/google')
def google_login():
    nonce = secrets.token_urlsafe(16)
    session['oauth_nonce'] = nonce
    redirect_uri = url_for('auth.google_callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri, nonce=nonce)

@auth_bp.route('/login/google/callback')
def google_callback():
    token = oauth.google.authorize_access_token()
    nonce = session.pop('oauth_nonce', None)
    user_info = oauth.google.parse_id_token(token, nonce=nonce)

    if not user_info:
        flash('Google login failed: unable to fetch user info.', 'danger')
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(email=user_info['email']).first()

    if not user:
        new_user = User(
            username=user_info['name'].replace(" ", "").lower(),
            email=user_info['email'],
            password=generate_password_hash(os.urandom(16).hex(), method='pbkdf2:sha256')
        )
        db.session.add(new_user)
        db.session.commit()
        user = new_user

    login_user(user)
    flash('You have been successfully logged in with Google.', 'success')
    return redirect(url_for('main.dashboard'))