"""
Enhanced Enrollment Request API with Duplicate Checking
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User, EnrollmentRequest, Person, SystemLog
from duplicate_checker import duplicate_checker
from background_worker import background_worker, generate_face_embedding_task
from face_service import face_service
import os
import logging
import base64
from datetime import datetime

logger = logging.getLogger(__name__)

enrollment_api_bp = Blueprint('enrollment_api', __name__)

def require_admin(fn):
    """Decorator to require admin or superadmin access"""
    @jwt_required()
    def wrapper(*args, **kwargs):
        identity = get_jwt_identity()
        if identity.get('type') not in ['admin', 'superadmin']:
            return jsonify({'error': 'Admin access required'}), 403
        return fn(*args, **kwargs)
    wrapper.__name__ = fn.__name__
    return wrapper

@enrollment_api_bp.route('/requests', methods=['POST'])
@jwt_required()
def submit_enrollment_request():
    """
    Submit enrollment request with face images
    Supports both file uploads and base64 encoded images
    """
    try:
        identity = get_jwt_identity()
        user_id = identity.get('id')
        
        data = request.get_json() if request.is_json else request.form.to_dict()
        
        name = data.get('name')
        email = data.get('email')
        phone = data.get('phone', '')
        images = data.get('images', [])  # List of base64 or file paths
        camera_id = data.get('camera_id')  # Optional camera used for capture
        
        if not all([name, email]):
            return jsonify({'error': 'Name and email are required'}), 400
        
        if not images or len(images) == 0:
            return jsonify({'error': 'At least one face image is required'}), 400
        
        # Save images and analyze quality
        saved_images = []
        quality_scores = []
        embeddings_for_check = []
        
        from config import Config
        upload_folder = Config.UPLOAD_FOLDER
        os.makedirs(upload_folder, exist_ok=True)
        
        for idx, img_data in enumerate(images):
            try:
                # Handle base64 encoded images
                if isinstance(img_data, str) and img_data.startswith('data:image'):
                    # Extract base64 data
                    header, encoded = img_data.split(',', 1)
                    img_bytes = base64.b64decode(encoded)
                    
                    # Save to file
                    filename = f"enrollment_{user_id}_{datetime.utcnow().timestamp()}_{idx}.jpg"
                    filepath = os.path.join(upload_folder, filename)
                    
                    with open(filepath, 'wb') as f:
                        f.write(img_bytes)
                    
                    saved_images.append(filepath)
                    
                    # Analyze quality
                    import cv2
                    import numpy as np
                    nparr = np.frombuffer(img_bytes, np.uint8)
                    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    
                    # Basic quality check
                    if img is not None:
                        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                        blur_score = int(cv2.Laplacian(gray, cv2.CV_64F).var() / 10)
                        brightness = int(np.mean(gray))
                        
                        quality = {
                            'image_index': idx,
                            'blur_score': min(100, blur_score),
                            'brightness': brightness,
                            'quality': 'good' if blur_score > 60 else 'poor',
                            'filename': filename
                        }
                        quality_scores.append(quality)
                        
                        # Generate embedding for duplicate check
                        embedding = face_service.get_face_embedding(img)
                        if embedding is not None:
                            embeddings_for_check.append(embedding)
                    else:
                        quality_scores.append({
                            'image_index': idx,
                            'error': 'Failed to decode image'
                        })
                
                elif isinstance(img_data, str):
                    # File path
                    saved_images.append(img_data)
                    quality_scores.append({'image_index': idx, 'filepath': img_data})
            
            except Exception as e:
                logger.error(f"Error processing image {idx}: {e}")
                quality_scores.append({'image_index': idx, 'error': str(e)})
        
        # Create enrollment request
        enrollment_request = EnrollmentRequest(
            user_id=user_id,
            name=name,
            email=email,
            phone=phone,
            images=saved_images,
            quality_scores=quality_scores
        )
        
        db.session.add(enrollment_request)
        db.session.commit()
        
        # Log activity
        log = SystemLog(
            action='enrollment_request_submitted',
            user_type=identity.get('type'),
            user_id=user_id,
            user_email=email,
            details=f"Enrollment request {enrollment_request.id} submitted with {len(saved_images)} images",
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()
        
        # Check for duplicates using best quality embedding
        duplicate_results = []
        if embeddings_for_check:
            best_embedding = embeddings_for_check[0]  # Use first good embedding
            duplicates = duplicate_checker.find_duplicates(best_embedding, k=5, threshold=0.6)
            duplicate_results = duplicates
        
        return jsonify({
            'message': 'Enrollment request submitted successfully',
            'request_id': enrollment_request.id,
            'images_processed': len(saved_images),
            'quality_scores': quality_scores,
            'potential_duplicates': duplicate_results,
            'status': 'pending'
        }), 201
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Enrollment request error: {e}")
        return jsonify({'error': str(e)}), 500

@enrollment_api_bp.route('/requests', methods=['GET'])
@require_admin
def get_enrollment_requests():
    """Get all enrollment requests with filters"""
    try:
        status = request.args.get('status', 'pending')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        
        query = EnrollmentRequest.query
        
        if status != 'all':
            query = query.filter_by(status=status)
        
        # Pagination
        pagination = query.order_by(EnrollmentRequest.submitted_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        requests = [{
            **req.to_dict(include_images=True),
            'image_count': len(req.images),
            'user_info': req.user.to_dict() if req.user else None
        } for req in pagination.items]
        
        return jsonify({
            'requests': requests,
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page
        })
    
    except Exception as e:
        logger.error(f"Error fetching enrollment requests: {e}")
        return jsonify({'error': str(e)}), 500

@enrollment_api_bp.route('/requests/<int:request_id>', methods=['GET'])
@require_admin
def get_enrollment_request_detail(request_id):
    """Get detailed enrollment request with duplicate check"""
    try:
        req = EnrollmentRequest.query.get(request_id)
        if not req:
            return jsonify({'error': 'Request not found'}), 404
        
        # Get duplicate check results
        duplicate_results = []
        if req.images and len(req.images) > 0:
            # Load first image and generate embedding
            import cv2
            img_path = req.images[0]
            if os.path.exists(img_path):
                img = cv2.imread(img_path)
                if img is not None:
                    embedding = face_service.get_face_embedding(img)
                    if embedding is not None:
                        duplicates = duplicate_checker.find_duplicates(embedding, k=5, threshold=0.6)
                        duplicate_results = duplicates
        
        return jsonify({
            **req.to_dict(include_images=True),
            'quality_scores': req.quality_scores,
            'potential_duplicates': duplicate_results,
            'duplicate_count': len(duplicate_results),
            'high_confidence_duplicates': len([d for d in duplicate_results if d.get('is_high_match', False)]),
            'user_info': req.user.to_dict() if req.user else None
        })
    
    except Exception as e:
        logger.error(f"Error fetching request detail: {e}")
        return jsonify({'error': str(e)}), 500

@enrollment_api_bp.route('/requests/<int:request_id>/approve', methods=['POST'])
@require_admin
def approve_enrollment_request(request_id):
    """Approve enrollment request and create Person record"""
    try:
        identity = get_jwt_identity()
        
        req = EnrollmentRequest.query.get(request_id)
        if not req:
            return jsonify({'error': 'Request not found'}), 404
        
        if req.status != 'pending':
            return jsonify({'error': f'Request already {req.status}'}), 400
        
        # Create Person record
        person = Person(
            name=req.name,
            email=req.email,
            phone=req.phone,
            user_id=req.user_id,
            status='active'
        )
        
        db.session.add(person)
        
        # Update request status
        req.status = 'approved'
        req.processed_at = datetime.utcnow()
        req.processed_by = identity.get('email')
        
        db.session.commit()
        
        # Generate embeddings in background
        for img_path in req.images:
            if os.path.exists(img_path):
                task_id = f"embed_person_{person.id}_{datetime.utcnow().timestamp()}"
                background_worker.submit_task(
                    task_id,
                    generate_face_embedding_task,
                    img_path,
                    face_service
                )
        
        # Log approval
        log = SystemLog(
            action='enrollment_request_approved',
            user_type=identity.get('type'),
            user_id=identity.get('id'),
            user_email=identity.get('email'),
            details=f"Approved enrollment request {request_id}, created Person {person.id}",
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify({
            'message': 'Enrollment request approved',
            'person_id': person.id,
            'embedding_tasks_queued': len(req.images)
        })
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error approving enrollment: {e}")
        return jsonify({'error': str(e)}), 500

@enrollment_api_bp.route('/requests/<int:request_id>/reject', methods=['POST'])
@require_admin
def reject_enrollment_request(request_id):
    """Reject enrollment request"""
    try:
        identity = get_jwt_identity()
        data = request.get_json()
        
        reason = data.get('reason')
        if not reason:
            return jsonify({'error': 'Rejection reason is required'}), 400
        
        req = EnrollmentRequest.query.get(request_id)
        if not req:
            return jsonify({'error': 'Request not found'}), 404
        
        if req.status != 'pending':
            return jsonify({'error': f'Request already {req.status}'}), 400
        
        req.status = 'rejected'
        req.rejection_reason = reason
        req.processed_at = datetime.utcnow()
        req.processed_by = identity.get('email')
        
        db.session.commit()
        
        # Log rejection
        log = SystemLog(
            action='enrollment_request_rejected',
            user_type=identity.get('type'),
            user_id=identity.get('id'),
            user_email=identity.get('email'),
            details=f"Rejected enrollment request {request_id}: {reason}",
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify({'message': 'Enrollment request rejected'})
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error rejecting enrollment: {e}")
        return jsonify({'error': str(e)}), 500
