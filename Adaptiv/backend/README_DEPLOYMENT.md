# Adaptiv Backend Deployment Guide

This guide covers deploying your FastAPI backend to Render, which provides an excellent free tier for Python applications.

## Prerequisites

- A [Render Account](https://render.com/signup)
- Your code in a Git repository (GitHub, GitLab, or Bitbucket)

## Deployment Steps

### 1. Create a New Web Service on Render

1. **Log in to Render** and go to your dashboard
2. Click **New** and select **Web Service**
3. Connect to your repository
4. Configure the service:
   - **Name**: `adaptiv-backend` (or your preferred name)
   - **Root Directory**: Select the path to your backend (`Adaptiv/backend`)
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

### 2. Configure Environment Variables

Add these environment variables in the Render dashboard:
- `DATABASE_URL`: Your PostgreSQL connection string
- Any other sensitive variables your app needs

### 3. Deploy Your Service

Click **Create Web Service** and Render will automatically deploy your application.

### 4. Get Your API URL

After deployment completes, Render will provide a URL like:
- `https://adaptiv-backend.onrender.com`

Use this URL for setting up your Vercel frontend.

## Database Options

1. **Render PostgreSQL**:
   - Render offers PostgreSQL databases with a free tier
   - Easy to connect to your Render web service

2. **Supabase**:
   - Free tier with more generous limits
   - Simple to set up

3. **Neon.tech**:
   - Serverless PostgreSQL with a free tier
   - Scales to zero when not in use

## Important Notes

- The **free tier on Render** will spin down after periods of inactivity, causing a delay on the first request after inactivity
- For production use, consider upgrading to a paid tier ($7/month) to avoid spin-down
- Make sure all environment variables are properly set before deployment
