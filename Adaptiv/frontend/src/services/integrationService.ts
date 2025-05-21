import api from './api';

/**
 * Service for handling POS and other third-party integrations
 */
export class IntegrationService {
  /**
   * Get the Square authorization URL to start the OAuth flow
   */
  async getSquareAuthUrl() {
    try {
      const response = await api.get('/api/integrations/square/auth');
      return response.data.auth_url;
    } catch (error) {
      console.error('Error getting Square auth URL:', error);
      throw error;
    }
  }

  /**
   * Process the Square OAuth callback by sending the code to the backend
   */
  async processSquareCallback(code: string, state: string) {
    try {
      const response = await api.post('/api/integrations/square/process-callback', {
        code,
        state
      });
      return response.data;
    } catch (error) {
      console.error('Error processing Square callback:', error);
      throw error;
    }
  }

  /**
   * Get orders from the connected Square account
   */
  async getSquareOrders() {
    try {
      const response = await api.get('/api/integrations/square/orders');
      return response.data;
    } catch (error) {
      console.error('Error getting Square orders:', error);
      throw error;
    }
  }

  /**
   * Sync data from Square to the local database
   */
  async syncSquareData() {
    try {
      const response = await api.post('/api/integrations/square/sync');
      return response.data;
    } catch (error) {
      console.error('Error syncing Square data:', error);
      throw error;
    }
  }
}

// Create a singleton instance
export const integrationService = new IntegrationService();
