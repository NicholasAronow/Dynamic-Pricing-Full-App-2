import api from './api';

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
      const response = await api.get('items');
      return response.data;
    } catch (error) {
      console.error('Error fetching items:', error);
      throw error;
    }
  },
  
  getPriceHistory: async (itemId: number): Promise<PriceHistory[]> => {
    try {
      const response = await api.get(`price-history?item_id=${itemId}`);
      return response.data;
    } catch (error) {
      console.error(`Error fetching price history for item ${itemId}:`, error);
      return [];
    }
  },

  getItem: async (id: number): Promise<Item> => {
    const response = await api.get(`items/${id}`);
    return response.data;
  },

  createItem: async (item: ItemCreate): Promise<Item> => {
    const response = await api.post('items', item);
    return response.data;
  },

  updateItem: async (id: number, item: Partial<ItemCreate>): Promise<Item> => {
    const response = await api.put(`items/${id}`, item);
    return response.data;
  },

  deleteItem: async (id: number): Promise<void> => {
    await api.delete(`items/${id}`);
  }
};

export default itemService;
