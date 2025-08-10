import moment from 'moment';
import api from './api';
import authService from './authService';

export interface Order {
  id: number;
  order_date: string;
  total_amount: number;
  items: OrderItem[];
  created_at: string;
  total_cost?: number;
  gross_margin?: number;
  net_margin?: number;
}

export interface OrderItem {
  id: number;
  order_id: number;
  item_id: number;
  item_name: string;
  quantity: number;
  unit_price: number;
  subtotal: number;
  unit_cost?: number;
  subtotal_cost?: number;
}

export interface OrderCreate {
  order_date: string;
  total_amount: number;
  items: Omit<OrderItem, 'id' | 'order_id'>[];
}

export const orderService = {
  getOrders: async (limit?: number, skip?: number): Promise<Order[]> => {
    try {
      const params: any = {};
      if (limit !== undefined) params.limit = limit;
      if (skip !== undefined) params.skip = skip;
      
      const response = await api.get('/orders/', { params });
      return response.data || [];
    } catch (error) {
      console.error('Error fetching orders:', error);
      return [];
    }
  },

  getOrder: async (id: number): Promise<Order> => {
    const response = await api.get(`/orders/${id}`);
    return response.data;
  },

  createOrder: async (order: OrderCreate): Promise<Order> => {
    const response = await api.post('/orders', order);
    return response.data;
  },

  // Get analytics on order history
  getOrderAnalytics: async (startDate?: string, endDate?: string): Promise<any> => {
    let url = '/orders/analytics';
    if (startDate && endDate) {
      url += `?start_date=${startDate}&end_date=${endDate}`;
    }
    const response = await api.get(url);
    return response.data;
  },
  
  // Check if user has ever had any orders (used to determine if POS is connected)
  checkHasEverHadOrders: async (): Promise<boolean> => {
    try {
      const currentUser = authService.getCurrentUser();
      if (!currentUser) {
        console.error('User not authenticated');
        return false;
      }
      
      try {
        // First try with user_id which seems to be expected in production
        const response = await api.get(`/orders/has-orders?user_id=${currentUser.id}`);
        return response.data.has_orders === true;
      } catch (userIdError) {
        console.error(`Error with user_id parameter, trying fallback with account_id:`, userIdError);
        
        // Call a lightweight endpoint to check if user has any orders with account_id
        const response = await api.get(`/orders/has-orders?account_id=${currentUser.id}`);
        return response.data.has_orders === true;
      }
    } catch (error) {
      console.error('Error checking if user has orders:', error);
      // For test accounts, fail gracefully and assume they have orders
      // This helps ensure the POS prompt doesn't show incorrectly
      const currentUser = authService.getCurrentUser();
      if (currentUser?.email?.includes('test')) {
        console.log('Test account detected, assuming orders exist');
        return true;
      }
      return false;
    }
  },

  // Get orders by date range
  getOrdersByDateRange: async (startDate: string, endDate: string): Promise<Order[]> => {
    try {
      const currentUser = authService.getCurrentUser();
      if (!currentUser) {
        console.error('User not authenticated');
        return [];
      }
      
      console.log('Requesting orders with dates:', { startDate, endDate });

      const isoStartDate = `${startDate}T00:00:00`;
      const isoEndDate = `${endDate}T23:59:59`;
      
      console.log('Requesting orders with ISO dates:', { 
        start_date: isoStartDate, 
        end_date: isoEndDate 
      });
      
        const response = await api.get('/orders/range', {
          params: {
            start_date: isoStartDate,
            end_date: isoEndDate
          }
        });
      
      
      console.log(`Fetched ${response.data.length} orders for date range ${startDate} to ${endDate}`);
      return response.data || [];
    } catch (error: any) {
      console.error('Error fetching orders by date range:', error);
      console.error('Error response:', error.response?.data);
      return [];
    }
  },
  
  // Helper method to process sync response (defined first so we can use it in syncSquareOrders)
  processOrderSyncResponse: (response: any): {success: boolean, message: string, total_orders?: number} => {
    // Extract order count if available in response
    const totalOrders = response.data?.total_orders || 
                      response.data?.orders_count || 
                      (response.data?.orders ? response.data.orders.length : undefined) ||
                      undefined;
                      
    return { 
      success: true, 
      message: response.data?.message || 'Orders synchronized successfully',
      total_orders: totalOrders
    };
  },

  // Start Square sync as background task
  syncSquareOrders: async (force_sync: boolean = false): Promise<{success: boolean, message: string, task_id?: string}> => {
    try {
      const currentUser = authService.getCurrentUser();
      if (!currentUser) {
        console.error('User not authenticated');
        return { success: false, message: 'User not authenticated' };
      }
      
      // Start the background sync task
      const response = await api.post('/integrations/square/sync', {
        force_sync: force_sync
      });
      
      if (response.data.success) {
        return {
          success: true,
          message: response.data.message || 'Square sync started in background',
          task_id: response.data.task_id
        };
      } else {
        return {
          success: false,
          message: response.data.error || 'Failed to start sync'
        };
      }
    } catch (error: any) {
      console.error('Error starting Square sync:', error);
      return { 
        success: false, 
        message: error.response?.data?.detail || 'Failed to start sync. Please try again.'
      };
    }
  },

  // Check status of Square sync background task
  getSquareSyncStatus: async (task_id: string): Promise<{success: boolean, status: string, progress?: number, result?: any, error?: string}> => {
    try {
      const response = await api.get(`/integrations/square/sync/status/${task_id}`);
      
      return {
        success: true,
        status: response.data.task_status,
        progress: response.data.progress,
        result: response.data.result,
        error: response.data.error
      };
    } catch (error: any) {
      console.error('Error getting sync status:', error);
      return {
        success: false,
        status: 'ERROR',
        error: error.response?.data?.detail || 'Failed to get sync status'
      };
    }
  },

  // Get current user's persistent Square sync metadata (active sync status)
  getCurrentSquarePersistentSyncStatus: async (): Promise<{success: boolean, data?: any, error?: string}> => {
    try {
      const response = await api.get('/integrations/square/sync/status/current');
      // Backend shape: { success: true, data: meta }
      const data = response.data?.data ?? response.data;
      return { success: true, data };
    } catch (error: any) {
      // 404 if integration not found, or 500. Treat as not active.
      console.error('Error fetching current Square sync metadata:', error);
      return { success: false, error: error.response?.data?.detail || 'Failed to fetch sync metadata' };
    }
  },

  // Poll sync status until completion
  pollSquareSyncStatus: async (task_id: string, onProgress?: (progress: number, status: string) => void): Promise<{success: boolean, result?: any, error?: string}> => {
    const maxAttempts = 60; // 5 minutes with 5-second intervals
    let attempts = 0;
    
    while (attempts < maxAttempts) {
      const statusResponse = await orderService.getSquareSyncStatus(task_id);
      
      if (!statusResponse.success) {
        return { success: false, error: statusResponse.error };
      }
      
      // Update progress if callback provided
      if (onProgress && statusResponse.progress !== undefined) {
        onProgress(statusResponse.progress, statusResponse.status);
      }
      
      // Check if task is completed
      if (statusResponse.status === 'COMPLETED') {
        return { success: true, result: statusResponse.result };
      } else if (statusResponse.status === 'ERROR') {
        return { success: false, error: statusResponse.error || 'Sync task failed' };
      }
      
      // Wait 5 seconds before next check
      await new Promise(resolve => setTimeout(resolve, 5000));
      attempts++;
    }
    
    return { success: false, error: 'Sync task timed out' };
  },

  // Legacy method for backward compatibility - now uses background task
  syncSquareOrdersLegacy: async (): Promise<{success: boolean, message: string, total_orders?: number}> => {
    try {
      // Start sync
      const syncStart = await orderService.syncSquareOrders(false);
      if (!syncStart.success || !syncStart.task_id) {
        return { success: false, message: syncStart.message };
      }
      
      // Poll for completion
      const result = await orderService.pollSquareSyncStatus(syncStart.task_id);
      
      if (result.success && result.result) {
        return {
          success: true,
          message: `Sync completed! Created ${result.result.orders_created} orders, updated ${result.result.orders_updated} orders`,
          total_orders: (result.result.orders_created || 0) + (result.result.orders_updated || 0)
        };
      } else {
        return {
          success: false,
          message: result.error || 'Sync failed'
        };
      }
    } catch (error: any) {
      console.error('Error in legacy sync:', error);
      return { 
        success: false, 
        message: 'Failed to sync orders. Please try again.'
      };
    }
  }
};

export default orderService;
