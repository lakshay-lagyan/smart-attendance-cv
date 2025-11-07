"""
Database Migration Script
Adds missing columns to existing tables
"""
import logging
from app import app, db
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_database():
    """Add missing columns to database tables"""
    with app.app_context():
        try:
            # Check and add missing columns to users table
            logger.info("Checking users table...")
            
            # Add email_verified column if it doesn't exist
            try:
                db.session.execute(text("""
                    ALTER TABLE users ADD COLUMN email_verified BOOLEAN DEFAULT FALSE
                """))
                db.session.commit()
                logger.info("✅ Added email_verified column to users table")
            except Exception as e:
                if "already exists" in str(e) or "duplicate column" in str(e).lower():
                    logger.info("⏭️  email_verified column already exists")
                    db.session.rollback()
                else:
                    raise
            
            # Add verified_at column if it doesn't exist
            try:
                db.session.execute(text("""
                    ALTER TABLE users ADD COLUMN verified_at DATETIME
                """))
                db.session.commit()
                logger.info("✅ Added verified_at column to users table")
            except Exception as e:
                if "already exists" in str(e) or "duplicate column" in str(e).lower():
                    logger.info("⏭️  verified_at column already exists")
                    db.session.rollback()
                else:
                    raise
            
            # Check and add missing columns to signup_requests table
            logger.info("Checking signup_requests table...")
            
            # Add documents column if it doesn't exist (for JSON data)
            try:
                db.session.execute(text("""
                    ALTER TABLE signup_requests ADD COLUMN documents TEXT
                """))
                db.session.commit()
                logger.info("✅ Added documents column to signup_requests table")
            except Exception as e:
                if "already exists" in str(e) or "duplicate column" in str(e).lower():
                    logger.info("⏭️  documents column already exists")
                    db.session.rollback()
                else:
                    raise
            
            # Add processed_by column if it doesn't exist
            try:
                db.session.execute(text("""
                    ALTER TABLE signup_requests ADD COLUMN processed_by VARCHAR(255)
                """))
                db.session.commit()
                logger.info("✅ Added processed_by column to signup_requests table")
            except Exception as e:
                if "already exists" in str(e) or "duplicate column" in str(e).lower():
                    logger.info("⏭️  processed_by column already exists")
                    db.session.rollback()
                else:
                    raise
            
            # Add processed_at column if it doesn't exist
            try:
                db.session.execute(text("""
                    ALTER TABLE signup_requests ADD COLUMN processed_at DATETIME
                """))
                db.session.commit()
                logger.info("✅ Added processed_at column to signup_requests table")
            except Exception as e:
                if "already exists" in str(e) or "duplicate column" in str(e).lower():
                    logger.info("⏭️  processed_at column already exists")
                    db.session.rollback()
                else:
                    raise
            
            # Check and add rejection_reason column if it doesn't exist
            try:
                db.session.execute(text("""
                    ALTER TABLE signup_requests ADD COLUMN rejection_reason TEXT
                """))
                db.session.commit()
                logger.info("✅ Added rejection_reason column to signup_requests table")
            except Exception as e:
                if "already exists" in str(e) or "duplicate column" in str(e).lower():
                    logger.info("⏭️  rejection_reason column already exists")
                    db.session.rollback()
                else:
                    raise
            
            # Check and add missing columns to enrollment_requests table
            logger.info("Checking enrollment_requests table...")
            
            # Add quality_scores column if it doesn't exist (for JSON data)
            try:
                db.session.execute(text("""
                    ALTER TABLE enrollment_requests ADD COLUMN quality_scores TEXT
                """))
                db.session.commit()
                logger.info("✅ Added quality_scores column to enrollment_requests table")
            except Exception as e:
                if "already exists" in str(e) or "duplicate column" in str(e).lower():
                    logger.info("⏭️  quality_scores column already exists")
                    db.session.rollback()
                else:
                    raise
            
            # Add processed_by column to enrollment_requests if it doesn't exist
            try:
                db.session.execute(text("""
                    ALTER TABLE enrollment_requests ADD COLUMN processed_by VARCHAR(255)
                """))
                db.session.commit()
                logger.info("✅ Added processed_by column to enrollment_requests table")
            except Exception as e:
                if "already exists" in str(e) or "duplicate column" in str(e).lower():
                    logger.info("⏭️  processed_by column already exists")
                    db.session.rollback()
                else:
                    raise
            
            # Add processed_at column to enrollment_requests if it doesn't exist
            try:
                db.session.execute(text("""
                    ALTER TABLE enrollment_requests ADD COLUMN processed_at DATETIME
                """))
                db.session.commit()
                logger.info("✅ Added processed_at column to enrollment_requests table")
            except Exception as e:
                if "already exists" in str(e) or "duplicate column" in str(e).lower():
                    logger.info("⏭️  processed_at column already exists")
                    db.session.rollback()
                else:
                    raise
            
            # Add rejection_reason column to enrollment_requests if it doesn't exist
            try:
                db.session.execute(text("""
                    ALTER TABLE enrollment_requests ADD COLUMN rejection_reason TEXT
                """))
                db.session.commit()
                logger.info("✅ Added rejection_reason column to enrollment_requests table")
            except Exception as e:
                if "already exists" in str(e) or "duplicate column" in str(e).lower():
                    logger.info("⏭️  rejection_reason column already exists")
                    db.session.rollback()
                else:
                    raise
            
            # Check and modify system_logs table to allow NULL user_id
            logger.info("Checking system_logs table...")
            
            # For SQLite, we need to check if the column constraint needs modification
            try:
                # Check if system_logs table exists and has data
                result = db.session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='system_logs'"))
                if result.fetchone():
                    # SQLite doesn't support ALTER COLUMN directly, so we need to recreate the table
                    # First, check if user_id already allows NULL
                    try:
                        db.session.execute(text("""
                            INSERT INTO system_logs (action, user_type, user_id, user_email, ip_address)
                            VALUES ('test', 'user', NULL, 'test@example.com', '0.0.0.0')
                        """))
                        db.session.rollback()
                        logger.info("⏭️  system_logs.user_id already allows NULL")
                    except Exception as test_e:
                        if "NOT NULL constraint failed" in str(test_e):
                            db.session.rollback()
                            # Need to modify the table
                            logger.info("Modifying system_logs table to allow NULL user_id...")
                            
                            # Create a temporary table with the new schema
                            db.session.execute(text("""
                                CREATE TABLE system_logs_new (
                                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                                    action VARCHAR(100) NOT NULL,
                                    user_type VARCHAR(20) NOT NULL,
                                    user_id INTEGER,
                                    user_email VARCHAR(120) NOT NULL,
                                    details TEXT,
                                    ip_address VARCHAR(50),
                                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                                )
                            """))
                            
                            # Copy existing data
                            db.session.execute(text("""
                                INSERT INTO system_logs_new (id, action, user_type, user_id, user_email, details, ip_address, timestamp)
                                SELECT id, action, user_type, user_id, user_email, details, ip_address, timestamp
                                FROM system_logs
                            """))
                            
                            # Drop old table and rename new one
                            db.session.execute(text("DROP TABLE system_logs"))
                            db.session.execute(text("ALTER TABLE system_logs_new RENAME TO system_logs"))
                            
                            # Recreate index
                            db.session.execute(text("""
                                CREATE INDEX idx_system_logs_timestamp ON system_logs (timestamp DESC)
                            """))
                            
                            db.session.commit()
                            logger.info("✅ Modified system_logs table to allow NULL user_id")
                        else:
                            db.session.rollback()
                            raise
                else:
                    logger.info("⏭️  system_logs table doesn't exist yet")
            except Exception as e:
                if "already exists" in str(e).lower() or "table" in str(e).lower() and "exists" in str(e).lower():
                    logger.info("⏭️  system_logs migration already applied or table structure is correct")
                    db.session.rollback()
                else:
                    raise
            
            logger.info("\n✅ Database migration completed successfully!")
            logger.info("All required columns have been added or already exist.")
            
        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            db.session.rollback()
            raise

if __name__ == '__main__':
    migrate_database()
