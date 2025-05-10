import api from './api';

export interface Order {
  id: number;
  order_date: string;
  total_amount: number;
  items: OrderItem[];
  created_at: string;
}

export interface OrderItem {
  id: number;
  order_id: number;
  item_id: number;
  item_name: string;
  quantity: number;
  unit_price: number;
  subtotal: number;
}

export interface OrderCreate {
  order_date: string;
  total_amount: number;
  items: Omit<OrderItem, 'id' | 'order_id'>[];
}

export const orderService = {
  getOrders: async (): Promise<Order[]> => {
    const response = await api.get('/orders');
    return response.data;
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

  // Get orders by date range
  getOrdersByDateRange: async (startDate: string, endDate: string): Promise<Order[]> => {
    const response = await api.get(`/orders/range?start_date=${startDate}&end_date=${endDate}`);
    return response.data;
  }
};

export default orderService;
