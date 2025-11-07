"""
Production-grade Camera Management System
Supports multiple cameras (USB devices and IP/RTSP streams)
"""
import cv2
import threading
import time
import numpy as np
from datetime import datetime
from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class CameraStream:
    """Individual camera stream handler"""
    
    def __init__(self, camera_id: int, source, config: dict):
        self.camera_id = camera_id
        self.source = source  # int for device index, str for URL
        self.config = config
        
        # Stream properties
        self.capture = None
        self.frame = None
        self.is_running = False
        self.last_frame_time = None
        self.error_count = 0
        self.max_errors = 10
        
        # Health metrics
        self.total_frames = 0
        self.fps = 0
        self.last_health_check = datetime.utcnow()
        
        # Threading
        self.lock = threading.Lock()
        self.thread = None
        
        logger.info(f"Camera {camera_id} initialized with source: {source}")
    
    def start(self) -> bool:
        """Start camera stream"""
        if self.is_running:
            logger.warning(f"Camera {self.camera_id} already running")
            return True
        
        try:
            # Open capture
            if isinstance(self.source, int):
                self.capture = cv2.VideoCapture(self.source, cv2.CAP_DSHOW)  # DirectShow for Windows
            else:
                self.capture = cv2.VideoCapture(self.source)
            
            if not self.capture.isOpened():
                logger.error(f"Failed to open camera {self.camera_id}")
                return False
            
            # Set properties
            self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.get('width', 1280))
            self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.get('height', 720))
            self.capture.set(cv2.CAP_PROP_FPS, self.config.get('fps', 30))
            
            # Set buffer size for IP cameras
            if isinstance(self.source, str):
                self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            self.is_running = True
            self.error_count = 0
            
            # Start capture thread
            self.thread = threading.Thread(target=self._capture_loop, daemon=True)
            self.thread.start()
            
            logger.info(f"Camera {self.camera_id} started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error starting camera {self.camera_id}: {e}")
            return False
    
    def _capture_loop(self):
        """Continuous frame capture loop"""
        frame_interval = 1.0 / self.config.get('fps', 30)
        
        while self.is_running:
            try:
                ret, frame = self.capture.read()
                
                if ret:
                    with self.lock:
                        self.frame = frame
                        self.last_frame_time = datetime.utcnow()
                        self.total_frames += 1
                        self.error_count = 0
                    
                    # Calculate FPS
                    if self.total_frames % 30 == 0:
                        self._update_fps()
                    
                else:
                    self.error_count += 1
                    logger.warning(f"Camera {self.camera_id} read failed (error {self.error_count}/{self.max_errors})")
                    
                    if self.error_count >= self.max_errors:
                        logger.error(f"Camera {self.camera_id} max errors reached, attempting restart")
                        self._restart()
                
                time.sleep(frame_interval)
                
            except Exception as e:
                logger.error(f"Error in capture loop for camera {self.camera_id}: {e}")
                self.error_count += 1
                time.sleep(1)
    
    def _restart(self):
        """Restart camera stream"""
        logger.info(f"Restarting camera {self.camera_id}")
        self.stop()
        time.sleep(2)
        self.start()
    
    def _update_fps(self):
        """Update FPS calculation"""
        now = datetime.utcnow()
        if self.last_health_check:
            delta = (now - self.last_health_check).total_seconds()
            if delta > 0:
                self.fps = 30 / delta
        self.last_health_check = now
    
    def get_frame(self) -> Optional[np.ndarray]:
        """Get latest frame"""
        with self.lock:
            return self.frame.copy() if self.frame is not None else None
    
    def get_jpeg_frame(self) -> Optional[bytes]:
        """Get frame as JPEG bytes for streaming"""
        frame = self.get_frame()
        if frame is None:
            return None
        
        try:
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            return buffer.tobytes()
        except Exception as e:
            logger.error(f"Error encoding frame for camera {self.camera_id}: {e}")
            return None
    
    def get_health_status(self) -> dict:
        """Get camera health metrics"""
        with self.lock:
            age = (datetime.utcnow() - self.last_frame_time).total_seconds() if self.last_frame_time else None
            
            return {
                'camera_id': self.camera_id,
                'is_running': self.is_running,
                'total_frames': self.total_frames,
                'fps': round(self.fps, 2),
                'error_count': self.error_count,
                'last_frame_age': round(age, 2) if age else None,
                'status': 'healthy' if self.is_running and age and age < 5 else 'unhealthy'
            }
    
    def apply_quality_checks(self, frame: np.ndarray) -> dict:
        """Analyze frame quality for enrollment"""
        try:
            # Blur detection using Laplacian variance
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            blur_score = min(100, int(laplacian_var / 10))
            
            # Brightness check
            brightness = np.mean(gray)
            brightness_score = 100 if 50 < brightness < 200 else int((brightness / 255) * 100)
            
            # Overall quality
            overall_quality = (blur_score + brightness_score) / 2
            
            return {
                'blur_score': blur_score,
                'brightness_score': brightness_score,
                'overall_quality': int(overall_quality),
                'is_acceptable': overall_quality > 60
            }
        except Exception as e:
            logger.error(f"Error in quality check: {e}")
            return {
                'blur_score': 0,
                'brightness_score': 0,
                'overall_quality': 0,
                'is_acceptable': False
            }
    
    def stop(self):
        """Stop camera stream"""
        logger.info(f"Stopping camera {self.camera_id}")
        self.is_running = False
        
        if self.thread:
            self.thread.join(timeout=3)
        
        if self.capture:
            self.capture.release()
            self.capture = None
        
        with self.lock:
            self.frame = None


class CameraManager:
    """Centralized manager for all cameras"""
    
    def __init__(self):
        self.cameras: Dict[int, CameraStream] = {}
        self.lock = threading.Lock()
        self.next_id = 1
        
        logger.info("CameraManager initialized")
    
    def add_camera(self, source, config: dict = None) -> int:
        """
        Add a new camera
        Args:
            source: int for device index (e.g., 0, 1) or str for URL (RTSP/HTTP)
            config: Camera configuration dict
        Returns:
            camera_id: Unique identifier for the camera
        """
        with self.lock:
            camera_id = self.next_id
            self.next_id += 1
            
            default_config = {
                'width': 1280,
                'height': 720,
                'fps': 30,
                'name': f'Camera {camera_id}',
                'enabled': True
            }
            
            if config:
                default_config.update(config)
            
            camera = CameraStream(camera_id, source, default_config)
            self.cameras[camera_id] = camera
            
            logger.info(f"Camera {camera_id} added: {source}")
            return camera_id
    
    def start_camera(self, camera_id: int) -> bool:
        """Start specific camera"""
        with self.lock:
            camera = self.cameras.get(camera_id)
            if not camera:
                logger.error(f"Camera {camera_id} not found")
                return False
            
            return camera.start()
    
    def stop_camera(self, camera_id: int):
        """Stop specific camera"""
        with self.lock:
            camera = self.cameras.get(camera_id)
            if camera:
                camera.stop()
    
    def remove_camera(self, camera_id: int):
        """Remove camera"""
        self.stop_camera(camera_id)
        with self.lock:
            if camera_id in self.cameras:
                del self.cameras[camera_id]
                logger.info(f"Camera {camera_id} removed")
    
    def get_frame(self, camera_id: int) -> Optional[np.ndarray]:
        """Get frame from specific camera"""
        with self.lock:
            camera = self.cameras.get(camera_id)
            if camera:
                return camera.get_frame()
        return None
    
    def get_jpeg_frame(self, camera_id: int) -> Optional[bytes]:
        """Get JPEG frame for streaming"""
        with self.lock:
            camera = self.cameras.get(camera_id)
            if camera:
                return camera.get_jpeg_frame()
        return None
    
    def get_all_cameras(self) -> list:
        """Get list of all cameras with status"""
        with self.lock:
            return [
                {
                    'id': cam_id,
                    'source': cam.source,
                    'config': cam.config,
                    **cam.get_health_status()
                }
                for cam_id, cam in self.cameras.items()
            ]
    
    def get_camera_health(self, camera_id: int) -> Optional[dict]:
        """Get health status for specific camera"""
        with self.lock:
            camera = self.cameras.get(camera_id)
            if camera:
                return camera.get_health_status()
        return None
    
    def start_all(self):
        """Start all cameras"""
        with self.lock:
            for camera in self.cameras.values():
                if camera.config.get('enabled', True):
                    camera.start()
    
    def stop_all(self):
        """Stop all cameras"""
        with self.lock:
            for camera in self.cameras.values():
                camera.stop()
    
    def analyze_frame_quality(self, camera_id: int) -> Optional[dict]:
        """Analyze quality of current frame"""
        frame = self.get_frame(camera_id)
        if frame is None:
            return None
        
        with self.lock:
            camera = self.cameras.get(camera_id)
            if camera:
                return camera.apply_quality_checks(frame)
        return None


# Global camera manager instance
camera_manager = CameraManager()
