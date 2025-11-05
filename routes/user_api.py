from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from models import db, User, EnrollmentRequest, Attendance, Person
from face_service import face_service
import pickle

user_api_bp = Blueprint('user_api', __name__)

def require_user(fn):
    @jwt_required()
    def wrapper(*args, **kwargs):
        identity = get_jwt_identity()
        if identity.get('type') != 'user':
            return jsonify({'error': 'User access required'}), 403
        return fn(*args, **kwargs)
    wrapper.__name__ = fn.__name__
    return wrapper

@user_api_bp.route('/enrollment/submit', methods=['POST'])
@require_user
def submit_enrollment():
    identity = get_jwt_identity()
    user_id = identity.get('id')
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    existing_request = EnrollmentRequest.query.filter_by(
        user_id=user_id,
        status='pending'
    ).first()
    
    if existing_request:
        return jsonify({'error': 'You already have a pending enrollment request'}), 400
    
    if user.is_enrolled:
        return jsonify({'error': 'You are already enrolled'}), 400
    
    data = request.get_json()
    images = data.get('images', [])
    
    if len(images) < 3:
        return jsonify({'error': 'At least 3 photos required'}), 400
    
    enroll_request = EnrollmentRequest(
        user_id=user_id,
        name=user.name,
        email=user.email,
        phone=user.phone,
        images=images
    )
    
    db.session.add(enroll_request)
    db.session.commit()
    
    return jsonify({
        'message': 'Enrollment request submitted successfully',
        'request': enroll_request.to_dict()
    }), 201

@user_api_bp.route('/enrollment/status', methods=['GET'])
@require_user
def get_enrollment_status():
    identity = get_jwt_identity()
    user_id = identity.get('id')
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    latest_request = EnrollmentRequest.query.filter_by(
        user_id=user_id
    ).order_by(EnrollmentRequest.submitted_at.desc()).first()
    
    return jsonify({
        'is_enrolled': user.is_enrolled,
        'latest_request': latest_request.to_dict() if latest_request else None
    })

@user_api_bp.route('/attendance/mark', methods=['POST'])
@require_user
def mark_attendance():
    identity = get_jwt_identity()
    user_id = identity.get('id')
    
    user = User.query.get(user_id)
    if not user or not user.is_enrolled:
        return jsonify({'error': 'You must be enrolled first'}), 400
    
    data = request.get_json()
    image_data = data.get('image')
    
    if not image_data:
        return jsonify({'error': 'Image required'}), 400
    
    try:
        image = face_service.base64_to_image(image_data)
        embedding = face_service.extract_embedding(image)
        
        if embedding is None:
            return jsonify({'error': 'No face detected'}), 400
        
        person_id, confidence = face_service.recognize_face(embedding)
        
        if person_id is None:
            return jsonify({'error': 'Face not recognized'}), 400
        
        person = Person.query.get(person_id)
        if not person or person.user_id != user_id:
            return jsonify({'error': 'Face does not match your profile'}), 400
        
        today = datetime.utcnow().date()
        existing_attendance = Attendance.query.filter_by(
            user_id=user_id
        ).filter(
            db.func.date(Attendance.timestamp) == today
        ).first()
        
        if existing_attendance:
            return jsonify({
                'message': 'Attendance already marked today',
                'attendance': existing_attendance.to_dict()
            })
        
        attendance = Attendance(
            person_id=person_id,
            user_id=user_id,
            name=user.name,
            confidence=confidence
        )
        
        db.session.add(attendance)
        db.session.commit()
        
        return jsonify({
            'message': 'Attendance marked successfully',
            'attendance': attendance.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@user_api_bp.route('/attendance/history', methods=['GET'])
@require_user
def get_attendance_history():
    identity = get_jwt_identity()
    user_id = identity.get('id')
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 30, type=int)
    
    attendance = Attendance.query.filter_by(user_id=user_id).order_by(
        Attendance.timestamp.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'attendance': [a.to_dict() for a in attendance.items],
        'total': attendance.total,
        'pages': attendance.pages,
        'current_page': page
    })

@user_api_bp.route('/stats', methods=['GET'])
@require_user
def get_user_stats():
    identity = get_jwt_identity()
    user_id = identity.get('id')
    
    total_attendance = Attendance.query.filter_by(user_id=user_id).count()
    
    today = datetime.utcnow().date()
    today_marked = Attendance.query.filter_by(user_id=user_id).filter(
        db.func.date(Attendance.timestamp) == today
    ).first() is not None
    
    return jsonify({
        'total_attendance': total_attendance,
        'today_marked': today_marked
    })
