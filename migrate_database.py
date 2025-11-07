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
            
            logger.info("\n✅ Database migration completed successfully!")
            logger.info("All required columns have been added or already exist.")
            
        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            db.session.rollback()
            raise

if __name__ == '__main__':
    migrate_database()
