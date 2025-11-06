/**
 * Camera utility functions for mobile and desktop
 * Handles permissions, device selection, and error handling
 */

class CameraManager {
    constructor() {
        this.stream = null;
        this.videoElement = null;
        this.facingMode = 'user'; // 'user' for front camera, 'environment' for back
        this.constraints = null;
    }

    /**
     * Check if camera API is available
     */
    isCameraAvailable() {
        return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
    }

    /**
     * Check if device is mobile
     */
    isMobileDevice() {
        return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    }

    /**
     * Request camera permission with detailed error handling
     */
    async requestCameraPermission() {
        if (!this.isCameraAvailable()) {
            throw new Error('Camera API not supported in this browser');
        }

        try {
            // First, check if we already have permission
            if (navigator.permissions && navigator.permissions.query) {
                const permissionStatus = await navigator.permissions.query({ name: 'camera' });
                console.log('Camera permission status:', permissionStatus.state);
                
                if (permissionStatus.state === 'denied') {
                    throw new Error('Camera permission denied. Please enable camera access in your browser settings.');
                }
            }

            return true;
        } catch (error) {
            console.warn('Permission query not supported:', error);
            return true; // Continue anyway as not all browsers support permission query
        }
    }

    /**
     * Get optimal camera constraints based on device
     */
    getConstraints(useFrontCamera = true) {
        const isMobile = this.isMobileDevice();
        
        // Base constraints
        const constraints = {
            video: {
                facingMode: useFrontCamera ? 'user' : 'environment'
            },
            audio: false
        };

        // Add resolution constraints
        if (isMobile) {
            // Mobile devices - optimize for performance
            constraints.video.width = { ideal: 1280, max: 1920 };
            constraints.video.height = { ideal: 720, max: 1080 };
        } else {
            // Desktop - higher quality
            constraints.video.width = { ideal: 1920 };
            constraints.video.height = { ideal: 1080 };
        }

        // Add frame rate
        constraints.video.frameRate = { ideal: 30, max: 30 };

        this.constraints = constraints;
        return constraints;
    }

    /**
     * Start camera with permission handling
     */
    async startCamera(videoElement, useFrontCamera = true) {
        this.videoElement = videoElement;
        
        try {
            // Request permission first
            await this.requestCameraPermission();

            // Get constraints
            const constraints = this.getConstraints(useFrontCamera);
            console.log('Requesting camera with constraints:', constraints);

            // Try to get media stream
            try {
                this.stream = await navigator.mediaDevices.getUserMedia(constraints);
            } catch (err) {
                // If exact constraints fail, try with simplified constraints
                console.warn('Failed with specific constraints, trying fallback:', err);
                
                const fallbackConstraints = {
                    video: {
                        facingMode: useFrontCamera ? 'user' : 'environment'
                    },
                    audio: false
                };
                
                this.stream = await navigator.mediaDevices.getUserMedia(fallbackConstraints);
            }

            // Attach stream to video element
            videoElement.srcObject = this.stream;
            
            // Wait for video to be ready
            await new Promise((resolve, reject) => {
                videoElement.onloadedmetadata = () => {
                    videoElement.play()
                        .then(resolve)
                        .catch(reject);
                };
                
                // Timeout after 10 seconds
                setTimeout(() => reject(new Error('Video load timeout')), 10000);
            });

            console.log('Camera started successfully');
            return this.stream;

        } catch (error) {
            console.error('Camera error:', error);
            this.handleCameraError(error);
            throw error;
        }
    }

    /**
     * Handle camera errors with user-friendly messages
     */
    handleCameraError(error) {
        let message = 'Failed to access camera. ';

        if (error.name === 'NotAllowedError' || error.name === 'PermissionDeniedError') {
            message += 'Please allow camera access in your browser settings.';
            
            // Provide platform-specific instructions
            if (this.isMobileDevice()) {
                if (/iPhone|iPad|iPod/i.test(navigator.userAgent)) {
                    message += '\n\niOS: Go to Settings → Safari → Camera → Allow';
                } else if (/Android/i.test(navigator.userAgent)) {
                    message += '\n\nAndroid: Go to Settings → Apps → Browser → Permissions → Camera → Allow';
                }
            }
        } else if (error.name === 'NotFoundError' || error.name === 'DevicesNotFoundError') {
            message += 'No camera device found on this device.';
        } else if (error.name === 'NotReadableError' || error.name === 'TrackStartError') {
            message += 'Camera is already in use by another application.';
        } else if (error.name === 'OverconstrainedError') {
            message += 'Camera does not support the requested settings.';
        } else if (error.name === 'TypeError') {
            message += 'Camera API is not supported in this browser.';
        } else {
            message += error.message || 'Unknown error occurred.';
        }

        console.error('Camera Error Details:', {
            name: error.name,
            message: error.message,
            constraint: error.constraint
        });

        // Show to user
        if (typeof showToast !== 'undefined') {
            showToast(message, 'error');
        } else {
            alert(message);
        }
    }

    /**
     * Switch between front and back camera (mobile)
     */
    async switchCamera() {
        if (!this.isMobileDevice()) {
            console.warn('Camera switching is primarily for mobile devices');
            return;
        }

        const useFrontCamera = this.facingMode === 'environment';
        this.facingMode = useFrontCamera ? 'user' : 'environment';

        // Stop current stream
        this.stopCamera();

        // Start with new facing mode
        if (this.videoElement) {
            await this.startCamera(this.videoElement, useFrontCamera);
        }
    }

    /**
     * Stop camera and release resources
     */
    stopCamera() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => {
                track.stop();
                console.log('Camera track stopped:', track.label);
            });
            this.stream = null;
        }

        if (this.videoElement) {
            this.videoElement.srcObject = null;
        }
    }

    /**
     * Get available camera devices
     */
    async getAvailableCameras() {
        try {
            const devices = await navigator.mediaDevices.enumerateDevices();
            const cameras = devices.filter(device => device.kind === 'videoinput');
            
            console.log('Available cameras:', cameras.length);
            return cameras;
        } catch (error) {
            console.error('Failed to enumerate devices:', error);
            return [];
        }
    }

    /**
     * Capture photo from video stream
     */
    capturePhoto(videoElement, canvasElement) {
        if (!this.stream) {
            throw new Error('Camera not started');
        }

        const canvas = canvasElement;
        const video = videoElement;

        // Set canvas size to match video
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;

        // Draw video frame to canvas
        const ctx = canvas.getContext('2d');
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

        // Get image data
        return canvas.toDataURL('image/jpeg', 0.92);
    }

    /**
     * Check camera permissions status
     */
    async checkPermissionStatus() {
        if (!navigator.permissions || !navigator.permissions.query) {
            return 'unknown';
        }

        try {
            const result = await navigator.permissions.query({ name: 'camera' });
            return result.state; // 'granted', 'denied', or 'prompt'
        } catch (error) {
            console.warn('Permission query failed:', error);
            return 'unknown';
        }
    }
}

// Create global instance
const cameraManager = new CameraManager();

// Export for use in modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { CameraManager, cameraManager };
}
