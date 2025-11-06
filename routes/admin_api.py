from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from sqlalchemy import func
import pickle
import base64
from models import db, Admin, User, Person, Attendance, EnrollmentRequest, SignupRequest, LeaveRequest, SystemLog
from face_service import face_service

admin_api_bp = Blueprint('admin_api', __name__)

def require_admin(fn):
    @jwt_required()
    def wrapper(*args, **kwargs):
        identity = get_jwt_identity()
        user_type = identity.get('type')
        if user_type not in ['admin', 'superadmin']:
            return jsonify({'error': 'Admin access required'}), 403
        return fn(*args, **kwargs)
    wrapper.__name__ = fn.__name__
    return wrapper

@admin_api_bp.route('/stats', methods=['GET'])
@require_admin
def get_dashboard_stats():
    total_users = User.query.filter_by(status='active').count()
    total_enrolled = Person.query.filter_by(status='active').count()
    pending_requests = EnrollmentRequest.query.filter_by(status='pending').count()
    
    today = datetime.utcnow().date()
    today_attendance = Attendance.query.filter(
        func.date(Attendance.timestamp) == today
    ).count()
    
    return jsonify({
        'total_users': total_users,
        'total_enrolled': total_enrolled,
        'pending_requests': pending_requests,
        'today_attendance': today_attendance
    })

@admin_api_bp.route('/enrollment/requests', methods=['GET'])
@require_admin
def get_enrollment_requests():
    status = request.args.get('status', 'pending')
    requests = EnrollmentRequest.query.filter_by(status=status).order_by(
        EnrollmentRequest.submitted_at.desc()
    ).all()
    
    return jsonify({
        'requests': [req.to_dict(include_images=True) for req in requests]
    })

@admin_api_bp.route('/enrollment/requests/<int:request_id>/approve', methods=['POST'])
@require_admin
def approve_enrollment_request(request_id):
    enroll_req = EnrollmentRequest.query.get(request_id)
    if not enroll_req:
        return jsonify({'error': 'Request not found'}), 404
    
    if enroll_req.status != 'pending':
        return jsonify({'error': 'Request already processed'}), 400
    
    try:
        embeddings = []
        for img_data in enroll_req.images:
            image = face_service.base64_to_image(img_data)
            embedding = face_service.extract_embedding(image)
            
            if embedding is not None:
                embeddings.append(embedding)
        
        if len(embeddings) == 0:
            return jsonify({'error': 'No valid faces detected'}), 400
        
        avg_embedding = sum(embeddings) / len(embeddings)
        
        person = Person(
            name=enroll_req.name,
            user_id=enroll_req.user_id,
            embedding=pickle.dumps(avg_embedding),
            embedding_dim=len(avg_embedding),
            photos_count=len(embeddings)
        )
        db.session.add(person)
        
        user = User.query.get(enroll_req.user_id)
        if user:
            user.is_enrolled = True
        
        identity = get_jwt_identity()
        enroll_req.status = 'approved'
        enroll_req.processed_at = datetime.utcnow()
        enroll_req.processed_by = identity.get('email')
        
        db.session.commit()
        
        face_service.add_person(person.id, embeddings)
        
        log = SystemLog(
            action='approve_enrollment',
            user_type=identity.get('type'),
            user_id=identity.get('id'),
            user_email=identity.get('email'),
            details=f'Approved enrollment for {enroll_req.email}',
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify({
            'message': 'Enrollment approved successfully',
            'person': person.to_dict()
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_api_bp.route('/enrollment/requests/<int:request_id>/reject', methods=['POST'])
@require_admin
def reject_enrollment_request(request_id):
    enroll_req = EnrollmentRequest.query.get(request_id)
    if not enroll_req:
        return jsonify({'error': 'Request not found'}), 404
    
    if enroll_req.status != 'pending':
        return jsonify({'error': 'Request already processed'}), 400
    
    data = request.get_json()
    reason = data.get('reason', 'Not specified')
    
    identity = get_jwt_identity()
    enroll_req.status = 'rejected'
    enroll_req.processed_at = datetime.utcnow()
    enroll_req.processed_by = identity.get('email')
    enroll_req.rejection_reason = reason
    
    db.session.commit()
    
    log = SystemLog(
        action='reject_enrollment',
        user_type=identity.get('type'),
        user_id=identity.get('id'),
        user_email=identity.get('email'),
        details=f'Rejected enrollment for {enroll_req.email}: {reason}',
        ip_address=request.remote_addr
    )
    db.session.add(log)
    db.session.commit()
    
    return jsonify({'message': 'Enrollment rejected'})

@admin_api_bp.route('/enrollment/direct', methods=['POST'])
@require_admin
def direct_enrollment():
    data = request.get_json()
    name = data.get('name')
    images = data.get('images', [])
    
    if not name or len(images) < 3:
        return jsonify({'error': 'Name and at least 3 images required'}), 400
    
    try:
        embeddings = []
        for img_data in images:
            image = face_service.base64_to_image(img_data)
            embedding = face_service.extract_embedding(image)
            
            if embedding is not None:
                embeddings.append(embedding)
        
        if len(embeddings) < 2:
            return jsonify({'error': 'At least 2 valid faces required'}), 400
        
        avg_embedding = sum(embeddings) / len(embeddings)
        
        person = Person(
            name=name,
            embedding=pickle.dumps(avg_embedding),
            embedding_dim=len(avg_embedding),
            photos_count=len(embeddings)
        )
        db.session.add(person)
        db.session.commit()
        
        face_service.add_person(person.id, embeddings)
        
        identity = get_jwt_identity()
        log = SystemLog(
            action='direct_enrollment',
            user_type=identity.get('type'),
            user_id=identity.get('id'),
            user_email=identity.get('email'),
            details=f'Enrolled person directly: {name}',
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify({
            'message': 'Person enrolled successfully',
            'person': person.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_api_bp.route('/persons', methods=['GET'])
@require_admin
def get_persons():
    persons = Person.query.filter_by(status='active').all()
    return jsonify({'persons': [p.to_dict() for p in persons]})

@admin_api_bp.route('/attendance', methods=['GET'])
@require_admin
def get_attendance():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    attendance = Attendance.query.order_by(Attendance.timestamp.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'attendance': [a.to_dict() for a in attendance.items],
        'total': attendance.total,
        'pages': attendance.pages,
        'current_page': page
    })

@admin_api_bp.route('/users', methods=['GET'])
@require_admin
def get_users():
    users = User.query.filter_by(status='active').all()
    return jsonify({'users': [u.to_dict() for u in users]})

# Signup Request Management
@admin_api_bp.route('/signup/requests', methods=['GET'])
@require_admin
def get_signup_requests():
    status = request.args.get('status', 'pending')
    requests = SignupRequest.query.filter_by(status=status).order_by(
        SignupRequest.submitted_at.desc()
    ).all()
    
    return jsonify({
        'requests': [req.to_dict(include_documents=True) for req in requests]
    })

@admin_api_bp.route('/signup/requests/count', methods=['GET'])
@require_admin
def get_signup_requests_count():
    count = SignupRequest.query.filter_by(status='pending').count()
    return jsonify({'count': count})

@admin_api_bp.route('/signup/requests/<int:request_id>/approve', methods=['POST'])
@require_admin
def approve_signup_request(request_id):
    signup_req = SignupRequest.query.get(request_id)
    if not signup_req:
        return jsonify({'error': 'Request not found'}), 404
    
    if signup_req.status != 'pending':
        return jsonify({'error': 'Request already processed'}), 400
    
    try:
        # Create user from signup request
        user = User(
            name=signup_req.name,
            email=signup_req.email,
            phone=signup_req.phone,
            department=signup_req.department,
            profile_image=signup_req.profile_image,
            status='active'
        )
        user.password_hash = signup_req.password_hash  # Copy hashed password directly
        
        db.session.add(user)
        
        identity = get_jwt_identity()
        signup_req.status = 'approved'
        signup_req.processed_at = datetime.utcnow()
        signup_req.processed_by = identity.get('email')
        
        db.session.commit()
        
        log = SystemLog(
            action='approve_signup',
            user_type=identity.get('type'),
            user_id=identity.get('id'),
            user_email=identity.get('email'),
            details=f'Approved signup for {signup_req.email}',
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify({
            'message': 'Signup request approved successfully',
            'user': user.to_dict()
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_api_bp.route('/signup/requests/<int:request_id>/reject', methods=['POST'])
@require_admin
def reject_signup_request(request_id):
    signup_req = SignupRequest.query.get(request_id)
    if not signup_req:
        return jsonify({'error': 'Request not found'}), 404
    
    if signup_req.status != 'pending':
        return jsonify({'error': 'Request already processed'}), 400
    
    data = request.get_json()
    reason = data.get('reason', 'Not specified')
    
    identity = get_jwt_identity()
    signup_req.status = 'rejected'
    signup_req.processed_at = datetime.utcnow()
    signup_req.processed_by = identity.get('email')
    signup_req.rejection_reason = reason
    
    db.session.commit()
    
    log = SystemLog(
        action='reject_signup',
        user_type=identity.get('type'),
        user_id=identity.get('id'),
        user_email=identity.get('email'),
        details=f'Rejected signup for {signup_req.email}: {reason}',
        ip_address=request.remote_addr
    )
    db.session.add(log)
    db.session.commit()
    
    return jsonify({'message': 'Signup request rejected'})

# Leave Request Management
@admin_api_bp.route('/leave/requests', methods=['GET'])
@require_admin
def get_leave_requests():
    status = request.args.get('status', 'pending')
    requests = LeaveRequest.query.filter_by(status=status).order_by(
        LeaveRequest.submitted_at.desc()
    ).all()
    
    result = []
    for req in requests:
        req_dict = req.to_dict()
        if req.user:
            req_dict['user_name'] = req.user.name
        result.append(req_dict)
    
    return jsonify({'requests': result})

@admin_api_bp.route('/leave/requests/<int:request_id>/approve', methods=['POST'])
@require_admin
def approve_leave_request(request_id):
    leave_req = LeaveRequest.query.get(request_id)
    if not leave_req:
        return jsonify({'error': 'Request not found'}), 404
    
    if leave_req.status != 'pending':
        return jsonify({'error': 'Request already processed'}), 400
    
    identity = get_jwt_identity()
    leave_req.status = 'approved'
    leave_req.processed_at = datetime.utcnow()
    leave_req.processed_by = identity.get('email')
    
    db.session.commit()
    
    log = SystemLog(
        action='approve_leave',
        user_type=identity.get('type'),
        user_id=identity.get('id'),
        user_email=identity.get('email'),
        details=f'Approved leave request for user {leave_req.user_id}',
        ip_address=request.remote_addr
    )
    db.session.add(log)
    db.session.commit()
    
    return jsonify({'message': 'Leave request approved'})

@admin_api_bp.route('/leave/requests/<int:request_id>/reject', methods=['POST'])
@require_admin
def reject_leave_request(request_id):
    leave_req = LeaveRequest.query.get(request_id)
    if not leave_req:
        return jsonify({'error': 'Request not found'}), 404
    
    if leave_req.status != 'pending':
        return jsonify({'error': 'Request already processed'}), 400
    
    data = request.get_json()
    reason = data.get('reason', 'Not specified')
    
    identity = get_jwt_identity()
    leave_req.status = 'rejected'
    leave_req.processed_at = datetime.utcnow()
    leave_req.processed_by = identity.get('email')
    leave_req.rejection_reason = reason
    
    db.session.commit()
    
    log = SystemLog(
        action='reject_leave',
        user_type=identity.get('type'),
        user_id=identity.get('id'),
        user_email=identity.get('email'),
        details=f'Rejected leave request for user {leave_req.user_id}: {reason}',
        ip_address=request.remote_addr
    )
    db.session.add(log)
    db.session.commit()
    
    return jsonify({'message': 'Leave request rejected'})
