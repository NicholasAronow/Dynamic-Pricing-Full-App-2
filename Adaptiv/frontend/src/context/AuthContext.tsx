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
    // Check if there's a token in localStorage
    const token = localStorage.getItem('token');
    if (token) {
      try {
        // Verify token expiration
        const decoded: any = jwt_decode(token);
        const currentTime = Date.now() / 1000;
        
        if (decoded.exp > currentTime) {
          // Set auth headers for all future requests
          axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
          setIsAuthenticated(true);
          
          // Get user data
          fetchUserData();
        } else {
          // Token expired
          localStorage.removeItem('token');
          delete axios.defaults.headers.common['Authorization'];
        }
      } catch (error) {
        localStorage.removeItem('token');
        delete axios.defaults.headers.common['Authorization'];
      }
    }
    setLoading(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchUserData = async () => {
    try {
      const response = await axios.get('/api/auth/me');
      setUser(response.data);
    } catch (error) {
      console.error('Error fetching user data:', error);
      logout();
    }
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
    // Clear token from localStorage
    localStorage.removeItem('token');
    
    // Remove auth header
    delete axios.defaults.headers.common['Authorization'];
    
    setIsAuthenticated(false);
    setUser(null);
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
