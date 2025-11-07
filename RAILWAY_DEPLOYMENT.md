# Railway Deployment Guide

## Prerequisites
- Railway account (https://railway.app)
- GitHub repository connected
- PostgreSQL database

## Deployment Steps

### Step 1: Create New Railway Project
1. Go to https://railway.app/dashboard
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Choose your repository: `lakshay-lagyan/smart-attendance-cv`

### Step 2: Add PostgreSQL Database
1. Click "New" in your project
2. Select "Database" → "PostgreSQL"
3. Railway will automatically set `DATABASE_URL` environment variable

### Step 3: Configure Environment Variables
Add these variables in Railway Settings → Variables:

```
SECRET_KEY=your-secret-key-here-change-this
JWT_SECRET_KEY=your-jwt-secret-key-here-change-this
FLASK_ENV=production
PORT=5000
```

### Step 4: Deploy
1. Railway will auto-deploy when you push to GitHub
2. Or click "Deploy" manually in Railway dashboard

### Step 5: Access Your App
- Your app will be available at: `https://your-project.up.railway.app`
- Railway provides the URL in Settings → Domains

## What Happens on Deploy

1. **Build Phase** (Dockerfile):
   - Installs Python 3.11
   - Installs system dependencies
   - Installs Python packages from requirements.txt
   - Sets up directories

2. **Start Phase** (start.sh):
   - Runs database migrations automatically
   - Creates necessary directories
   - Starts Gunicorn server with 2 workers

## Database Migration

The `railway_migrate.py` script automatically:
- Adds missing columns to all tables
- Fixes system_logs.user_id to allow NULL
- Creates indexes for performance

## Testing After Deployment

1. **Access the app**: Visit your Railway URL
2. **Test signup**: Try registering a new user
3. **Check logs**: Monitor Railway logs for any errors

## Troubleshooting

### If deployment fails:
1. Check Railway logs: Dashboard → Deployments → View Logs
2. Verify environment variables are set
3. Ensure PostgreSQL is running

### If signup fails:
1. Check that DATABASE_URL is set
2. Verify migrations ran successfully
3. Look for "system_logs" errors in logs

## URLs You'll Get

After deployment, you'll have:
- **App URL**: `https://[your-project].up.railway.app`
- **API Base**: `https://[your-project].up.railway.app/api`
- **Admin Panel**: `https://[your-project].up.railway.app/admin`

## Custom Domain (Optional)

1. Go to Settings → Domains in Railway
2. Click "Generate Domain" or add custom domain
3. Update DNS records if using custom domain
