import api from './api';
import authService from './authService';

export interface Item {
  id: number;
  name: string;
  description: string;
  category: string;
  current_price: number;
  cost: number;
  created_at: string;
  updated_at: string;
  // Additional fields that might be needed for the UI
  image?: string;
  margin?: number;
  weeklyUnits?: number;
}

export interface ItemCreate {
  name: string;
  description: string;
  category: string;
  current_price: number;
  cost: number;
}

export interface PriceHistory {
  id: number;
  item_id: number;
  old_price: number;
  new_price: number;
  change_date: string;
  reason?: string;
}

export const itemService = {
  getItems: async (): Promise<Item[]> => {
    try {
      // Add account_id filter parameter to only fetch items belonging to current user
      const currentUser = authService.getCurrentUser();
      if (!currentUser) {
        console.error('User not authenticated');
        return [];
      }
      
      const response = await api.get(`items?account_id=${currentUser.id}`);
      return response.data;
    } catch (error) {
      console.error('Error fetching items:', error);
      throw error;
    }
  },
  
  getPriceHistory: async (itemId: number): Promise<PriceHistory[]> => {
    try {
      const currentUser = authService.getCurrentUser();
      if (!currentUser) {
        console.error('User not authenticated');
        return [];
      }
      
      try {
        // First try with user_id which seems to be expected in production
        // Adding trailing slash to prevent 307 redirects
        const response = await api.get(`price-history/?item_id=${itemId}&user_id=${currentUser.id}`);
        return response.data;
      } catch (userIdError) {
        console.error(`Error with user_id parameter, trying fallback with account_id:`, userIdError);
        
        // If user_id fails, try with account_id as fallback (for local development)
        const response = await api.get(`price-history/?item_id=${itemId}&account_id=${currentUser.id}`);
        return response.data;
      }
    } catch (error) {
      console.error(`Error fetching price history for item ${itemId}:`, error);
      return [];
    }
  },

  getPriceHistoryBatch: async (itemIds: number[]): Promise<{[itemId: number]: any[]}> => {
    if (!itemIds.length) return {};
    
    try {
      // Join item IDs with commas for the request
      const itemIdsParam = itemIds.join(',');
      console.log(`Fetching price history in batch for ${itemIds.length} items`);
      
      // First try with user_id
      try {
        const response = await api.get(`price-history/?item_ids=${itemIdsParam}&user_id=${authService.getCurrentUser()?.id}`);
        
        // Group results by item_id
        const grouped = response.data.reduce((acc: {[key: number]: any[]}, item: any) => {
          if (!acc[item.item_id]) {
            acc[item.item_id] = [];
          }
          acc[item.item_id].push(item);
          return acc;
        }, {});
        
        // Add empty arrays for any items that didn't have price history
        itemIds.forEach(id => {
          if (!grouped[id]) {
            grouped[id] = [];
          }
        });
        
        return grouped;
      } catch (error) {
        console.log('Error with user_id batch request, trying with account_id', error);
        // Fall back to account_id
        const response = await api.get(`price-history/?item_ids=${itemIdsParam}&account_id=${authService.getCurrentUser()?.id}`);
        
        // Group results by item_id
        const grouped = response.data.reduce((acc: {[key: number]: any[]}, item: any) => {
          if (!acc[item.item_id]) {
            acc[item.item_id] = [];
          }
          acc[item.item_id].push(item);
          return acc;
        }, {});
        
        // Add empty arrays for any items that didn't have price history
        itemIds.forEach(id => {
          if (!grouped[id]) {
            grouped[id] = [];
          }
        });
        
        return grouped;
      }
    } catch (error) {
      console.error('Failed to fetch batch price history:', error);
      // Return empty arrays for each item ID
      return itemIds.reduce((acc: {[key: number]: any[]}, id) => {
        acc[id] = [];
        return acc;
      }, {});
    }
  },

  getItem: async (id: number): Promise<Item> => {
    try {
      const currentUser = authService.getCurrentUser();
      if (!currentUser) {
        console.error('User not authenticated');
        throw new Error('User not authenticated');
      }
      
      // The backend should verify the item belongs to the current user
      const response = await api.get(`items/${id}?account_id=${currentUser.id}`);
      return response.data;
    } catch (error) {
      console.error(`Error fetching item ${id}:`, error);
      throw error;
    }
  },

  createItem: async (item: ItemCreate): Promise<Item> => {
    try {
      const currentUser = authService.getCurrentUser();
      if (!currentUser) {
        console.error('User not authenticated');
        throw new Error('User not authenticated');
      }
      
      // Add the account_id to the item data when creating
      const itemWithAccount = {
        ...item,
        account_id: currentUser.id
      };
      
      const response = await api.post('items', itemWithAccount);
      return response.data;
    } catch (error) {
      console.error('Error creating item:', error);
      throw error;
    }
  },

  updateItem: async (id: number, item: Partial<ItemCreate>): Promise<Item> => {
    try {
      const currentUser = authService.getCurrentUser();
      if (!currentUser) {
        console.error('User not authenticated');
        throw new Error('User not authenticated');
      }
      
      // The backend should verify the item belongs to the current user
      // but we'll also add the account_id as a query parameter for extra security
      const response = await api.put(`items/${id}?account_id=${currentUser.id}`, item);
      return response.data;
    } catch (error) {
      console.error(`Error updating item ${id}:`, error);
      throw error;
    }
  },

  deleteItem: async (id: number): Promise<void> => {
    try {
      const currentUser = authService.getCurrentUser();
      if (!currentUser) {
        console.error('User not authenticated');
        throw new Error('User not authenticated');
      }
      
      // The backend should verify the item belongs to the current user
      await api.delete(`items/${id}?account_id=${currentUser.id}`);
    } catch (error) {
      console.error(`Error deleting item ${id}:`, error);
      throw error;
    }
  }
};

export default itemService;
