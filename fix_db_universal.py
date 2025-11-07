"""
Universal database fix for system_logs table
Works with any database location by using Flask app config
"""
import os
import sys

# Temporarily disable tensorflow/face service imports
os.environ['SKIP_FACE_SERVICE'] = '1'

try:
    from flask import Flask
    from flask_sqlalchemy import SQLAlchemy
    from sqlalchemy import text, inspect
    import logging
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Create a minimal Flask app with just the database config
    app = Flask(__name__)
    
    # Load config
    from config import DevelopmentConfig
    app.config.from_object(DevelopmentConfig)
    
    db = SQLAlchemy(app)
    
    def fix_system_logs():
        """Modify system_logs table to allow NULL user_id"""
        with app.app_context():
            try:
                inspector = inspect(db.engine)
                
                # Check if table exists
                if 'system_logs' not in inspector.get_table_names():
                    logger.info("✅ system_logs table doesn't exist yet - will be created with correct schema")
                    return
                
                # For SQLite databases
                if 'sqlite' in str(db.engine.url):
                    logger.info("Detected SQLite database")
                    
                    # Test if user_id already allows NULL
                    try:
                        db.session.execute(text("""
                            INSERT INTO system_logs (action, user_type, user_id, user_email, ip_address)
                            VALUES ('test', 'user', NULL, 'test@example.com', '0.0.0.0')
                        """))
                        db.session.rollback()
                        logger.info("✅ system_logs.user_id already allows NULL - no fix needed")
                        return
                    except Exception as e:
                        if "NOT NULL constraint failed" in str(e):
                            db.session.rollback()
                            logger.info("Fixing system_logs table...")
                            
                            # Create new table with correct schema
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
                            
                            # Copy data
                            db.session.execute(text("""
                                INSERT INTO system_logs_new 
                                SELECT * FROM system_logs
                            """))
                            
                            # Replace old table
                            db.session.execute(text("DROP TABLE system_logs"))
                            db.session.execute(text("ALTER TABLE system_logs_new RENAME TO system_logs"))
                            
                            # Recreate index
                            db.session.execute(text("""
                                CREATE INDEX idx_system_logs_timestamp ON system_logs (timestamp DESC)
                            """))
                            
                            db.session.commit()
                            logger.info("✅ Successfully fixed system_logs table!")
                        else:
                            raise
                
                # For PostgreSQL databases
                elif 'postgres' in str(db.engine.url):
                    logger.info("Detected PostgreSQL database")
                    db.session.execute(text("""
                        ALTER TABLE system_logs ALTER COLUMN user_id DROP NOT NULL
                    """))
                    db.session.commit()
                    logger.info("✅ Successfully modified system_logs.user_id to allow NULL")
                
            except Exception as e:
                logger.error(f"❌ Fix failed: {e}")
                db.session.rollback()
                raise
    
    if __name__ == '__main__':
        logger.info(f"Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
        fix_system_logs()
        print("\n✅ Database fix completed! Restart your app to register users.")
        
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("\nTrying alternative approach...")
    
    # Fallback: Direct SQL approach
    import sqlite3
    db_path = input("Enter the full path to your attendance.db file: ")
    
    if not os.path.exists(db_path):
        print(f"File not found: {db_path}")
        sys.exit(1)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Test if fix is needed
        cursor.execute("""
            INSERT INTO system_logs (action, user_type, user_id, user_email, ip_address)
            VALUES ('test', 'user', NULL, 'test@example.com', '0.0.0.0')
        """)
        conn.rollback()
        print("✅ system_logs.user_id already allows NULL")
    except sqlite3.IntegrityError:
        conn.rollback()
        print("Applying fix...")
        
        cursor.execute("""CREATE TABLE system_logs_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action VARCHAR(100) NOT NULL,
            user_type VARCHAR(20) NOT NULL,
            user_id INTEGER,
            user_email VARCHAR(120) NOT NULL,
            details TEXT,
            ip_address VARCHAR(50),
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )""")
        
        cursor.execute("INSERT INTO system_logs_new SELECT * FROM system_logs")
        cursor.execute("DROP TABLE system_logs")
        cursor.execute("ALTER TABLE system_logs_new RENAME TO system_logs")
        cursor.execute("CREATE INDEX idx_system_logs_timestamp ON system_logs (timestamp DESC)")
        
        conn.commit()
        print("✅ Fix applied successfully!")
    
    conn.close()
