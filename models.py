from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class SuperAdmin(db.Model):
    """Super Admin with full system control"""
    __tablename__ = 'super_admins'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    profile_image = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'profile_image': self.profile_image,
            'role': 'superadmin',
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }


class Admin(db.Model):
    """Admin user model"""
    __tablename__ = 'admins'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    profile_image = db.Column(db.Text, default='')
    department = db.Column(db.String(100), default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey('super_admins.id'))
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'profile_image': self.profile_image,
            'department': self.department,
            'role': 'admin',
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }


class User(db.Model):
    """Regular user model"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    department = db.Column(db.String(100), default='')
    phone = db.Column(db.String(20), default='')
    profile_image = db.Column(db.Text, default='')
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_enrolled = db.Column(db.Boolean, default=False)
    email_verified = db.Column(db.Boolean, default=False)
    verified_at = db.Column(db.DateTime, nullable=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'department': self.department,
            'phone': self.phone,
            'profile_image': self.profile_image,
            'status': self.status,
            'role': 'user',
            'is_enrolled': self.is_enrolled,
            'email_verified': self.email_verified,
            'verified_at': self.verified_at.isoformat() if self.verified_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }


class Person(db.Model):
    """Person with face embeddings"""
    __tablename__ = 'persons'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    embedding = db.Column(db.LargeBinary, nullable=False)
    embedding_dim = db.Column(db.Integer, nullable=False)
    photos_count = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default='active')
    enrollment_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='person_profile')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'user_id': self.user_id,
            'photos_count': self.photos_count,
            'status': self.status,
            'enrollment_date': self.enrollment_date.isoformat() if self.enrollment_date else None
        }


class EmailVerification(db.Model):
    """Email verification codes for user verification"""
    __tablename__ = 'email_verifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    email = db.Column(db.String(120), nullable=False, index=True)
    verification_code = db.Column(db.String(6), nullable=False)
    is_used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    
    user = db.relationship('User', backref='verification_codes')
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'email': self.email,
            'is_used': self.is_used,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None
        }


class SignupRequest(db.Model):
    """Signup request from new users requiring admin approval"""
    __tablename__ = 'signup_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(20), default='')
    department = db.Column(db.String(100), default='')
    profile_image = db.Column(db.Text, default='')
    documents = db.Column(db.JSON, default=[])  # Store uploaded documents/images
    status = db.Column(db.String(20), default='pending', index=True)  # pending, approved, rejected
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed_at = db.Column(db.DateTime, nullable=True)
    processed_by = db.Column(db.String(120), nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)
    requires_verification = db.Column(db.Boolean, default=False)
    verification_sent_at = db.Column(db.DateTime, nullable=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def to_dict(self, include_documents=False):
        data = {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'department': self.department,
            'profile_image': self.profile_image,
            'status': self.status,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
            'processed_by': self.processed_by,
            'rejection_reason': self.rejection_reason
        }
        if include_documents:
            data['documents'] = self.documents
        return data


class EnrollmentRequest(db.Model):
    """Enrollment request from users"""
    __tablename__ = 'enrollment_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False, index=True)
    phone = db.Column(db.String(20), default='')
    images = db.Column(db.JSON, nullable=False)
    quality_scores = db.Column(db.JSON, default=[])  # Quality scores for each image
    status = db.Column(db.String(20), default='pending', index=True)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed_at = db.Column(db.DateTime, nullable=True)
    processed_by = db.Column(db.String(120), nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)
    
    user = db.relationship('User', backref='enrollment_requests')
    
    def to_dict(self, include_images=False):
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'status': self.status,
            'quality_scores': self.quality_scores,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
            'processed_by': self.processed_by,
            'rejection_reason': self.rejection_reason
        }
        if include_images:
            data['images'] = self.images
        return data


class LeaveRequest(db.Model):
    """Leave request from users"""
    __tablename__ = 'leave_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False, index=True)
    end_date = db.Column(db.Date, nullable=False)
    leave_type = db.Column(db.String(50), nullable=False)  # sick, vacation, personal, etc.
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending', index=True)  # pending, approved, rejected
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed_at = db.Column(db.DateTime, nullable=True)
    processed_by = db.Column(db.String(120), nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)
    
    user = db.relationship('User', backref='leave_requests')
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'leave_type': self.leave_type,
            'reason': self.reason,
            'status': self.status,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
            'processed_by': self.processed_by,
            'rejection_reason': self.rejection_reason
        }


class Attendance(db.Model):
    """Attendance records"""
    __tablename__ = 'attendance'
    
    id = db.Column(db.Integer, primary_key=True)
    person_id = db.Column(db.Integer, db.ForeignKey('persons.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    confidence = db.Column(db.Float, default=0.0)
    image_data = db.Column(db.Text, nullable=True)
    
    person = db.relationship('Person', backref='attendance_records')
    user = db.relationship('User', backref='attendance_records')
    
    def to_dict(self):
        return {
            'id': self.id,
            'person_id': self.person_id,
            'user_id': self.user_id,
            'name': self.name,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'confidence': round(self.confidence, 3)
        }


class SystemLog(db.Model):
    """System activity logs for super admin"""
    __tablename__ = 'system_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(100), nullable=False)
    user_type = db.Column(db.String(20), nullable=False)  # superadmin, admin, user
    user_id = db.Column(db.Integer, nullable=False)
    user_email = db.Column(db.String(120), nullable=False)
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(50))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'action': self.action,
            'user_type': self.user_type,
            'user_id': self.user_id,
            'user_email': self.user_email,
            'details': self.details,
            'ip_address': self.ip_address,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }


# Create indexes for better performance
db.Index('idx_attendance_timestamp', Attendance.timestamp.desc())
db.Index('idx_attendance_name_timestamp', Attendance.name, Attendance.timestamp.desc())
db.Index('idx_persons_status', Person.status)
db.Index('idx_users_status', User.status)
db.Index('idx_enrollment_status', EnrollmentRequest.status)
db.Index('idx_signup_status', SignupRequest.status)
db.Index('idx_leave_status', LeaveRequest.status)
db.Index('idx_leave_dates', LeaveRequest.start_date, LeaveRequest.end_date)
db.Index('idx_system_logs_timestamp', SystemLog.timestamp.desc())
