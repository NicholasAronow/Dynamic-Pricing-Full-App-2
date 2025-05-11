import api from './api';
import { Item } from './itemService';
import { Order } from './orderService';
import authService from './authService';

export interface CompetitorData {
  item: {
    id: number;
    name: string;
    category: string;
    price: number;
  };
  marketStats: {
    low: number;
    high: number;
    average: number;
    averagePosition: number;
  };
  ourPosition: number;
  competitors: {
    id: number;
    name: string;
    item_name: string;
    price: number;
    difference: number;
    percentageDiff: number;
    position: number;
    normalizedPosition: number;
    updated_at: string;
  }[];
}

export interface SalesAnalytics {
  totalSales: number;
  totalOrders: number;
  averageOrderValue: number;
  topSellingItems: TopSellingItem[];
  salesByDay: DailySales[];
  salesByCategory: CategorySales[];
}

export interface TopSellingItem {
  id: number;
  name: string;
  quantity: number;
  revenue: number;
}

export interface DailySales {
  date: string;
  revenue: number;
  orders: number;
}

export interface CategorySales {
  category: string;
  revenue: number;
  itemCount: number;
}

export interface PriceElasticityData {
  price: number;
  sales_volume: number;
  revenue: number;
}

export const analyticsService = {
  // Get sales data for dashboard
  getSalesAnalytics: async (startDate?: string, endDate?: string): Promise<SalesAnalytics> => {
    try {
      const currentUser = authService.getCurrentUser();
      if (!currentUser) {
        console.error('User not authenticated');
        throw new Error('User not authenticated');
      }

      // Add account_id to filter data by user's account
      let queryParams = `account_id=${currentUser.id}`;
      if (startDate && endDate) {
        queryParams += `&start_date=${startDate}&end_date=${endDate}`;
      }

      // Use our new dashboard endpoint which returns data in the exact format we need
      const response = await api.get(`dashboard/sales-data?${queryParams}`);
      
      // The data is already in the correct format for the frontend
      return response.data;
    } catch (error) {
      console.error('Error fetching sales analytics:', error);
      // Return default structure with zeros if API fails
      return {
        totalSales: 0,
        totalOrders: 0,
        averageOrderValue: 0,
        topSellingItems: [],
        salesByDay: [],
        salesByCategory: []
      };
    }
  },
  
  // Get item performance data
  getItemPerformance: async (timeFrame?: string): Promise<any[]> => {
    try {
      const currentUser = authService.getCurrentUser();
      if (!currentUser) {
        console.error('User not authenticated');
        throw new Error('User not authenticated');
      }

      // Add account_id to filter data by user's account
      let queryParams = `account_id=${currentUser.id}`;
      if (timeFrame) {
        queryParams += `&time_frame=${timeFrame}`;
      }

      // Use the new dashboard/product-performance endpoint with account_id and time frame parameter
      const response = await api.get(`dashboard/product-performance?${queryParams}`);
      return response.data;
    } catch (error) {
      console.error('Error fetching item performance:', error);
      
      // Fallback to the old approach if the new endpoint fails
      try {
        const currentUser = authService.getCurrentUser();
        if (!currentUser) {
          console.error('User not authenticated');
          return [];
        }
        
        // Fetch all items as a backup, filtered by account
        const itemsResponse = await api.get(`items?account_id=${currentUser.id}`);
        const items = itemsResponse.data;
        
        return items.map((item: Item) => ({
          id: item.id,
          name: item.name,
          category: item.category,
          currentPrice: item.current_price,
          cost: item.cost || item.current_price * 0.6,
          revenue: 0, // Fallback to zero
          margin: 0, // Fallback to zero
          volumeTrend: Math.random() > 0.5 ? 'up' : 'down',
          marginTrend: Math.random() > 0.5 ? 'up' : 'down'
        }));
      } catch (fallbackError) {
        console.error('Fallback also failed:', fallbackError);
        return [];
      }
    }
  },
  
  // Get competitor data for a specific menu item
  getCompetitorData: async (itemId: number): Promise<CompetitorData | null> => {
    try {
      const response = await api.get(`competitor-items/similar-to/${itemId}`);
      return response.data;
    } catch (error) {
      console.error('Error fetching competitor data:', error);
      return null;
    }
  },
  
  // Get price elasticity data for a specific product
  getPriceElasticity: async (itemId: number): Promise<PriceElasticityData[]> => {
    try {
      const currentUser = authService.getCurrentUser();
      if (!currentUser) {
        console.error('User not authenticated');
        throw new Error('User not authenticated');
      }

      // This would call a specialized endpoint in a real implementation
      // For now, we'll generate simulated data based on price history
      // Include account_id to ensure we're only getting price history for the current user's items
      const priceHistoryResponse = await api.get(`price-history?item_id=${itemId}&account_id=${currentUser.id}`);
      const priceHistory = priceHistoryResponse.data;
      
      // Use price history to generate elasticity data points 
      // In a real system, this would be calculated from actual sales data
      const basePrice = priceHistory.length > 0 
        ? priceHistory[0].new_price 
        : 10.0;
      
      const maxVariation = 2.0; // Maximum price variation in either direction
      const numberOfPoints = 7; // Number of data points to generate
      
      const step = (maxVariation * 2) / (numberOfPoints - 1);
      
      const elasticityData: PriceElasticityData[] = [];
      
      // Generate price elasticity data points
      for (let i = 0; i < numberOfPoints; i++) {
        const priceMultiplier = 1 - maxVariation + (step * i);
        const price = basePrice * priceMultiplier;
        
        // Elasticity curve formula (simplified for simulation)
        // Higher demand at lower prices, with diminishing returns
        const salesVolume = basePrice / price * (Math.random() * 0.2 + 0.9) * 100;
        
        elasticityData.push({
          price,
          sales_volume: salesVolume,
          revenue: price * salesVolume
        });
      }
      
      return elasticityData;
    } catch (error) {
      console.error('Error getting price elasticity data:', error);
      return [];
    }
  },
  
  // Get real sales data for a specific item over time
  getItemSalesData: async (itemId: number, timeFrame: string): Promise<any[]> => {
    try {
      const currentUser = authService.getCurrentUser();
      if (!currentUser) {
        console.error('User not authenticated');
        throw new Error('User not authenticated');
      }

      const response = await api.get(`item-analytics/sales/${itemId}`, {
        params: { 
          time_frame: timeFrame,
          account_id: currentUser.id
        }
      });
      return response.data;
    } catch (error) {
      console.error('Error fetching item sales data:', error);
      return [];
    }
  },
  
  // Get real hourly sales data for a specific item
  getItemHourlySales: async (itemId: number, date?: string): Promise<any[]> => {
    try {
      const currentUser = authService.getCurrentUser();
      if (!currentUser) {
        console.error('User not authenticated');
        throw new Error('User not authenticated');
      }

      const params: any = {
        account_id: currentUser.id
      };
      if (date) {
        params.date = date;
      }
      
      const response = await api.get(`item-analytics/hourly-sales/${itemId}`, { params });
      return response.data;
    } catch (error) {
      console.error('Error fetching item hourly sales data:', error);
      return [];
    }
  },
  
  // Get weekly sales data by day of week for a specific item
  getItemWeeklySales: async (itemId: number): Promise<any[]> => {
    try {
      const response = await api.get(`item-analytics/weekly-sales/${itemId}`);
      return response.data;
    } catch (error) {
      console.error('Error fetching item weekly sales data:', error);
      return [];
    }
  },
  
  // Get forecast data for a specific item
  getItemForecast: async (itemId: number): Promise<any> => {
    try {
      const response = await api.get(`item-analytics/forecast/${itemId}`);
      return response.data;
    } catch (error) {
      console.error('Error fetching item forecast data:', error);
      return {
        monthlyData: [],
        metrics: {
          nextMonthForecast: 0,
          growthRate: 0,
          forecastAccuracy: 0
        }
      };
    }
  }
};

export default analyticsService;
