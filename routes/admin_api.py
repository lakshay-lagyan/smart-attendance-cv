from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from sqlalchemy import func
import pickle
import base64
from models import db, Admin, User, Person, Attendance, EnrollmentRequest, SystemLog
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
