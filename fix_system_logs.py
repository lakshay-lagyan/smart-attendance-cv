"""
Quick fix for system_logs table to allow NULL user_id
"""
import sqlite3
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_system_logs():
    """Modify system_logs table to allow NULL user_id"""
    try:
        # Try to find the database file
        possible_paths = [
            'attendance.db',
            'instance/attendance.db',
            os.path.join(os.path.dirname(__file__), 'attendance.db'),
            os.path.join(os.path.dirname(__file__), 'instance', 'attendance.db'),
        ]
        
        db_path = None
        for path in possible_paths:
            if os.path.exists(path):
                db_path = path
                logger.info(f"Found database at: {path}")
                break
        
        if db_path is None:
            logger.error("Database file not found. Please ensure the app has been run at least once.")
            logger.info("Tried paths: " + ", ".join(possible_paths))
            return
        
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='system_logs'")
        if not cursor.fetchone():
            logger.info("system_logs table doesn't exist yet, nothing to migrate")
            conn.close()
            return
        
        # Test if user_id already allows NULL
        try:
            cursor.execute("""
                INSERT INTO system_logs (action, user_type, user_id, user_email, ip_address)
                VALUES ('test', 'user', NULL, 'test@example.com', '0.0.0.0')
            """)
            conn.rollback()
            logger.info("✅ system_logs.user_id already allows NULL - no migration needed")
            conn.close()
            return
        except sqlite3.IntegrityError as e:
            if "NOT NULL constraint failed" not in str(e):
                raise
            # Need to modify the table
            logger.info("Modifying system_logs table to allow NULL user_id...")
        
        # Create a new table with the correct schema
        cursor.execute("""
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
        """)
        
        # Copy existing data
        cursor.execute("""
            INSERT INTO system_logs_new (id, action, user_type, user_id, user_email, details, ip_address, timestamp)
            SELECT id, action, user_type, user_id, user_email, details, ip_address, timestamp
            FROM system_logs
        """)
        
        # Drop old table and rename new one
        cursor.execute("DROP TABLE system_logs")
        cursor.execute("ALTER TABLE system_logs_new RENAME TO system_logs")
        
        # Recreate index
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_system_logs_timestamp ON system_logs (timestamp DESC)")
        
        conn.commit()
        logger.info("✅ Successfully modified system_logs table to allow NULL user_id")
        conn.close()
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        raise

if __name__ == '__main__':
    fix_system_logs()
    print("\n✅ Database fix completed! You can now register users.")
