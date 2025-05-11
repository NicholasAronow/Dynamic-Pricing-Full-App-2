# Vercel Environment Configuration for Adaptiv

To ensure your frontend correctly connects to your backend API, you need to set the proper environment variable in your Vercel project.

## Setting the Environment Variable

1. Go to your Vercel dashboard and select your project
2. Navigate to "Settings" > "Environment Variables"
3. Add the following environment variable:

| Name | Value |
|------|-------|
| `REACT_APP_API_URL` | `https://adaptiv-backend.onrender.com/api` |

(Replace `adaptiv-backend.onrender.com` with your actual Render backend URL)

4. Select which environments should use this variable (Production, Preview, Development)
5. Click "Save"
6. Redeploy your application for the changes to take effect

## Testing the Connection

After redeploying, you can test the connection by:

1. Opening your browser's developer console (F12)
2. Going to the Network tab
3. Attempting to register or log in
4. Checking that the requests are going to your Render backend URL rather than to Vercel

## Troubleshooting

If you're still having issues:

1. Verify that your backend is correctly running on Render (check the health endpoint)
2. Make sure CORS is properly configured on your backend to accept requests from your Vercel domain
3. Check that the environment variable is correctly set and applied in the build

## Note on Local Development

When developing locally, the app will default to `http://localhost:8000/api` if no `REACT_APP_API_URL` is found. This allows you to work with your local backend during development.
