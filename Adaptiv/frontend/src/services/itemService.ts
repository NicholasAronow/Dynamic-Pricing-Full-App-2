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
      
      // Add account_id filter to ensure we only get price history for items the user owns
      const response = await api.get(`price-history?item_id=${itemId}&account_id=${currentUser.id}`);
      return response.data;
    } catch (error) {
      console.error(`Error fetching price history for item ${itemId}:`, error);
      return [];
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
