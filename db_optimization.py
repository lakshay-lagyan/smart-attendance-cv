from app import app, db
from models import User, Person, SignupRequest, EnrollmentRequest, LeaveRequest, Attendance, SystemLog

def add_indexes():
    """Add database indexes for performance optimization"""
    with app.app_context():
        # Get database connection
        connection = db.engine.connect()
        
        try:
            print("Adding database indexes...")
            
            # User indexes
            connection.execute(db.text(
                "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)"
            ))
            connection.execute(db.text(
                "CREATE INDEX IF NOT EXISTS idx_users_status ON users(status)"
            ))
            connection.execute(db.text(
                "CREATE INDEX IF NOT EXISTS idx_users_department ON users(department)"
            ))
            
            # Person indexes
            connection.execute(db.text(
                "CREATE INDEX IF NOT EXISTS idx_persons_user_id ON persons(user_id)"
            ))
            connection.execute(db.text(
                "CREATE INDEX IF NOT EXISTS idx_persons_status ON persons(status)"
            ))
            
            # SignupRequest indexes
            connection.execute(db.text(
                "CREATE INDEX IF NOT EXISTS idx_signup_requests_status ON signup_requests(status)"
            ))
            connection.execute(db.text(
                "CREATE INDEX IF NOT EXISTS idx_signup_requests_email ON signup_requests(email)"
            ))
            connection.execute(db.text(
                "CREATE INDEX IF NOT EXISTS idx_signup_requests_submitted_at ON signup_requests(submitted_at)"
            ))
            
            # EnrollmentRequest indexes
            connection.execute(db.text(
                "CREATE INDEX IF NOT EXISTS idx_enrollment_requests_user_id ON enrollment_requests(user_id)"
            ))
            connection.execute(db.text(
                "CREATE INDEX IF NOT EXISTS idx_enrollment_requests_status ON enrollment_requests(status)"
            ))
            connection.execute(db.text(
                "CREATE INDEX IF NOT EXISTS idx_enrollment_requests_submitted_at ON enrollment_requests(submitted_at)"
            ))
            
            # LeaveRequest indexes
            connection.execute(db.text(
                "CREATE INDEX IF NOT EXISTS idx_leave_requests_user_id ON leave_requests(user_id)"
            ))
            connection.execute(db.text(
                "CREATE INDEX IF NOT EXISTS idx_leave_requests_status ON leave_requests(status)"
            ))
            connection.execute(db.text(
                "CREATE INDEX IF NOT EXISTS idx_leave_requests_start_date ON leave_requests(start_date)"
            ))
            
            # Attendance indexes  
            connection.execute(db.text(
                "CREATE INDEX IF NOT EXISTS idx_attendance_person_id ON attendance(person_id)"
            ))
            connection.execute(db.text(
                "CREATE INDEX IF NOT EXISTS idx_attendance_user_id ON attendance(user_id)"
            ))
            connection.execute(db.text(
                "CREATE INDEX IF NOT EXISTS idx_attendance_timestamp ON attendance(timestamp)"
            ))
            connection.execute(db.text(
                "CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance(DATE(timestamp))"
            ))
            
            # SystemLog indexes
            connection.execute(db.text(
                "CREATE INDEX IF NOT EXISTS idx_system_logs_user_type ON system_logs(user_type)"
            ))
            connection.execute(db.text(
                "CREATE INDEX IF NOT EXISTS idx_system_logs_action ON system_logs(action)"
            ))
            connection.execute(db.text(
                "CREATE INDEX IF NOT EXISTS idx_system_logs_timestamp ON system_logs(timestamp)"
            ))
            
            connection.commit()
            print("✓ Database indexes added successfully!")
            
        except Exception as e:
            print(f"Error adding indexes: {e}")
            connection.rollback()
        finally:
            connection.close()

if __name__ == '__main__':
    print("Database Optimization Script")
    print("=" * 50)
    add_indexes()
    print("=" * 50)
    print("Optimization complete!")
