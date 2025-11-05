from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from datetime import datetime
from models import db, SuperAdmin, Admin, User, SystemLog

auth_bp = Blueprint('auth', __name__)

def log_activity(action, user_type, user_id, user_email, details=None):
    try:
        log = SystemLog(
            action=action,
            user_type=user_type,
            user_id=user_id,
            user_email=user_email,
            details=details,
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()
    except:
        pass

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    
    user = None
    user_type = None
    
    superadmin = SuperAdmin.query.filter_by(email=email).first()
    if superadmin and superadmin.check_password(password):
        if not superadmin.is_active:
            return jsonify({'error': 'Account is inactive'}), 403
        user = superadmin
        user_type = 'superadmin'
    
    if not user:
        admin = Admin.query.filter_by(email=email).first()
        if admin and admin.check_password(password):
            if not admin.is_active:
                return jsonify({'error': 'Account is inactive'}), 403
            user = admin
            user_type = 'admin'
    
    if not user:
        regular_user = User.query.filter_by(email=email).first()
        if regular_user and regular_user.check_password(password):
            if regular_user.status != 'active':
                return jsonify({'error': 'Account is inactive'}), 403
            user = regular_user
            user_type = 'user'
    
    if not user:
        return jsonify({'error': 'Invalid credentials'}), 401
    
    user.last_login = datetime.utcnow()
    db.session.commit()
    
    access_token = create_access_token(
        identity={'id': user.id, 'type': user_type, 'email': user.email}
    )
    
    log_activity('login', user_type, user.id, user.email, 'User logged in')
    
    return jsonify({
        'access_token': access_token,
        'user': user.to_dict(),
        'user_type': user_type
    })

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    phone = data.get('phone', '')
    department = data.get('department', '')
    
    if not all([name, email, password]):
        return jsonify({'error': 'Name, email and password required'}), 400
    
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 400
    
    if Admin.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 400
    
    if SuperAdmin.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 400
    
    user = User(
        name=name,
        email=email,
        phone=phone,
        department=department
    )
    user.set_password(password)
    
    db.session.add(user)
    db.session.commit()
    
    log_activity('register', 'user', user.id, user.email, 'New user registered')
    
    return jsonify({
        'message': 'Registration successful',
        'user': user.to_dict()
    }), 201

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    identity = get_jwt_identity()
    user_type = identity.get('type')
    user_id = identity.get('id')
    
    if user_type == 'superadmin':
        user = SuperAdmin.query.get(user_id)
    elif user_type == 'admin':
        user = Admin.query.get(user_id)
    elif user_type == 'user':
        user = User.query.get(user_id)
    else:
        return jsonify({'error': 'Invalid user type'}), 400
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({
        'user': user.to_dict(),
        'user_type': user_type
    })

@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    identity = get_jwt_identity()
    data = request.get_json()
    
    old_password = data.get('old_password')
    new_password = data.get('new_password')
    
    if not all([old_password, new_password]):
        return jsonify({'error': 'Both passwords required'}), 400
    
    user_type = identity.get('type')
    user_id = identity.get('id')
    
    if user_type == 'superadmin':
        user = SuperAdmin.query.get(user_id)
    elif user_type == 'admin':
        user = Admin.query.get(user_id)
    elif user_type == 'user':
        user = User.query.get(user_id)
    else:
        return jsonify({'error': 'Invalid user type'}), 400
    
    if not user or not user.check_password(old_password):
        return jsonify({'error': 'Invalid old password'}), 401
    
    user.set_password(new_password)
    db.session.commit()
    
    log_activity('password_change', user_type, user.id, user.email, 'Password changed')
    
    return jsonify({'message': 'Password changed successfully'})
