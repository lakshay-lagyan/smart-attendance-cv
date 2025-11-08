@echo off
echo ========================================
echo Railway Deployment Helper
echo ========================================
echo.

echo This script will help you deploy to Railway.
echo.
echo PREREQUISITES:
echo 1. Railway CLI installed (https://docs.railway.app/develop/cli)
echo 2. Railway account created
echo.

echo Installing Railway CLI (if not installed)...
echo.

where railway >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Railway CLI not found. Installing via npm...
    npm install -g @railway/cli
    if %ERRORLEVEL% NEQ 0 (
        echo ERROR: Failed to install Railway CLI
        echo Please install manually: npm install -g @railway/cli
        pause
        exit /b 1
    )
)

echo.
echo ========================================
echo Step 1: Login to Railway
echo ========================================
railway login

echo.
echo ========================================
echo Step 2: Initialize New Project
echo ========================================
echo Creating new Railway project...
railway init

echo.
echo ========================================
echo Step 3: Add PostgreSQL Database
echo ========================================
echo.
echo IMPORTANT: Open Railway dashboard and add PostgreSQL:
echo 1. Go to https://railway.app/dashboard
echo 2. Open your new project
echo 3. Click "New" → "Database" → "PostgreSQL"
echo.
pause

echo.
echo ========================================
echo Step 4: Set Environment Variables
echo ========================================
echo.
echo Setting required environment variables...

set /p SECRET_KEY="Enter SECRET_KEY (or press Enter for random): "
if "%SECRET_KEY%"=="" set SECRET_KEY=prod-secret-key-%RANDOM%%RANDOM%%RANDOM%

set /p JWT_SECRET="Enter JWT_SECRET_KEY (or press Enter for random): "
if "%JWT_SECRET%"=="" set JWT_SECRET=jwt-secret-key-%RANDOM%%RANDOM%%RANDOM%

railway variables set SECRET_KEY="%SECRET_KEY%"
railway variables set JWT_SECRET_KEY="%JWT_SECRET%"
railway variables set FLASK_ENV=production

echo.
echo Environment variables set successfully!

echo.
echo ========================================
echo Step 5: Deploy Application
echo ========================================
echo.
echo Deploying to Railway...
railway up

echo.
echo ========================================
echo DEPLOYMENT COMPLETE!
echo ========================================
echo.
echo Getting your deployment URL...
railway domain

echo.
echo Your application is now deployed!
echo.
echo Next steps:
echo 1. Visit your Railway URL (shown above)
echo 2. Check logs: railway logs
echo 3. Test the signup functionality
echo.
pause
