# Render Deployment Instructions

## 1. Fix for Current Deployment Error

The current deployment is failing because of a missing dependency. We've added these to your requirements.txt:
- `email-validator==2.0.0` - Required by Pydantic for email validation
- `gunicorn==20.1.0` - A production-ready WSGI HTTP server

## 2. Database Configuration

Your application is currently using SQLite, which won't work well in a cloud environment. For Render deployment:

### Option A: Use Render PostgreSQL Service
1. Create a PostgreSQL database in Render
2. In your Render web service settings, add these environment variables:
   - `DATABASE_URL`: The PostgreSQL connection string provided by Render
   - `SECRET_KEY`: A secure random string for JWT tokens

### Option B: External PostgreSQL (e.g., Supabase, Neon)
1. Create a PostgreSQL database on Supabase, Neon, or another provider
2. Configure environment variables in Render:
   - `DATABASE_URL`: Your PostgreSQL connection string
   - `SECRET_KEY`: A secure random string for JWT tokens

## 3. Update Deployment Configuration

For your Render service:

1. **Root Directory**: `Adaptiv/backend`
2. **Runtime**: Python 3
3. **Build Command**: `pip install -r requirements.txt`
4. **Start Command**: `gunicorn main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT`

## 4. Database Migration

After deployment, you may need to run migrations to create the database schema:

1. Add this command in the Render dashboard's "Shell" tab:
   ```
   python -c "from database import Base, engine; Base.metadata.create_all(bind=engine)"
   ```

## 5. Vercel Frontend Configuration

After your backend is successfully deployed:

1. Update your Vercel environment variable:
   - `REACT_APP_API_URL`: `https://your-render-service-name.onrender.com/api`

2. Redeploy your frontend if needed.

## Troubleshooting

If you continue to have deployment issues:
1. Check the Render logs for specific error messages
2. Verify that your environment variables are correctly set
3. Confirm that your database connection string is properly formatted
4. Ensure your database user has proper permissions
