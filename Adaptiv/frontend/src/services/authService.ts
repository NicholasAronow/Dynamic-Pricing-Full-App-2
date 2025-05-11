import api from './api';
import jwtDecode from 'jwt-decode';

interface User {
  id: number;
  email: string;
  business_name: string;
  role: string;
}

interface TokenPayload {
  sub: string; // Email address
  user_id: number; // User ID
  business_name?: string;
  role?: string;
  exp: number;
}

export const authService = {
  login: async (email: string, password: string): Promise<boolean> => {
    try {
      const response = await api.post('/api/auth/login', { email, password });
      const { token } = response.data;
      localStorage.setItem('token', token);
      return true;
    } catch (error) {
      console.error('Login error:', error);
      return false;
    }
  },

  logout: (): void => {
    localStorage.removeItem('token');
    window.location.href = '/login';
  },

  register: async (userData: any): Promise<boolean> => {
    try {
      const response = await api.post('/api/auth/register', userData);
      const { token } = response.data;
      localStorage.setItem('token', token);
      return true;
    } catch (error) {
      console.error('Register error:', error);
      return false;
    }
  },

  getCurrentUser: (): User | null => {
    const token = localStorage.getItem('token');
    if (!token) return null;
    
    try {
      const decoded = jwtDecode<TokenPayload>(token);
      // Check token expiration
      if (decoded.exp * 1000 < Date.now()) {
        authService.logout();
        return null;
      }
      
      return {
        id: decoded.user_id,
        email: decoded.sub, // sub contains the email
        business_name: decoded.business_name || '',
        role: decoded.role || 'user'
      };
    } catch (error) {
      console.error('Error decoding token:', error);
      return null;
    }
  },

  isAuthenticated: (): boolean => {
    return authService.getCurrentUser() !== null;
  }
};

export default authService;
