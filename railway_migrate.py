"""
Railway PostgreSQL Migration Script
Run this INSIDE Railway, not locally!

CORRECT WAY:
1. Add to Railway start command: python railway_migrate.py && gunicorn app:app
2. Or use Railway Shell: railway shell, then: python railway_migrate.py

WRONG WAY:
❌ railway run python railway_migrate.py (from local machine - won't work!)
"""
import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get database URL from environment (Railway sets this automatically)
DATABASE_URL = os.environ.get('DATABASE_URL') or os.environ.get('DATABASE_PRIVATE_URL')

if not DATABASE_URL:
    logger.error("❌ DATABASE_URL environment variable not set!")
    logger.error("This script must be run INSIDE Railway, not locally!")
    logger.error("")
    logger.error("To fix:")
    logger.error("1. Go to Railway Dashboard → Your Service → Settings")
    logger.error("2. Change Start Command to: python railway_migrate.py && gunicorn app:app")
    logger.error("3. Redeploy")
    logger.error("")
    logger.error("Or use: railway shell, then run: python railway_migrate.py")
    exit(1)

# Check if running on Railway (not locally)
if 'railway.internal' in DATABASE_URL and 'RAILWAY_ENVIRONMENT' not in os.environ:
    logger.error("❌ Cannot run this script locally!")
    logger.error("The DATABASE_URL points to Railway's internal network.")
    logger.error("")
    logger.error("✅ SOLUTION: Run migration INSIDE Railway:")
    logger.error("1. Update Railway start command to:")
    logger.error("   python railway_migrate.py && gunicorn app:app")
    logger.error("")
    logger.error("2. Or use Railway Shell:")
    logger.error("   railway shell")
    logger.error("   python railway_migrate.py")
    logger.error("")
    logger.error("3. Or deploy to Heroku/Render (they auto-run on deploy)")
    exit(1)

# Fix for SQLAlchemy 1.4+ with PostgreSQL
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

logger.info(f"✅ Running migration on Railway...")

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
                
                # System logs table - Allow NULL user_id for pre-registration logs
                ("ALTER TABLE system_logs ALTER COLUMN user_id DROP NOT NULL", "user_id nullable in system_logs"),
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
