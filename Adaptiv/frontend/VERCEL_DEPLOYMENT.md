# Deploying Your Dynamic Pricing App to Vercel

This guide walks you through deploying the frontend of your Dynamic Pricing application to Vercel.

## Prerequisites

- A [Vercel account](https://vercel.com/signup)
- Git repository containing your code (GitHub, GitLab, or Bitbucket)
- Your backend API hosted separately (see Backend Deployment section)

## Frontend Deployment Steps

1. **Push your code to a Git repository** if you haven't already

2. **Connect your repository to Vercel**:
   - Go to [Vercel Dashboard](https://vercel.com/dashboard)
   - Click "Add New" > "Project"
   - Import your Git repository
   - Select the "Adaptiv/frontend" directory as the root directory

3. **Configure your project**:
   - Framework Preset: Create React App
   - Build Command: `npm run build` (already set in vercel.json)
   - Output Directory: `build` (already set in vercel.json)

4. **Set up environment variables**:
   - Add `REACT_APP_API_URL` pointing to your hosted backend API
   - Example: `https://your-backend-api-url.com/api`

5. **Deploy**:
   - Click "Deploy"
   - Vercel will build and deploy your application

## Backend Deployment Options

Since Vercel is primarily for frontend applications, you'll need to host your Python backend separately. Options include:

1. **Heroku**:
   - Supports Python applications
   - Has a free tier for small projects
   - Easy deployment with Git

2. **Railway**:
   - Modern platform with Python support
   - Simple deployment process
   - Reasonable free tier

3. **DigitalOcean App Platform**:
   - Robust hosting for Python applications
   - Starts at $5/month

4. **AWS Elastic Beanstalk**:
   - Enterprise-grade hosting
   - More complex setup
   - Good for production applications

After deploying your backend, update the `REACT_APP_API_URL` in Vercel to point to your new backend URL.

## Local Testing Before Deployment

To test your application locally with production environment variables:

1. Create a `.env.production.local` file in the frontend directory
2. Add `REACT_APP_API_URL=https://your-backend-url.com/api`
3. Run `npm run build` followed by `npx serve -s build`

## Troubleshooting

- **API Connection Issues**: Ensure CORS is properly configured in your backend
- **Build Failures**: Check Vercel build logs for specific errors
- **Missing Environment Variables**: Verify environment variables are correctly set in Vercel dashboard
