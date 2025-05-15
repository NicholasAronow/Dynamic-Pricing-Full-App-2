import React, { createContext, useState, useContext, useEffect, ReactNode } from 'react';
import axios from 'axios';
import jwt_decode from 'jwt-decode';

interface AuthContextType {
  isAuthenticated: boolean;
  user: any;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType>({
  isAuthenticated: false,
  user: null,
  loading: true,
  login: async () => {},
  register: async () => {},
  logout: () => {},
});

export const useAuth = () => useContext(AuthContext);

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [user, setUser] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const initializeAuth = async () => {
      try {
        console.log('Initializing auth state...');
        // Check if there's a token in localStorage
        const token = localStorage.getItem('token');
        if (!token) {
          console.log('No token found in localStorage');
          setLoading(false);
          return;
        }
        
        console.log('Token found, applying to auth state');
        
        // Apply token immediately to indicate authentication
        // This early flag setting helps prevent premature redirects
        setIsAuthenticated(true);
        
        // Import the API service to ensure consistent headers
        const apiModule = await import('../services/api');
        const api = apiModule.default;
        
        try {
          // Verify token expiration
          const decoded: any = jwt_decode(token);
          const currentTime = Date.now() / 1000;
          
          console.log('Token expiration check - Current time:', new Date(currentTime * 1000).toISOString());
          console.log('Token expiration time:', new Date(decoded.exp * 1000).toISOString());
          
          // Add a full day buffer to account for timezone and clock differences
          // This is because the backend now uses a long-lived token (7 days)
          if (decoded.exp > currentTime - 86400) { // 1 day buffer
            console.log('Token is valid, setting auth headers...');
            
            // Set auth headers for all future requests
            api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
            axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
            
            // Get user data - but we've already set isAuthenticated flag
            try {
              const userData = await fetchUserData();
              if (!userData) {
                console.warn('Could not fetch user data despite valid token');
                // We'll still consider the user logged in even if we can't fetch their data
              }
            } catch (userError) {
              console.warn('Error fetching user data, but keeping session active:', userError);
              // Even if we can't fetch user data, don't log out the user
            }
          } else {
            // Token expired
            console.log('Token expired, clearing auth state');
            logout(); // Use the logout function to ensure proper cleanup
          }
        } catch (error) {
          console.error('Error decoding token:', error);
          // Don't automatically logout on token decoding errors
          // The token might still be valid for the backend
          
          // Still apply the token to headers just in case
          api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
          axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
          
          // Try to fetch user data to verify the token with backend
          try {
            await fetchUserData();
            console.log('Token appears to be valid despite decode error');
          } catch (fetchError) {
            console.error('Token validation failed after decode error');
            logout();
          }
        }
      } catch (error) {
        console.error('Auth initialization error:', error);
      } finally {
        setLoading(false);
      }
    };
    
    initializeAuth();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchUserData = async () => {
    let retries = 2; // Allow a couple of retries
    
    while (retries >= 0) {
      try {
        // Use the same API instance as the other methods
        const api = (await import('../services/api')).default;
        const token = localStorage.getItem('token');
        
        // Double-check that token is in headers
        if (token && !api.defaults.headers.common['Authorization']) {
          console.log('Re-applying authorization header');
          api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
        }
        
        console.log('Fetching user data from:', api.defaults.baseURL + '/api/auth/me');
        
        const response = await api.get('/api/auth/me');
        console.log('User data received:', response.data);
        setUser(response.data);
        return response.data;
      } catch (error: any) {
        console.error(`Error fetching user data (${retries} retries left):`, error);
        retries--;
        
        // Only logout on critical auth errors after all retries fail
        if (retries < 0) {
          // Check for specific error conditions that indicate auth problems
          if (
            error.response?.status === 401 ||
            error.response?.status === 403 ||
            error.response?.data?.detail?.includes('credentials') ||
            error.response?.data?.detail?.includes('token')
          ) {
            console.log('Critical auth error, logging out');
            logout();
          } else {
            // For non-auth errors, don't logout but still return null
            console.log('Non-critical error fetching user data, keeping session');
          }
          return null;
        }
        
        // Wait a bit before retrying
        await new Promise(resolve => setTimeout(resolve, 500));
      }
    }
    
    return null;
  };

  const login = async (email: string, password: string) => {
    try {
      // IMPORTANT: Import api from services to ensure we use the backend URL, not Vercel
      const api = (await import('../services/api')).default;
      
      // Log the base URL being used
      console.log('Using API base URL:', api.defaults.baseURL);
      
      let response;
      try {
        // First try debug-login endpoint
        response = await api.post('/api/auth/debug-login', {
          email,
          password
        });
        console.log('Debug login successful');
      } catch (debugError) {
        // If debug endpoint isn't available (404), try regular login
        console.log('Debug login endpoint not available, trying regular login...');
        
        // Try the standard login endpoint
        try {
          response = await api.post('/api/auth/login', {
            email,
            password
          });
          console.log('Standard login successful');
        } catch (loginError) {
          // If that fails, try the token endpoint with form data format as a last resort
          console.log('Standard login failed, trying token endpoint...');
          response = await api.post('/api/auth/token', 
            new URLSearchParams({
              'username': email,
              'password': password
            }), 
            {
              headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
              }
            }
          );
          console.log('Token endpoint login successful');
        }
      }
      
      console.log('Login response:', response.data);
      
      // Handle both token formats (backend might return either token or access_token)
      const access_token = response.data.access_token || response.data.token;
      
      if (!access_token) {
        throw new Error('No token received from server');
      }
      
      // Store token in localStorage
      localStorage.setItem('token', access_token);
      
      // Set auth headers but use the api service's axios instance
      api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
      
      setIsAuthenticated(true);
      
      // Get user data using the same api instance
      try {
        await fetchUserData();
      } catch (userError) {
        console.warn('Could not fetch user data, but login successful', userError);
      }
    } catch (error) {
      console.error('Login error:', error);
      throw error;
    }
  };

  const register = async (email: string, password: string) => {
    try {
      // Import api from services to ensure we use the backend URL, not Vercel
      const api = (await import('../services/api')).default;
      
      // Log the base URL being used for debugging
      console.log('Using API base URL for registration:', api.defaults.baseURL);
      
      try {
        // Try first with the debug register endpoint which we added
        await api.post('/api/auth/debug-register', {
          email,
          password,
        });
        console.log('Debug registration successful');
      } catch (debugError) {
        // If debug endpoint isn't available (404), fall back to regular endpoint
        console.log('Debug endpoint not available, trying regular endpoint...');
        await api.post('/api/auth/register', {
          email,
          password,
        });
        console.log('Standard registration successful');
      }
      
      console.log('Registration successful, attempting login...');
      
      // Auto login after registration
      await login(email, password);
    } catch (error) {
      console.error('Registration error:', error);
      throw error;
    }
  };

  const logout = () => {
    console.log('Logging out user');
    // Clear token from localStorage
    localStorage.removeItem('token');
    
    // Clear all auth headers to be safe
    delete axios.defaults.headers.common['Authorization'];
    
    // Also clear authorization from the API service
    import('../services/api').then(module => {
      const api = module.default;
      delete api.defaults.headers.common['Authorization'];
      console.log('Cleared auth headers from API service');
    }).catch(err => {
      console.error('Error clearing API auth headers:', err);
    });
    
    // Reset authentication state
    setIsAuthenticated(false);
    setUser(null);
    
    console.log('Logout complete, auth state reset');
  };

  return (
    <AuthContext.Provider value={{
      isAuthenticated,
      user,
      loading,
      login,
      register,
      logout,
    }}>
      {children}
    </AuthContext.Provider>
  );
};

export default AuthContext;
