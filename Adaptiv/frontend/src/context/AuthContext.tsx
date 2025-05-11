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
      const response = await axios.post('/api/auth/token', new URLSearchParams({
        'username': email,
        'password': password,
      }), {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        }
      });
      
      const { access_token } = response.data;
      
      // Store token in localStorage
      localStorage.setItem('token', access_token);
      
      // Set auth headers
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
      
      setIsAuthenticated(true);
      
      // Get user data
      await fetchUserData();
    } catch (error) {
      console.error('Login error:', error);
      throw error;
    }
  };

  const register = async (email: string, password: string) => {
    try {
      // Import api from services to use the configured base URL
      const api = (await import('../services/api')).default;
      
      await api.post('auth/register', {
        email,
        password,
      });
      
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
