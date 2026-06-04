import os
from datetime import datetime
from functools import wraps
from flask import request, jsonify, current_app
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
import bcrypt
from app import db
from app.database import User

def hash_password(password):
    """Hash password using bcrypt"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password, hashed):
    """Verify password against hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def generate_tokens(user_id, email, role):
    """Generate JWT tokens"""
    access_token = create_access_token(
        identity={'user_id': user_id, 'email': email, 'role': role}
    )
    refresh_token = create_refresh_token(
        identity={'user_id': user_id, 'email': email, 'role': role}
    )
    return {'access_token': access_token, 'refresh_token': refresh_token}

def role_required(role):
    """Decorator to check user role"""
    def decorator(fn):
        @wraps(fn)
        @jwt_required()
        def wrapper(*args, **kwargs):
            identity = get_jwt_identity()
            if identity['role'] != role:
                return {'error': 'Unauthorized'}, 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator

def teacher_required(fn):
    """Decorator for teacher-only routes"""
    return role_required('teacher')(fn)

def student_required(fn):
    """Decorator for student-only routes"""
    return role_required('student')(fn)