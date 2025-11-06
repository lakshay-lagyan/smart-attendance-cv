from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from models import db, User, EnrollmentRequest, Attendance, Person, LeaveRequest, EmailVerification
from face_service import face_service
from email_service import email_service
import pickle
from datetime import timedelta

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

@user_api_bp.route('/verify-email', methods=['POST'])
@require_user
def verify_email():
    """Verify user email with verification code"""
    identity = get_jwt_identity()
    user_id = identity.get('id')
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    if user.email_verified:
        return jsonify({'error': 'Email already verified'}), 400
    
    data = request.get_json()
    code = data.get('code', '').strip()
    
    if not code:
        return jsonify({'error': 'Verification code required'}), 400
    
    # Find valid verification code
    verification = EmailVerification.query.filter_by(
        user_id=user_id,
        verification_code=code,
        is_used=False
    ).filter(
        EmailVerification.expires_at > datetime.utcnow()
    ).first()
    
    if not verification:
        return jsonify({'error': 'Invalid or expired verification code'}), 400
    
    # Mark as verified
    user.email_verified = True
    user.verified_at = datetime.utcnow()
    verification.is_used = True
    
    db.session.commit()
    
    return jsonify({
        'message': 'Email verified successfully',
        'user': user.to_dict()
    })

@user_api_bp.route('/resend-verification', methods=['POST'])
@require_user
def resend_verification():
    """Resend verification code to user email"""
    identity = get_jwt_identity()
    user_id = identity.get('id')
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    if user.email_verified:
        return jsonify({'error': 'Email already verified'}), 400
    
    # Invalidate old codes
    EmailVerification.query.filter_by(
        user_id=user_id,
        is_used=False
    ).update({'is_used': True})
    
    # Generate new code
    verification_code = email_service.generate_verification_code()
    
    verification = EmailVerification(
        user_id=user.id,
        email=user.email,
        verification_code=verification_code,
        expires_at=datetime.utcnow() + timedelta(hours=24)
    )
    db.session.add(verification)
    db.session.commit()
    
    # Send email
    email_sent = email_service.send_verification_code(
        user.email,
        verification_code,
        user.name
    )
    
    response_data = {'message': 'Verification code sent to your email'}
    
    if not email_service.enabled:
        response_data['verification_code'] = verification_code
        response_data['note'] = 'Email service disabled. Use this code to verify.'
    
    return jsonify(response_data)

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
    
    from datetime import timedelta, time
    from sqlalchemy import func, and_, extract
    
    total_attendance = Attendance.query.filter_by(user_id=user_id).count()
    
    today = datetime.utcnow().date()
    today_marked = Attendance.query.filter_by(user_id=user_id).filter(
        db.func.date(Attendance.timestamp) == today
    ).first() is not None
    
    # Get today's attendance record
    today_record = Attendance.query.filter_by(user_id=user_id).filter(
        db.func.date(Attendance.timestamp) == today
    ).first()
    
    # Calculate late arrivals (after 9:00 AM)
    late_threshold = time(9, 0, 0)
    late_count = 0
    on_time_count = 0
    
    all_attendance = Attendance.query.filter_by(user_id=user_id).all()
    for att in all_attendance:
        if att.timestamp.time() > late_threshold:
            late_count += 1
        else:
            on_time_count += 1
    
    # Count leaves
    approved_leaves = LeaveRequest.query.filter_by(
        user_id=user_id, 
        status='approved'
    ).count()
    
    pending_leaves = LeaveRequest.query.filter_by(
        user_id=user_id, 
        status='pending'
    ).count()
    
    # Calculate absence frequency (days without attendance in last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    attendance_dates = set([
        att.timestamp.date() 
        for att in Attendance.query.filter(
            and_(
                Attendance.user_id == user_id,
                Attendance.timestamp >= thirty_days_ago
            )
        ).all()
    ])
    
    # Get working days (excluding weekends)
    working_days = 0
    current_date = thirty_days_ago.date()
    while current_date <= today:
        if current_date.weekday() < 5:  # Monday to Friday
            working_days += 1
        current_date += timedelta(days=1)
    
    absence_days = working_days - len(attendance_dates)
    
    # Get monthly attendance
    monthly_attendance = db.session.query(
        func.strftime('%Y-%m', Attendance.timestamp).label('month'),
        func.count(Attendance.id).label('count')
    ).filter(
        Attendance.user_id == user_id
    ).group_by(
        func.strftime('%Y-%m', Attendance.timestamp)
    ).order_by(
        func.strftime('%Y-%m', Attendance.timestamp).desc()
    ).limit(12).all()
    
    return jsonify({
        'total_attendance': total_attendance,
        'today_marked': today_marked,
        'today_time': today_record.timestamp.isoformat() if today_record else None,
        'late_count': late_count,
        'on_time_count': on_time_count,
        'late_percentage': round((late_count / total_attendance * 100) if total_attendance > 0 else 0, 2),
        'on_time_percentage': round((on_time_count / total_attendance * 100) if total_attendance > 0 else 0, 2),
        'approved_leaves': approved_leaves,
        'pending_leaves': pending_leaves,
        'absence_days': absence_days,
        'monthly_attendance': [
            {'month': month, 'count': count} 
            for month, count in monthly_attendance
        ]
    })

# Leave Request Management
@user_api_bp.route('/leave/submit', methods=['POST'])
@require_user
def submit_leave_request():
    identity = get_jwt_identity()
    user_id = identity.get('id')
    
    data = request.get_json()
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    leave_type = data.get('leave_type')
    reason = data.get('reason')
    
    if not all([start_date, end_date, leave_type, reason]):
        return jsonify({'error': 'All fields required'}), 400
    
    try:
        from datetime import datetime as dt
        start = dt.strptime(start_date, '%Y-%m-%d').date()
        end = dt.strptime(end_date, '%Y-%m-%d').date()
        
        if end < start:
            return jsonify({'error': 'End date must be after start date'}), 400
        
        leave_request = LeaveRequest(
            user_id=user_id,
            start_date=start,
            end_date=end,
            leave_type=leave_type,
            reason=reason
        )
        
        db.session.add(leave_request)
        db.session.commit()
        
        return jsonify({
            'message': 'Leave request submitted successfully',
            'request': leave_request.to_dict()
        }), 201
    
    except ValueError as e:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@user_api_bp.route('/leave/requests', methods=['GET'])
@require_user
def get_user_leave_requests():
    identity = get_jwt_identity()
    user_id = identity.get('id')
    
    status = request.args.get('status')
    
    query = LeaveRequest.query.filter_by(user_id=user_id)
    if status:
        query = query.filter_by(status=status)
    
    requests = query.order_by(LeaveRequest.submitted_at.desc()).all()
    
    return jsonify({
        'requests': [req.to_dict() for req in requests]
    })

@user_api_bp.route('/attendance/chart', methods=['GET'])
@require_user
def get_attendance_chart_data():
    identity = get_jwt_identity()
    user_id = identity.get('id')
    
    from datetime import timedelta
    from sqlalchemy import func
    
    days = request.args.get('days', 30, type=int)
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Daily attendance times
    daily_records = db.session.query(
        func.date(Attendance.timestamp).label('date'),
        func.min(Attendance.timestamp).label('time')
    ).filter(
        and_(
            Attendance.user_id == user_id,
            Attendance.timestamp >= start_date
        )
    ).group_by(
        func.date(Attendance.timestamp)
    ).all()
    
    daily_times = []
    for record in daily_records:
        time_obj = record.time
        # Extract hour and minute as decimal (e.g., 9:30 = 9.5)
        time_decimal = time_obj.hour + (time_obj.minute / 60.0)
        daily_times.append({
            'date': str(record.date),
            'time': time_obj.strftime('%H:%M:%S'),
            'hour': time_decimal
        })
    
    return jsonify({
        'daily_times': daily_times,
        'period_days': days
    })
