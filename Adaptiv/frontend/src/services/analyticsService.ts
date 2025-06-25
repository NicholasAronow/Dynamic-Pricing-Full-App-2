import api from './api';
import { Item } from './itemService';
import authService from './authService';
import moment from 'moment';

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
  itemId?: number; // Alternative id format sometimes used in API
  name: string;
  quantity: number;
  revenue: number;
  unitPrice?: number;
  unitCost?: number;
  totalCost?: number;
  hasCost?: boolean;
  marginPercentage?: number;
}

export interface DailySales {
  date: string;
  revenue: number;
  orders: number;
  orderCount?: number; // Alternative name for orders used in some API responses
  totalCost?: number; // Cost data for margin calculations
  profitMargin?: number; // Pre-calculated profit margin
  formattedDate?: string; // Pre-formatted date string for display
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
  isCurrentPrice?: boolean;
}

export interface ElasticityCalculationData {
  price_changes_count: number;
  required_changes: number;
  has_enough_data: boolean;
  elasticity: number | null;
  price_change_data: Array<{
    date: string;
    previous_price: number;
    new_price: number;
    sales_before: number;
    sales_after: number;
    has_sales_data: boolean;
  }>;
}

export const analyticsService = {
  // Market boundary information for current item
  marketBoundaries: {
    marketLow: 0,
    marketHigh: 0
  },
  
  // Get elasticity calculation data for a specific item
  getElasticityCalculation: async (itemId: number): Promise<ElasticityCalculationData> => {
    try {
      const currentUser = authService.getCurrentUser();
      if (!currentUser) {
        console.error('User not authenticated');
        throw new Error('User not authenticated');
      }
      
      const response = await api.get(`item-analytics/elasticity/${itemId}`);
      return response.data;
    } catch (error) {
      console.error('Error getting elasticity calculation data:', error);
      // Return default empty data structure
      return {
        price_changes_count: 0,
        required_changes: 5,
        has_enough_data: false,
        elasticity: null,
        price_change_data: []
      };
    }
  },
  // Get sales data for dashboard - optimized for all timeframes
  getSalesAnalytics: async (startDate?: string, endDate?: string, timeFrame?: string, includeItemDetails: boolean = false): Promise<SalesAnalytics> => {
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
      
      // Add timeFrame parameter to let backend optimize aggregation
      if (timeFrame) {
        queryParams += `&time_frame=${timeFrame}`;
      }
      
      // Flag to include detailed item performance data
      if (includeItemDetails) {
        queryParams += `&include_item_details=true`;
      }

      // Use our endpoint with the enhanced parameters
      const response = await api.get(`dashboard/sales-data?${queryParams}`);
      
      // Process the response to ensure it's in the expected format with properly formatted dates
      const result = response.data;
      
      // Add any missing properties needed by the frontend
      if (result.salesByDay && result.salesByDay.length > 0) {
        result.salesByDay = result.salesByDay.map((day: DailySales) => {
          // Ensure profit margin is calculated if not provided
          if (day.profitMargin === undefined && day.revenue > 0 && day.totalCost && day.totalCost > 0) {
            day.profitMargin = ((day.revenue - day.totalCost) / day.revenue) * 100;
          }
          
          // Format dates based on timeFrame if not already formatted
          if (!day.formattedDate && timeFrame) {
            if (timeFrame === '1d') {
              day.formattedDate = moment(day.date).format('HH:00');
            } else if (timeFrame === '7d' || timeFrame === '1m') {
              day.formattedDate = moment(day.date).format('MMM DD');
            } else {
              day.formattedDate = moment(day.date).format('MMM');
            }
          }
          
          return day;
        });
      }
      
      return result;
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
      
      // Store market boundaries for use in other functions
      if (response.data && response.data.marketStats) {
        analyticsService.marketBoundaries = {
          marketLow: response.data.marketStats.low || 0,
          marketHigh: response.data.marketStats.high || 0
        };
      }
      
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
      
      // Fetch elasticity calculation to get the actual elasticity value
      const elasticityCalc = await analyticsService.getElasticityCalculation(itemId);
      
      // Get the base price from elasticity calculation or price history
      const priceHistoryResponse = await api.get(`price-history?item_id=${itemId}&account_id=${currentUser.id}`);
      const priceHistory = priceHistoryResponse.data;
      
      // Get the item to find the current price
      const itemResponse = await api.get(`items/${itemId}?account_id=${currentUser.id}`);
      const item = itemResponse.data;
      const currentPrice = item.current_price;
      
      // Get a reasonable base price from price history or current price
      const basePrice = priceHistory.length > 0 ? priceHistory[0].new_price : currentPrice || 10.0;
      
      // Cap the base sales volume to a reasonable value (10-1000 units depending on price)
      // For more expensive items, typical sales volumes are lower
      const MAX_BASE_VOLUME = 1000;
      const MAX_REVENUE = 50000; // Cap maximum revenue to prevent unrealistic numbers
      const baseSalesVolume = Math.min(Math.max(10, 5000 / Math.max(1, basePrice)), MAX_BASE_VOLUME);
      
      // Use the calculated elasticity or a default value, with reasonable bounds
      let elasticity = elasticityCalc.elasticity !== null ? elasticityCalc.elasticity : -1.5;
      
      // Bound elasticity to reasonable values (-0.1 to -3.0)
      // Most real-world price elasticities are between -0.5 and -2.0
      if (elasticity < -3.0) elasticity = -3.0; // Cap extremely elastic products
      if (elasticity > -0.1) elasticity = -0.1; // Cap extremely inelastic products
      
      // Set a price range centered around current price with a ±100% range
      const pricePoints = 15; // More points for a smoother curve
      
      // Always center around current price with ±100% range (minimum of 0)
      const minPrice = Math.max(0, currentPrice - currentPrice); // Equivalent to 0 but more explicit
      const maxPrice = currentPrice + currentPrice; // 2x current price
      
      console.log('Using current price centered range for elasticity chart:', minPrice, maxPrice);
      
      const elasticityData: PriceElasticityData[] = [];
      
      // Generate a smooth curve of price elasticity data
      for (let i = 0; i < pricePoints; i++) {
        // Generate price points from min to max price (evenly distributed)
        const price = minPrice + (i / (pricePoints - 1)) * (maxPrice - minPrice);
        
        // Calculate sales volume using the elasticity formula with bounded output
        // Q2 = Q1 * (P2/P1)^elasticity
        // For example, if elasticity is -1.5:
        // - 10% price increase → ~15% sales volume decrease
        // - 10% price decrease → ~15% sales volume increase
        const priceRatio = price / basePrice; // Calculate the price ratio from absolute prices
        let salesVolume = baseSalesVolume * Math.pow(priceRatio, elasticity);
        
        // Cap the maximum possible sales increase/decrease to prevent unrealistic values
        // No matter how elastic, volume shouldn't increase/decrease by more than 3x from base
        const MAX_VOLUME_RATIO = 3.0;
        if (salesVolume > baseSalesVolume * MAX_VOLUME_RATIO) {
          salesVolume = baseSalesVolume * MAX_VOLUME_RATIO;
        }
        
        // Ensure sales volume is positive and not unrealistically large
        const MAX_POSSIBLE_VOLUME = 10000; // Cap to prevent unrealistic numbers
        const adjustedSalesVolume = Math.min(Math.max(salesVolume, 0), MAX_POSSIBLE_VOLUME);
        
        // Calculate revenue as price × sales volume and cap it to prevent unrealistic values
        let revenue = price * adjustedSalesVolume;
        revenue = Math.min(revenue, MAX_REVENUE); // Cap revenue to prevent wildly unrealistic values
        
        // Check if this price point is close to the current price (within 1%)
        const isCurrentPrice = Math.abs(price - currentPrice) / currentPrice < 0.01;
        
        elasticityData.push({
          price,
          sales_volume: adjustedSalesVolume,
          revenue: revenue,
          isCurrentPrice: isCurrentPrice
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

// Helper function to get date range from time frame
const getDateRangeFromTimeFrame = (timeFrame: string) => {
  const end = moment().endOf('day');
  let start;
  
  switch (timeFrame) {
    case '1d':
      start = moment().subtract(1, 'day').startOf('day');
      break;
    case '7d':
      start = moment().subtract(6, 'days').startOf('day');
      break;
    case '1m':
      start = moment().subtract(30, 'days').startOf('day');
      break;
    case '6m':
      start = moment().subtract(180, 'days').startOf('day');
      break;
    case '1yr':
      start = moment().subtract(365, 'days').startOf('day');
      break;
    default:
      start = moment().subtract(30, 'days').startOf('day');
  }
  
  return {
    startDate: start.format('YYYY-MM-DD'),
    endDate: end.format('YYYY-MM-DD')
  };
};

export default analyticsService;
