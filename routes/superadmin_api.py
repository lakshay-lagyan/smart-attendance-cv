from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from sqlalchemy import func
from models import db, SuperAdmin, Admin, User, Person, Attendance, EnrollmentRequest, SystemLog

superadmin_api_bp = Blueprint('superadmin_api', __name__)

def require_superadmin(fn):
    @jwt_required()
    def wrapper(*args, **kwargs):
        identity = get_jwt_identity()
        if identity.get('type') != 'superadmin':
            return jsonify({'error': 'Super admin access required'}), 403
        return fn(*args, **kwargs)
    wrapper.__name__ = fn.__name__
    return wrapper

@superadmin_api_bp.route('/stats', methods=['GET'])
@require_superadmin
def get_stats():
    total_admins = Admin.query.filter_by(is_active=True).count()
    total_users = User.query.filter_by(status='active').count()
    total_persons = Person.query.filter_by(status='active').count()
    total_attendance = Attendance.query.count()
    pending_enrollments = EnrollmentRequest.query.filter_by(status='pending').count()
    
    today = datetime.utcnow().date()
    today_attendance = Attendance.query.filter(
        func.date(Attendance.timestamp) == today
    ).count()
    
    return jsonify({
        'total_admins': total_admins,
        'total_users': total_users,
        'total_persons': total_persons,
        'total_attendance': total_attendance,
        'today_attendance': today_attendance,
        'pending_enrollments': pending_enrollments
    })

@superadmin_api_bp.route('/admins', methods=['GET'])
@require_superadmin
def get_admins():
    admins = Admin.query.all()
    return jsonify({'admins': [admin.to_dict() for admin in admins]})

@superadmin_api_bp.route('/admins', methods=['POST'])
@require_superadmin
def create_admin():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    department = data.get('department', '')
    
    if not all([name, email, password]):
        return jsonify({'error': 'Name, email and password required'}), 400
    
    if Admin.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already exists'}), 400
    
    identity = get_jwt_identity()
    superadmin_id = identity.get('id')
    
    admin = Admin(
        name=name,
        email=email,
        department=department,
        created_by=superadmin_id
    )
    admin.set_password(password)
    
    db.session.add(admin)
    db.session.commit()
    
    log = SystemLog(
        action='create_admin',
        user_type='superadmin',
        user_id=superadmin_id,
        user_email=identity.get('email'),
        details=f'Created admin: {email}',
        ip_address=request.remote_addr
    )
    db.session.add(log)
    db.session.commit()
    
    return jsonify({
        'message': 'Admin created successfully',
        'admin': admin.to_dict()
    }), 201

@superadmin_api_bp.route('/admins/<int:admin_id>', methods=['PUT'])
@require_superadmin
def update_admin(admin_id):
    admin = Admin.query.get(admin_id)
    if not admin:
        return jsonify({'error': 'Admin not found'}), 404
    
    data = request.get_json()
    admin.name = data.get('name', admin.name)
    admin.department = data.get('department', admin.department)
    admin.is_active = data.get('is_active', admin.is_active)
    
    if data.get('password'):
        admin.set_password(data['password'])
    
    db.session.commit()
    
    identity = get_jwt_identity()
    log = SystemLog(
        action='update_admin',
        user_type='superadmin',
        user_id=identity.get('id'),
        user_email=identity.get('email'),
        details=f'Updated admin: {admin.email}',
        ip_address=request.remote_addr
    )
    db.session.add(log)
    db.session.commit()
    
    return jsonify({
        'message': 'Admin updated successfully',
        'admin': admin.to_dict()
    })

@superadmin_api_bp.route('/admins/<int:admin_id>', methods=['DELETE'])
@require_superadmin
def delete_admin(admin_id):
    admin = Admin.query.get(admin_id)
    if not admin:
        return jsonify({'error': 'Admin not found'}), 404
    
    admin.is_active = False
    db.session.commit()
    
    identity = get_jwt_identity()
    log = SystemLog(
        action='delete_admin',
        user_type='superadmin',
        user_id=identity.get('id'),
        user_email=identity.get('email'),
        details=f'Deleted admin: {admin.email}',
        ip_address=request.remote_addr
    )
    db.session.add(log)
    db.session.commit()
    
    return jsonify({'message': 'Admin deleted successfully'})

@superadmin_api_bp.route('/users', methods=['GET'])
@require_superadmin
def get_all_users():
    users = User.query.all()
    return jsonify({'users': [user.to_dict() for user in users]})

@superadmin_api_bp.route('/users/<int:user_id>', methods=['PUT'])
@require_superadmin
def update_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json()
    user.name = data.get('name', user.name)
    user.department = data.get('department', user.department)
    user.phone = data.get('phone', user.phone)
    user.status = data.get('status', user.status)
    
    db.session.commit()
    
    return jsonify({
        'message': 'User updated successfully',
        'user': user.to_dict()
    })

@superadmin_api_bp.route('/logs', methods=['GET'])
@require_superadmin
def get_system_logs():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    logs = SystemLog.query.order_by(SystemLog.timestamp.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'logs': [log.to_dict() for log in logs.items],
        'total': logs.total,
        'pages': logs.pages,
        'current_page': page
    })

@superadmin_api_bp.route('/attendance/stats', methods=['GET'])
@require_superadmin
def get_attendance_stats():
    days = request.args.get('days', 7, type=int)
    start_date = datetime.utcnow() - timedelta(days=days)
    
    daily_stats = db.session.query(
        func.date(Attendance.timestamp).label('date'),
        func.count(Attendance.id).label('count')
    ).filter(
        Attendance.timestamp >= start_date
    ).group_by(
        func.date(Attendance.timestamp)
    ).all()
    
    return jsonify({
        'daily_attendance': [
            {'date': str(stat.date), 'count': stat.count}
            for stat in daily_stats
        ]
    })
