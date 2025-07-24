import api from './api';
import { Item } from './itemService';
import itemService, { PriceHistory } from './itemService';
import authService from './authService';

// New interface for agent-based pricing recommendations
export interface AgentPricingRecommendation {
  id: number;
  item_id: number;
  item_name: string;
  current_price: number;
  recommended_price: number;
  price_change_amount: number;
  price_change_percent: number;
  confidence_score: number;
  rationale: string;
  implementation_status: string;
  user_action: string | null;
  user_feedback: string | null;
  recommendation_date: string;
  reevaluation_date: string | null;
  batch_id: string;
}

export interface PriceRecommendation {
  id: number;
  name: string;
  category: string;
  currentPrice: number;
  previousPrice: number | null;
  lastPriceChangeDate?: string | null; // Can be string or null
  recommendedPrice?: number;
  percentChange?: number;
  quantity: number;
  revenue: number;
  growth: number;
  profitMargin: number;
  elasticity: string | null;
  optimizationReason: string | null;
  previousRevenue: number | null;
  incrementalRevenue: number | null;
  measuredRevenueChangePercent: number | null;
  projectedRevenue?: number;
  revenueChangePercent?: number;
  timeFrame: string;
  editing?: boolean;
}

// Track whether we're using mock data
let _usingMock = false;

// Frontend cache for performance optimization
interface CacheEntry {
  data: any;
  timestamp: number;
  ttl: number;
}

class FrontendCache {
  private cache = new Map<string, CacheEntry>();
  private readonly DEFAULT_TTL = 5 * 60 * 1000; // 5 minutes

  set(key: string, data: any, ttl: number = this.DEFAULT_TTL): void {
    this.cache.set(key, {
      data,
      timestamp: Date.now(),
      ttl
    });
  }

  get(key: string): any | null {
    const entry = this.cache.get(key);
    if (!entry) return null;
    
    if (Date.now() - entry.timestamp > entry.ttl) {
      this.cache.delete(key);
      return null;
    }
    
    return entry.data;
  }

  clear(): void {
    this.cache.clear();
  }

  generateKey(prefix: string, params: Record<string, any>): string {
    const sortedParams = Object.keys(params)
      .sort()
      .map(key => `${key}:${params[key]}`)
      .join('|');
    return `${prefix}:${sortedParams}`;
  }
}

const frontendCache = new FrontendCache();

export const pricingService = {
  // Get agent pricing recommendations from the database
  getAgentRecommendations: async (status?: string, batchId?: string): Promise<AgentPricingRecommendation[]> => {
    try {
      let params = '';
      if (status || batchId) {
        params = '?';
        if (status) params += `status=${status}`;
        if (status && batchId) params += '&';
        if (batchId) params += `batch_id=${batchId}`;
      }
      
      const response = await api.get(`pricing/recommendations${params}`);
      return response.data;
    } catch (error) {
      console.error('Error fetching agent pricing recommendations:', error);
      return [];
    }
  },

  // Accept or reject a pricing recommendation
  updateRecommendationAction: async (recommendationId: number, action: 'accept' | 'reject', feedback?: string): Promise<AgentPricingRecommendation | null> => {
    try {
      // Map frontend action terms to backend expected terms
      const mappedAction = action === 'accept' ? 'accept' : 'reject';
      
      const response = await api.put(`pricing/recommendations/${recommendationId}/action`, {
        action: mappedAction,
        feedback: feedback || ''
      });
      return response.data;
    } catch (error) {
      console.error('Error updating recommendation action:', error);
      return null;
    }
  },
  // Get available recommendation batches
  getAvailableBatches: async (): Promise<{batch_id: string, recommendation_date: string}[]> => {
    try {
      const response = await api.get('pricing/recommendation-batches');
      return response.data;
    } catch (error) {
      console.error('Error fetching recommendation batches:', error);
      return [];
    }
  },
  
  // Get price recommendations based on sales data and performance
  getPriceRecommendations: async (timeFrame: string = '1m'): Promise<PriceRecommendation[]> => {
    try {
      const currentUser = authService.getCurrentUser();
      if (!currentUser) {
        throw new Error('User not authenticated');
      }

      // OPTIMIZATION: Check cache first
      const cacheKey = frontendCache.generateKey('price_recommendations', {
        userId: currentUser.id,
        timeFrame
      });
      const cachedResult = frontendCache.get(cacheKey);
      if (cachedResult) {
        console.log('Returning cached price recommendations');
        _usingMock = false;
        return cachedResult;
      }

      // Fetch the core datasets needed for recommendations
      const [itemsResponse, analyticsResponse] = await Promise.all([
        api.get(`items?account_id=${currentUser.id}`),
        api.get(
          `dashboard/product-performance?account_id=${currentUser.id}${
            timeFrame ? `&time_frame=${timeFrame}` : ''
          }`
        )
      ]);

      const items = itemsResponse.data;
      const performanceResponse = analyticsResponse.data;
      // The backend returns the array directly, not wrapped in a products property
      const performanceData = Array.isArray(performanceResponse) ? performanceResponse : [];
      
      console.log('Fetched items:', items.length);
      console.log('Fetched performance data:', performanceData.length);
      console.log('Performance response structure:', performanceResponse);
      console.log('Performance data sample:', performanceData.slice(0, 2));
      console.log('Item IDs:', items.map((item: Item) => item.id));
      console.log('Performance data IDs:', performanceData.map((p: any) => p.id));
      
      // Extract all item IDs for batch fetching
      const itemIds = items.map((item: Item) => item.id);
      
      // Create a single request for all price histories using the batch API
      console.log(`Using batch API to fetch price history for ${itemIds.length} items at once`);
      
      // Fetch all orders for price analysis in parallel with price history
      const [priceHistoryByItemId] = await Promise.all([
        itemService.getPriceHistoryBatch(itemIds)]);
      
      console.log('Fetched price history for', Object.keys(priceHistoryByItemId).length, 'items');

      // Build recommendations using detailed price history data
      _usingMock = false;
      const recommendations = generateRecommendationsFromData(
        items,
        performanceData,
        priceHistoryByItemId,
        timeFrame
      );
      
      // OPTIMIZATION: Cache the result for 3 minutes
      frontendCache.set(cacheKey, recommendations, 3 * 60 * 1000);
      
      return recommendations;
    } catch (error) {
      console.error('Error fetching item summaries:', error);
      // Fallback to mock data so the UI still renders
      _usingMock = true;
      return generateMockRecommendations(timeFrame);
    }
  },
  
  // Apply a price recommendation (this would update the price in a real implementation)
  applyRecommendation: async (itemId: number, newPrice: number): Promise<boolean> => {
    try {
      const currentUser = authService.getCurrentUser();
      if (!currentUser) {
        console.error('User not authenticated');
        throw new Error('User not authenticated');
      }

      // In a real implementation, this would call an API to update the price
      // Include account_id to ensure we're only updating prices for items that belong to the current user
      await api.post(`items/${itemId}/update-price?account_id=${currentUser.id}`, { price: newPrice });
      return true;
    } catch (error) {
      console.error(`Error applying price recommendation for item ${itemId}:`, error);
      return false;
    }
  },
  
  // Accessor to let components know whether mock data was returned in the last call
  wasMock: (): boolean => _usingMock
};

// Helper function to generate recommendations from real data
const generateRecommendationsFromData = (
  items: Item[], 
  performanceData: any[], 
  priceHistoryByItemId: {[itemId: number]: PriceHistory[]},
  timeFrame: string,
): PriceRecommendation[] => {
  // Ensure performanceData is an array
  const safePerformanceData = Array.isArray(performanceData) ? performanceData : [];
  
  return items.map((item: Item) => {
    // Find performance data for this item
    const performance = safePerformanceData.find(p => p.id === item.id) || {
      quantity: 0,
      revenue: 0,
      marginPercentage: 0
    };
    
    // Get the price history for this item from our organized data structure 
    const priceHistory = priceHistoryByItemId[item.id] || [];
    
    console.log(`Processing item: ${item.name} (ID: ${item.id}), Current price: ${item.current_price}`);
    console.log(`Performance data found:`, performance);
    console.log(`Price history records found: ${priceHistory.length}`);
    
    // Calculate growth based on price history if available
    let growth = 0;
    if (priceHistory.length >= 2) {
      const oldPrice = priceHistory[priceHistory.length - 2].new_price;
      const currentPrice = item.current_price;
      growth = ((currentPrice - oldPrice) / oldPrice) * 100;
    }
    
    // Use profit margin from performance data or calculate if not available
    const profitMargin = performance.marginPercentage ? performance.marginPercentage / 100 : 
      (item.cost ? (item.current_price - item.cost) / item.current_price : 0.4); // Default 40% if no cost data
    
    return {
      id: item.id,
      name: item.name,
      category: item.category,
      currentPrice: item.current_price,
      previousPrice: null,
      lastPriceChangeDate: null,
      quantity: performance.quantity || 0,
      revenue: performance.revenue || 0,
      growth: Math.round(growth * 100) / 100, // Round to 2 decimal places
      profitMargin,
      elasticity: null,
      optimizationReason: null,
      previousRevenue: null,
      incrementalRevenue: null,
      measuredRevenueChangePercent: null,
      timeFrame
    };
  });
};

// Mock data generation for fallback
const generateMockRecommendations = (timeFrame: string): PriceRecommendation[] => {
  // Sample products for mock data
  const products = [
    { id: 1, name: 'Small Coffee', category: 'Coffee', basePrice: 2.99, popularity: 0.9 },
    { id: 2, name: 'Medium Coffee', category: 'Coffee', basePrice: 3.99, popularity: 1.5 },
    { id: 3, name: 'Large Coffee', category: 'Coffee', basePrice: 4.99, popularity: 0.6 },
    { id: 4, name: 'Cappucino', category: 'Coffee', basePrice: 5.99, popularity: 0.8 },
    { id: 5, name: 'Latte', category: 'Coffee', basePrice: 6.99, popularity: 0.7 },
    { id: 6, name: 'Americano', category: 'Coffee', basePrice: 7.99, popularity: 1.2 },
    { id: 7, name: 'Espresso', category: 'Coffee', basePrice: 8.99, popularity: 1.1 },
    { id: 8, name: 'Mocha', category: 'Coffee', basePrice: 9.99, popularity: 1.3 },
    { id: 9, name: 'Croissant', category: 'Pastry', basePrice: 1.99, popularity: 0.85 },
    { id: 10, name: 'Danish', category: 'Pastry', basePrice: 2.99, popularity: 0.95 },
  ];

  // Helper functions to create varied but deterministic recommendations
  const getVariationMultiplier = (timeFrame: string) => {
    switch (timeFrame) {
      case '1d': return 0.2;
      case '7d': return 0.5;
      case '1m': return 0.8;
      case '6m': return 1.2;
      case '1yr': return 2.0;
      default: return 0.5;
    }
  };

  const getBaseQuantity = (timeFrame: string) => {
    switch (timeFrame) {
      case '1d': return 5;
      case '7d': return 50;
      case '1m': return 200;
      case '6m': return 800;
      case '1yr': return 2000;
      default: return 50;
    }
  };

  const variationMultiplier = getVariationMultiplier(timeFrame);
  const baseQuantity = getBaseQuantity(timeFrame);
  
  // Create a seed based on the timeframe for consistent randomness
  let seed = timeFrame === '1d' ? 0.2 : 
             timeFrame === '7d' ? 0.3 : 
             timeFrame === '1m' ? 0.4 : 
             timeFrame === '6m' ? 0.5 : 0.6;

  return products.map(product => {
    // Use seed to create pseudo-random but consistent values
    seed = (seed * 9301 + 49297) % 233280;
    const random1 = seed / 233280;
    
    seed = (seed * 9301 + 49297) % 233280;
    const random2 = seed / 233280;
    
    seed = (seed * 9301 + 49297) % 233280;
    const random3 = seed / 233280;

    // Calculate current performance
    const quantity = Math.round(baseQuantity * product.popularity * (1 + (random1 * variationMultiplier - variationMultiplier/2)));
    const revenue = quantity * product.basePrice;
    const profitMargin = 0.3 + (random2 * 0.3);
    const profit = revenue * profitMargin;
    const growthVariance = variationMultiplier * 30;
    const growth = Math.round((random3 * growthVariance) - growthVariance/4);
    
    // Calculate price recommendation
    const demandElasticity = 0.5 + random1 * 1.5; // 0.5 - 2.0 range
    const currentDemandRatio = quantity / baseQuantity;
    
    // Recommended price change based on popularity and current demand
    let priceChangeDirection = 1;
    if (currentDemandRatio > 1.2 && growth > 5) {
      // High demand and positive growth: increase price
      priceChangeDirection = 1;
    } else if (currentDemandRatio < 0.8 || growth < -5) {
      // Low demand or negative growth: decrease price
      priceChangeDirection = -1;
    } else {
      // Stable demand: small adjustment based on profitability
      priceChangeDirection = profitMargin > 0.4 ? -1 : 1;
    }
    
    // Calculate percentage change (1-10%)
    const percentChange = Math.round((1 + random2 * 9) * priceChangeDirection);
    
    // Generate a previous price (slightly different from current to show history)
    const previousPriceVariation = (random2 > 0.5 ? 1 : -1) * (0.02 + random1 * 0.05);
    const previousPrice = Number((product.basePrice * (1 - previousPriceVariation)).toFixed(2));
    
    // Calculate measured impact from the price change
    const priceChangeRatio = product.basePrice / previousPrice;
    const estimatedPreviousQuantity = Math.round(quantity / (priceChangeRatio ** -demandElasticity));
    const previousRevenue = estimatedPreviousQuantity * previousPrice;
    const measuredRevenueDiff = revenue - previousRevenue;
    const measuredRevenueChangePercent = Math.round((measuredRevenueDiff / previousRevenue) * 100);
    
    return {
      id: product.id,
      name: product.name,
      category: product.category,
      currentPrice: product.basePrice,
      previousPrice,
      quantity,
      revenue,
      growth,
      profitMargin,
      elasticity: demandElasticity.toFixed(2),
      optimizationReason: percentChange > 0 
        ? 'Demand exceeds supply' 
        : percentChange < 0 
          ? 'Increase competitiveness' 
          : 'Maintain market position',
      previousRevenue,
      incrementalRevenue: measuredRevenueDiff,
      measuredRevenueChangePercent,
      timeFrame
    };
  });
};

export default pricingService;
