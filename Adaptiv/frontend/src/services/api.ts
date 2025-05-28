import axios from 'axios';

// Create an axios instance with default config
// IMPORTANT: Use a hard-coded backend URL if env variable is not set or if in debug mode
// This ensures we're not trying to make API calls to our own Vercel domain
let baseUrlFromEnv;

// Check if we're running in the deployed Vercel environment
const isVercel = typeof window !== 'undefined' && 
                 (window.location.hostname.includes('vercel.app') || 
                  window.location.hostname.includes('adaptiv-eight'));

if (isVercel) {
  // Hard-code the Render backend URL for deployed versions
  baseUrlFromEnv = 'https://adaptiv-backend.onrender.com';
  console.log('Detected Vercel environment, using hardcoded backend URL:', baseUrlFromEnv);
} else {
  // For local development, use the environment variable or localhost
  baseUrlFromEnv = process.env.REACT_APP_API_URL || 'http://localhost:8000';
  console.log('Using environment backend URL:', baseUrlFromEnv);
}

// Normalize base URL to always end with '/api/'
let normalizedBase = baseUrlFromEnv;
// Ensure trailing slash for easier concatenation
if (!normalizedBase.endsWith('/')) {
  normalizedBase += '/';
}
// Ensure it ends with 'api/'
if (!normalizedBase.endsWith('api/')) {
  normalizedBase += 'api/';
}

const API_BASE_URL = normalizedBase;

// Log the API URL for debugging
console.log('API Base URL:', API_BASE_URL);

// Safeguard against incorrect Render deployment URL
if (API_BASE_URL.includes('api.render.com/deploy')) {
  console.error('Invalid API URL detected (using Render deployment URL instead of app URL)');
  // Fall back to localhost for development or to a known working URL pattern for production
  if (window.location.hostname === 'localhost') {
    console.log('Falling back to localhost API URL');
  } else {
    // Extract the service ID from the invalid URL to build a proper one
    const serviceIdMatch = API_BASE_URL.match(/srv-[a-z0-9]+/);
    const serviceId = serviceIdMatch ? serviceIdMatch[0] : null;
    if (serviceId) {
      console.log(`Attempting to construct proper URL using service ID: ${serviceId}`);
    }
  }
}

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json'
  }
});

// Request interceptor: (1) fix URL duplication, (2) add auth token
api.interceptors.request.use(
  config => {
    // Fix URL path issues
    if (config.url) {
      // Remove any leading slash to avoid double slashes
      if (config.url.startsWith('/')) {
        config.url = config.url.substring(1);
      }
      // Remove an extra 'api/' prefix if present (we already have /api in baseURL)
      if (config.url.startsWith('api/')) {
        config.url = config.url.substring(4);
      }
    }

    // CRITICAL: Always check for token and apply it on every request
    // We do this even if the header might already be set elsewhere
    // This guarantees the token is included after page refresh
    const token = localStorage.getItem('token');
    if (token) {
      // Apply authorization header in a simpler way to avoid TypeScript errors
      // Directly set the header without conditional logic
      if (typeof config.headers === 'object') {
        // Set header using bracket notation to avoid TypeScript complaints
        config.headers['Authorization'] = `Bearer ${token}`;
      }
      
      // Also ensure it's set on the axios instance for future requests
      api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      
      // Log token presence for debugging (not the actual token value)
      console.log(`Auth token applied to ${config.url || 'request'}`);
    } else {
      console.log(`No auth token available for ${config.url || 'request'}`);
    }
    
    return config;
  },
  error => Promise.reject(error)
);

// Response interceptor to handle common errors
api.interceptors.response.use(
  response => response,
  error => {
    // Log the error for debugging
    console.log('API error response:', error.message);
    
    // Handle unauthorized errors (token expired, etc.)
    if (error.response && error.response.status === 401) {
      console.log('Received 401 error, path:', error.config.url);
      
      const requestUrl = error.config.url || '';
      const isAuthEndpoint = requestUrl.includes('/auth/token') || 
                           requestUrl.includes('/login') ||
                           (requestUrl.includes('/me') && error.response.data?.detail?.includes('credentials'));
      
      const isAgentEndpoint = requestUrl.includes('/agents-sdk/');
      
      // Check for token and reapply if missing
      const token = localStorage.getItem('token');
      if (token && !api.defaults.headers.common['Authorization']) {
        console.log('Re-applying missing auth token to headers');
        api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
        axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
        
        // If this was an agent endpoint error and we reapplied the token,
        // we'll return a special error that can be retried
        if (isAgentEndpoint) {
          error.shouldRetry = true;
          return Promise.reject(error);
        }
      }
      
      if (isAuthEndpoint) {
        console.log('Authentication endpoint error, clearing invalid token');
        localStorage.removeItem('token');
        
        // Only redirect if we're not already on the login page to avoid redirect loops
        if (!window.location.pathname.includes('/login')) {
          console.log('Redirecting to login due to auth endpoint error');
          window.location.href = '/login';
        }
      } else if (isAgentEndpoint) {
        console.log('Agent endpoint 401 error, token may be invalid');
        // For agent endpoint errors, we might want to refresh the token or redirect
        // if the user is clearly not authenticated
        
        if (!token) {
          console.log('No token found for agent endpoint request, redirecting to login');
          if (!window.location.pathname.includes('/login')) {
            window.location.href = '/login';
          }
        }
      } else {
        // For all other 401 errors, just log but don't disrupt the user session
        console.log('Non-auth endpoint 401 error, not disrupting session');
      }
    }
    return Promise.reject(error);
  }
);

export default api;
