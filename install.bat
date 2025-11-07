@echo off
echo ========================================
echo Smart Attendance System - Installation
echo ========================================
echo.

echo [1/5] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from python.org
    pause
    exit /b 1
)
python --version
echo.

echo [2/5] Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)
echo Dependencies installed successfully!
echo.

echo [3/5] Optimizing database...
python db_optimization.py
if errorlevel 1 (
    echo WARNING: Database optimization failed (this is okay for first run)
)
echo.

echo [4/5] Creating necessary directories...
if not exist "uploads" mkdir uploads
if not exist "face_data" mkdir face_data
if not exist "faiss_index" mkdir faiss_index
if not exist "logs" mkdir logs
echo Directories created!
echo.

echo [5/5] Checking environment file...
if not exist ".env" (
    echo WARNING: .env file not found
    echo Creating from .env.example...
    copy .env.example .env
    echo.
    echo IMPORTANT: Edit .env file with your settings!
    echo.
)

echo ========================================
echo Installation Complete!
echo ========================================
echo.
echo To start the server, run:
echo   python app.py
echo.
echo Default credentials:
echo   Super Admin: superadmin@admin.com / superadmin123
echo   Admin: admin@admin.com / admin123
echo.
echo Access the application at:
echo   http://localhost:5000
echo.
echo For production deployment, see:
echo   PRODUCTION_DEPLOYMENT.md
echo.
pause
