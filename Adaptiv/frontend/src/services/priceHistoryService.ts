import api from './api';

export interface PriceHistory {
  id: number;
  item_id: number;
  previous_price: number;
  new_price: number;
  change_reason: string;
  changed_at: string;
}

export interface PriceHistoryCreate {
  item_id: number;
  previous_price: number;
  new_price: number;
  change_reason: string;
}

export const priceHistoryService = {
  getPriceHistories: async (itemId?: number): Promise<PriceHistory[]> => {
    const url = itemId ? `/price-history?item_id=${itemId}` : '/price-history';
    const response = await api.get(url);
    return response.data;
  },

  getPriceHistory: async (id: number): Promise<PriceHistory> => {
    const response = await api.get(`/price-history/${id}`);
    return response.data;
  },

  createPriceHistory: async (priceHistory: PriceHistoryCreate): Promise<PriceHistory> => {
    const response = await api.post('/price-history', priceHistory);
    return response.data;
  },

  // Simulate price change - for testing without real Square integration
  simulatePriceChange: async (itemId: number, newPrice: number, reason: string): Promise<PriceHistory> => {
    const response = await api.post('/price-history/simulate', {
      item_id: itemId,
      new_price: newPrice,
      change_reason: reason
    });
    return response.data;
  }
};

export default priceHistoryService;
