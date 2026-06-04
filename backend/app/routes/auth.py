from flask import Blueprint, request, jsonify
from app import db
from app.database import User, TeacherProfile, StudentProfile
from app.auth import hash_password, verify_password, generate_tokens
import re

bp = Blueprint('auth', __name__, url_prefix='/api/auth')

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    if not any(char.isupper() for char in password):
        return False, "Password must contain uppercase letter"
    if not any(char.isdigit() for char in password):
        return False, "Password must contain digit"
    return True, "Valid"

@bp.route('/register', methods=['POST'])
def register():
    """Register new user (teacher or student)"""
    try:
        data = request.get_json()
        
        # Validate input
        if not all(k in data for k in ['email', 'password', 'first_name', 'last_name', 'role']):
            return {'error': 'Missing required fields'}, 400
        
        email = data['email'].lower()
        password = data['password']
        first_name = data['first_name']
        last_name = data['last_name']
        role = data['role'].lower()  # 'teacher' or 'student'
        
        # Validate
        if not validate_email(email):
            return {'error': 'Invalid email format'}, 400
        
        is_valid, msg = validate_password(password)
        if not is_valid:
            return {'error': msg}, 400
        
        if role not in ['teacher', 'student']:
            return {'error': 'Role must be teacher or student'}, 400
        
        # Check if user exists
        if User.query.filter_by(email=email).first():
            return {'error': 'Email already registered'}, 409
        
        # Create user
        user = User(
            email=email,
            password=hash_password(password),
            first_name=first_name,
            last_name=last_name,
            role=role
        )
        db.session.add(user)
        db.session.flush()
        
        # Create profile
        if role == 'teacher':
            teacher = TeacherProfile(user_id=user.id)
            db.session.add(teacher)
        else:
            student = StudentProfile(user_id=user.id)
            db.session.add(student)
        
        db.session.commit()
        
        return {
            'message': 'User registered successfully',
            'user_id': user.id,
            'email': user.email,
            'role': user.role
        }, 201
    
    except Exception as e:
        db.session.rollback()
        return {'error': str(e)}, 500

@bp.route('/login', methods=['POST'])
def login():
    """Login user"""
    try:
        data = request.get_json()
        
        if not data.get('email') or not data.get('password'):
            return {'error': 'Email and password required'}, 400
        
        email = data['email'].lower()
        password = data['password']
        
        user = User.query.filter_by(email=email).first()
        
        if not user or not verify_password(password, user.password):
            return {'error': 'Invalid email or password'}, 401
        
        if not user.is_active:
            return {'error': 'User account is inactive'}, 403
        
        tokens = generate_tokens(user.id, user.email, user.role)
        
        return {
            'message': 'Login successful',
            'user_id': user.id,
            'email': user.email,
            'role': user.role,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'tokens': tokens
        }, 200
    
    except Exception as e:
        return {'error': str(e)}, 500

@bp.route('/refresh', methods=['POST'])
def refresh():
    """Refresh access token"""
    from flask_jwt_extended import jwt_required, get_jwt_identity
    
    @jwt_required()
    def refresh_token():
        identity = get_jwt_identity()
        tokens = generate_tokens(identity['user_id'], identity['email'], identity['role'])
        return {'tokens': tokens}, 200
    
    return refresh_token()

@bp.route('/profile', methods=['GET'])
def get_profile():
    """Get user profile"""
    from flask_jwt_extended import jwt_required, get_jwt_identity
    
    @jwt_required()
    def profile():
        identity = get_jwt_identity()
        user = User.query.get(identity['user_id'])
        
        if not user:
            return {'error': 'User not found'}, 404
        
        profile_data = {
            'user_id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role': user.role,
            'phone': user.phone,
            'is_verified': user.is_verified
        }
        
        if user.role == 'teacher':
            profile_data['teacher_profile'] = user.teacher_profile.to_dict() if user.teacher_profile else None
        else:
            profile_data['student_profile'] = user.student_profile.to_dict() if user.student_profile else None
        
        return profile_data, 200
    
    return profile()