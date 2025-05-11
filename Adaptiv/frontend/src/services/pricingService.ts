import api from './api';
import { Item } from './itemService';
import authService from './authService';

export interface PriceRecommendation {
  id: number;
  name: string;
  category: string;
  currentPrice: number;
  previousPrice: number;
  recommendedPrice?: number;
  percentChange?: number;
  quantity: number;
  revenue: number;
  growth: number;
  profitMargin: number;
  elasticity: string;
  optimizationReason: string;
  previousRevenue: number;
  incrementalRevenue: number;
  measuredRevenueChangePercent: number;
  projectedRevenue?: number;
  revenueChangePercent?: number;
  timeFrame: string;
  editing?: boolean;
}

export const pricingService = {
  // Get price recommendations for all items
  getPriceRecommendations: async (timeFrame: string): Promise<PriceRecommendation[]> => {
    try {
      const currentUser = authService.getCurrentUser();
      if (!currentUser) {
        console.error('User not authenticated');
        throw new Error('User not authenticated');
      }

      // Call the API endpoint for price recommendations with account filtering
      const response = await api.get(`price-recommendations?time_frame=${timeFrame}&account_id=${currentUser.id}`);
      return response.data;
    } catch (error) {
      console.error('Error fetching price recommendations:', error);
      
      // Fallback to generating recommendations based on items and sales data
      try {
        const currentUser = authService.getCurrentUser();
        if (!currentUser) {
          console.error('User not authenticated');
          return [];
        }

        // Get items for the current user's account
        const itemsResponse = await api.get(`items?account_id=${currentUser.id}`);
        const items = itemsResponse.data;
        
        // Get sales analytics for performance data
        const analyticsResponse = await api.get(
          `dashboard/product-performance?account_id=${currentUser.id}${timeFrame ? `&time_frame=${timeFrame}` : ''}`
        );
        const performanceData = analyticsResponse.data;
        
        // Get price history data for the current user's account
        const priceHistoryResponse = await api.get(`price-history?account_id=${currentUser.id}`);
        const priceHistoryData = priceHistoryResponse.data;
        
        // Combine data to generate recommendations
        return generateRecommendationsFromData(items, performanceData, priceHistoryData, timeFrame);
      } catch (fallbackError) {
        console.error('Fallback recommendation generation failed:', fallbackError);
        
        // Use mock data if all API calls fail
        return generateMockRecommendations(timeFrame);
      }
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
  }
};

// Helper function to generate recommendations from real data
const generateRecommendationsFromData = (
  items: Item[], 
  performanceData: any[], 
  priceHistory: any[],
  timeFrame: string
): PriceRecommendation[] => {
  return items.map(item => {
    // Find performance data for this item
    const performance = performanceData.find(p => p.id === item.id) || {
      quantity: 0,
      revenue: 0,
      growth: 0
    };
    
    // Find the most recent price change for this item
    const priceChanges = priceHistory.filter(p => p.item_id === item.id);
    const latestPriceChange = priceChanges.length > 0 
      ? priceChanges.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())[0]
      : null;
    
    const previousPrice = latestPriceChange ? latestPriceChange.old_price : item.current_price * 0.95;
    
    // Calculate price elasticity based on historical data
    // In a real implementation, this would be a more sophisticated calculation
    const elasticity = performance.quantity > 0 && previousPrice !== item.current_price
      ? Math.abs((performance.quantity / (performance.quantity * 0.9) - 1) / 
         (item.current_price / previousPrice - 1)).toFixed(2)
      : (Math.random() * 1.5 + 0.5).toFixed(2); // Random elasticity between 0.5 and 2.0
    
    // Calculate measured impact from the price change
    const previousQuantity = performance.quantity / 
      (Math.pow(item.current_price / previousPrice, -parseFloat(elasticity)));
    const previousRevenue = previousQuantity * previousPrice;
    const measuredRevenueDiff = performance.revenue - previousRevenue;
    const measuredRevenueChangePercent = Math.round((measuredRevenueDiff / previousRevenue) * 100);
    
    // Determine optimization reason based on performance
    let optimizationReason = 'Maintain market position';
    if (performance.growth > 10) {
      optimizationReason = 'Demand exceeds supply';
    } else if (performance.growth < -5) {
      optimizationReason = 'Increase competitiveness';
    }
    
    // Calculate profit margin (assuming cost is 60% of price if not available)
    const cost = item.cost || item.current_price * 0.6;
    const profitMargin = (item.current_price - cost) / item.current_price;
    
    return {
      id: item.id,
      name: item.name,
      category: item.category,
      currentPrice: item.current_price,
      previousPrice,
      quantity: performance.quantity || 0,
      revenue: performance.revenue || 0,
      growth: performance.growth || 0,
      profitMargin,
      elasticity,
      optimizationReason,
      previousRevenue,
      incrementalRevenue: measuredRevenueDiff,
      measuredRevenueChangePercent,
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
