"""
Railway PostgreSQL Migration Script
Run this on your production server to migrate the database
"""
import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get database URL from environment (Railway sets this automatically)
DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    logger.error("❌ DATABASE_URL environment variable not set!")
    logger.error("This script must be run on Railway or with DATABASE_URL set")
    exit(1)

# Fix for SQLAlchemy 1.4+ with PostgreSQL
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

logger.info(f"Connecting to database...")

def migrate_database():
    """Add missing columns to database tables"""
    try:
        engine = create_engine(DATABASE_URL)
        
        with engine.connect() as conn:
            logger.info("✅ Connected to Railway PostgreSQL database")
            
            # Check and add missing columns to users table
            logger.info("Checking users table...")
            
            migrations = [
                # Users table
                ("ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT FALSE", "email_verified to users"),
                ("ALTER TABLE users ADD COLUMN IF NOT EXISTS verified_at TIMESTAMP", "verified_at to users"),
                
                # Signup requests table
                ("ALTER TABLE signup_requests ADD COLUMN IF NOT EXISTS documents TEXT", "documents to signup_requests"),
                ("ALTER TABLE signup_requests ADD COLUMN IF NOT EXISTS processed_by VARCHAR(255)", "processed_by to signup_requests"),
                ("ALTER TABLE signup_requests ADD COLUMN IF NOT EXISTS processed_at TIMESTAMP", "processed_at to signup_requests"),
                ("ALTER TABLE signup_requests ADD COLUMN IF NOT EXISTS rejection_reason TEXT", "rejection_reason to signup_requests"),
                
                # Enrollment requests table
                ("ALTER TABLE enrollment_requests ADD COLUMN IF NOT EXISTS quality_scores TEXT", "quality_scores to enrollment_requests"),
                ("ALTER TABLE enrollment_requests ADD COLUMN IF NOT EXISTS processed_by VARCHAR(255)", "processed_by to enrollment_requests"),
                ("ALTER TABLE enrollment_requests ADD COLUMN IF NOT EXISTS processed_at TIMESTAMP", "processed_at to enrollment_requests"),
                ("ALTER TABLE enrollment_requests ADD COLUMN IF NOT EXISTS rejection_reason TEXT", "rejection_reason to enrollment_requests"),
            ]
            
            for sql, description in migrations:
                try:
                    conn.execute(text(sql))
                    conn.commit()
                    logger.info(f"✅ Added {description}")
                except ProgrammingError as e:
                    if "already exists" in str(e).lower():
                        logger.info(f"⏭️  {description} already exists")
                        conn.rollback()
                    else:
                        logger.error(f"❌ Error adding {description}: {e}")
                        conn.rollback()
                except Exception as e:
                    logger.error(f"❌ Error adding {description}: {e}")
                    conn.rollback()
            
            logger.info("\n" + "="*50)
            logger.info("✅ Railway database migration completed!")
            logger.info("="*50)
            logger.info("\nYou can now:")
            logger.info("1. Test signup at your Railway URL")
            logger.info("2. Access Camera Manager")
            logger.info("3. Use Enrollment Requests")
            
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise

if __name__ == '__main__':
    logger.info("="*50)
    logger.info("Railway PostgreSQL Migration Script")
    logger.info("="*50)
    migrate_database()
