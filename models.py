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


class EnrollmentRequest(db.Model):
    """Enrollment request from users"""
    __tablename__ = 'enrollment_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False, index=True)
    phone = db.Column(db.String(20), default='')
    images = db.Column(db.JSON, nullable=False)
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
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
            'processed_by': self.processed_by,
            'rejection_reason': self.rejection_reason
        }
        if include_images:
            data['images'] = self.images
        return data


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
db.Index('idx_system_logs_timestamp', SystemLog.timestamp.desc())
