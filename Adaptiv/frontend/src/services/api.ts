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

// Remove trailing /api if present to avoid double prefixing
if (baseUrlFromEnv.endsWith('/api')) {
  baseUrlFromEnv = baseUrlFromEnv.slice(0, -4); // Remove trailing /api
}

const API_BASE_URL = baseUrlFromEnv;

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

// Request interceptor to add auth token
api.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  error => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle common errors
api.interceptors.response.use(
  response => response,
  error => {
    // Handle unauthorized errors (token expired, etc.)
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;
