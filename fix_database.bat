@echo off
echo ========================================
echo Database Migration Script
echo ========================================
echo.
echo This will add missing columns to your database
echo.
pause

echo Running migration...
python migrate_database.py

if %errorlevel% neq 0 (
    echo.
    echo ❌ Migration failed!
    echo Please check the error above.
    pause
    exit /b 1
)

echo.
echo ========================================
echo ✅ Migration completed successfully!
echo ========================================
echo.
echo Next steps:
echo 1. Start the server: python app.py
echo 2. Test signup at: http://localhost:5000/register
echo 3. Login as SuperAdmin: superadmin@admin.com / superadmin123
echo 4. Check Camera Manager: http://localhost:5000/superadmin/cameras
echo.
pause
