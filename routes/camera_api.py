"""
Camera Management API Routes
RBAC-protected endpoints for camera operations
"""
from flask import Blueprint, request, jsonify, Response
from flask_jwt_extended import jwt_required, get_jwt_identity
from camera_manager import camera_manager
from models import db, SystemLog
import logging

logger = logging.getLogger(__name__)

camera_api_bp = Blueprint('camera_api', __name__)

def require_superadmin(fn):
    """Decorator to require superadmin access"""
    @jwt_required()
    def wrapper(*args, **kwargs):
        identity = get_jwt_identity()
        if identity.get('type') != 'superadmin':
            return jsonify({'error': 'Super admin access required'}), 403
        return fn(*args, **kwargs)
    wrapper.__name__ = fn.__name__
    return wrapper

def log_camera_activity(action, camera_id, details, identity):
    """Log camera-related activities"""
    try:
        log = SystemLog(
            action=action,
            user_type=identity.get('type'),
            user_id=identity.get('id'),
            user_email=identity.get('email'),
            details=f"Camera {camera_id}: {details}",
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        logger.error(f"Error logging activity: {e}")

@camera_api_bp.route('/cameras', methods=['GET'])
@require_superadmin
def get_cameras():
    """Get all cameras with status"""
    try:
        cameras = camera_manager.get_all_cameras()
        return jsonify({
            'cameras': cameras,
            'total': len(cameras)
        })
    except Exception as e:
        logger.error(f"Error getting cameras: {e}")
        return jsonify({'error': str(e)}), 500

@camera_api_bp.route('/cameras', methods=['POST'])
@require_superadmin
def add_camera():
    """
    Add a new camera
    Body:
        source: int (device index) or str (URL)
        config: dict with width, height, fps, name, etc.
    """
    try:
        identity = get_jwt_identity()
        data = request.get_json()
        
        source = data.get('source')
        if source is None:
            return jsonify({'error': 'Source is required'}), 400
        
        # Convert to int if it's a numeric device index
        if isinstance(source, str) and source.isdigit():
            source = int(source)
        
        config = data.get('config', {})
        
        camera_id = camera_manager.add_camera(source, config)
        
        # Log activity
        log_camera_activity('add_camera', camera_id, f'Added camera from source: {source}', identity)
        
        return jsonify({
            'message': 'Camera added successfully',
            'camera_id': camera_id
        }), 201
    
    except Exception as e:
        logger.error(f"Error adding camera: {e}")
        return jsonify({'error': str(e)}), 500

@camera_api_bp.route('/cameras/<int:camera_id>/start', methods=['POST'])
@require_superadmin
def start_camera(camera_id):
    """Start a specific camera"""
    try:
        identity = get_jwt_identity()
        
        success = camera_manager.start_camera(camera_id)
        
        if success:
            log_camera_activity('start_camera', camera_id, 'Started camera', identity)
            return jsonify({'message': 'Camera started successfully'})
        else:
            return jsonify({'error': 'Failed to start camera'}), 500
    
    except Exception as e:
        logger.error(f"Error starting camera: {e}")
        return jsonify({'error': str(e)}), 500

@camera_api_bp.route('/cameras/<int:camera_id>/stop', methods=['POST'])
@require_superadmin
def stop_camera(camera_id):
    """Stop a specific camera"""
    try:
        identity = get_jwt_identity()
        
        camera_manager.stop_camera(camera_id)
        log_camera_activity('stop_camera', camera_id, 'Stopped camera', identity)
        
        return jsonify({'message': 'Camera stopped successfully'})
    
    except Exception as e:
        logger.error(f"Error stopping camera: {e}")
        return jsonify({'error': str(e)}), 500

@camera_api_bp.route('/cameras/<int:camera_id>', methods=['DELETE'])
@require_superadmin
def remove_camera(camera_id):
    """Remove a camera"""
    try:
        identity = get_jwt_identity()
        
        camera_manager.remove_camera(camera_id)
        log_camera_activity('remove_camera', camera_id, 'Removed camera', identity)
        
        return jsonify({'message': 'Camera removed successfully'})
    
    except Exception as e:
        logger.error(f"Error removing camera: {e}")
        return jsonify({'error': str(e)}), 500

@camera_api_bp.route('/cameras/<int:camera_id>/health', methods=['GET'])
@require_superadmin
def get_camera_health(camera_id):
    """Get health status of a camera"""
    try:
        health = camera_manager.get_camera_health(camera_id)
        
        if health:
            return jsonify(health)
        else:
            return jsonify({'error': 'Camera not found'}), 404
    
    except Exception as e:
        logger.error(f"Error getting camera health: {e}")
        return jsonify({'error': str(e)}), 500

@camera_api_bp.route('/cameras/<int:camera_id>/quality', methods=['GET'])
@jwt_required()
def get_frame_quality(camera_id):
    """Analyze current frame quality"""
    try:
        quality = camera_manager.analyze_frame_quality(camera_id)
        
        if quality:
            return jsonify(quality)
        else:
            return jsonify({'error': 'No frame available'}), 404
    
    except Exception as e:
        logger.error(f"Error analyzing frame quality: {e}")
        return jsonify({'error': str(e)}), 500

@camera_api_bp.route('/cameras/<int:camera_id>/stream')
@jwt_required()
def stream_camera(camera_id):
    """
    Stream camera feed as MJPEG
    This endpoint streams live video from the camera
    """
    def generate_frames():
        """Generator function for video streaming"""
        try:
            while True:
                jpeg_frame = camera_manager.get_jpeg_frame(camera_id)
                
                if jpeg_frame:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + jpeg_frame + b'\r\n')
                else:
                    # No frame available, send placeholder or wait
                    import time
                    time.sleep(0.1)
        
        except GeneratorExit:
            logger.info(f"Stream for camera {camera_id} closed")
    
    return Response(
        generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

@camera_api_bp.route('/cameras/<int:camera_id>/snapshot', methods=['GET'])
@jwt_required()
def get_snapshot(camera_id):
    """Get a single frame as JPEG"""
    try:
        jpeg_frame = camera_manager.get_jpeg_frame(camera_id)
        
        if jpeg_frame:
            return Response(jpeg_frame, mimetype='image/jpeg')
        else:
            return jsonify({'error': 'No frame available'}), 404
    
    except Exception as e:
        logger.error(f"Error getting snapshot: {e}")
        return jsonify({'error': str(e)}), 500

@camera_api_bp.route('/cameras/<int:camera_id>/config', methods=['PUT'])
@require_superadmin
def update_camera_config(camera_id):
    """Update camera configuration"""
    try:
        identity = get_jwt_identity()
        data = request.get_json()
        
        # Get current camera
        cameras = camera_manager.get_all_cameras()
        camera = next((c for c in cameras if c['id'] == camera_id), None)
        
        if not camera:
            return jsonify({'error': 'Camera not found'}), 404
        
        # Update config
        camera['config'].update(data.get('config', {}))
        
        # Restart camera to apply changes
        camera_manager.stop_camera(camera_id)
        camera_manager.start_camera(camera_id)
        
        log_camera_activity('update_camera_config', camera_id, f'Updated configuration', identity)
        
        return jsonify({'message': 'Camera configuration updated'})
    
    except Exception as e:
        logger.error(f"Error updating camera config: {e}")
        return jsonify({'error': str(e)}), 500

@camera_api_bp.route('/cameras/available-devices', methods=['GET'])
@require_superadmin
def get_available_devices():
    """
    Detect available camera devices
    Scans indices 0-5 for connected cameras
    """
    try:
        import cv2
        available = []
        
        for i in range(6):
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            if cap.isOpened():
                available.append({
                    'index': i,
                    'name': f'Device {i}'
                })
                cap.release()
        
        return jsonify({
            'devices': available,
            'count': len(available)
        })
    
    except Exception as e:
        logger.error(f"Error detecting devices: {e}")
        return jsonify({'error': str(e)}), 500
