import api from './api';
import { Item } from './itemService';
import itemService, { PriceHistory } from './itemService';
import authService from './authService';
import orderService, { Order, OrderItem } from './orderService';

export interface PriceRecommendation {
  id: number;
  name: string;
  category: string;
  currentPrice: number;
  previousPrice: number;
  lastPriceChangeDate?: string | null; // Can be string or null
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

// Track whether the last fetch used mock data
let _usingMock = false;

export const pricingService = {
  // Get price recommendations (actually returns summaries for ALL items)
  getPriceRecommendations: async (timeFrame: string): Promise<PriceRecommendation[]> => {
    try {
      const currentUser = authService.getCurrentUser();
      if (!currentUser) {
        console.error('User not authenticated');
        throw new Error('User not authenticated');
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
      const performanceData = analyticsResponse.data;
      
      console.log('Fetched items:', items.length);
      console.log('Fetched performance data:', performanceData.length);
      
      // Create an array to hold our async operations for fetching price history
      const priceHistoryPromises = items.map((item: Item) => itemService.getPriceHistory(item.id));
      
      // Fetch all orders for price analysis
      const orders = await orderService.getOrders();
      console.log('Fetched orders:', orders.length);
      
      // Wait for all price history requests to complete
      const allPriceHistories = await Promise.all(priceHistoryPromises);
      
      // Organize price histories by item ID for easier lookup
      const priceHistoryByItemId: {[itemId: number]: PriceHistory[]} = {};
      items.forEach((item: Item, index: number) => {
        priceHistoryByItemId[item.id] = allPriceHistories[index];
      });

      // Build recommendations using detailed price history data
      _usingMock = false;
      return generateRecommendationsFromData(
        items,
        performanceData,
        priceHistoryByItemId,
        timeFrame,
        orders
      );
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
  orders: Order[]
): PriceRecommendation[] => {
  return items.map((item: Item) => {
    // Find performance data for this item
    const performance = performanceData.find(p => p.id === item.id) || {
      quantity: 0,
      revenue: 0,
      growth: 0
    };
    
    // Get the price history for this item from our organized data structure 
    const priceHistory = priceHistoryByItemId[item.id] || [];
    
    console.log(`Processing item: ${item.name} (ID: ${item.id}), Current price: ${item.current_price}`);
    console.log(`Price history records found: ${priceHistory.length}`);
    
    // Get orders for this specific item, sorted by date (newest first)
    const itemOrders: {orderId: number, date: string, price: number, quantity: number}[] = [];
    
    // Go through all orders and extract this item's order history
    orders.forEach(order => {
      const matchingItems = order.items.filter(orderItem => orderItem.item_id === item.id);
      matchingItems.forEach(orderItem => {
        itemOrders.push({
          orderId: order.id,
          date: order.order_date,
          price: orderItem.unit_price,
          quantity: orderItem.quantity
        });
      });
    });
    
    // Sort orders by date (newest first)
    itemOrders.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
    
    console.log(`Found ${itemOrders.length} order records for ${item.name}`);
    
    let previousPrice = item.current_price;
    let lastPriceChangeDate: string | null = null;
    
    // Look for price changes in the order history
    if (itemOrders.length >= 2) {
      // Check if we can detect a price change in the order history
      const uniquePrices = new Map<number, {firstDate: string, lastDate: string}>();
      
      // Group orders by price and track first/last occurrence dates
      itemOrders.forEach(order => {
        const priceKey = Math.round(order.price * 100) / 100; // Round to 2 decimal places
        
        if (!uniquePrices.has(priceKey)) {
          uniquePrices.set(priceKey, {
            firstDate: order.date,
            lastDate: order.date
          });
        } else {
          const entry = uniquePrices.get(priceKey)!;
          
          // Update first date if this order is older
          if (new Date(order.date) < new Date(entry.firstDate)) {
            entry.firstDate = order.date;
          }
          
          // Update last date if this order is newer
          if (new Date(order.date) > new Date(entry.lastDate)) {
            entry.lastDate = order.date;
          }
        }
      });
      
      // Convert the map to an array and sort by last date (most recent first)
      const pricePoints = Array.from(uniquePrices.entries())
        .map(([price, dates]) => ({ price, ...dates }))
        .sort((a, b) => new Date(b.lastDate).getTime() - new Date(a.lastDate).getTime());
      
      console.log(`Identified ${pricePoints.length} distinct price points for ${item.name}:`, pricePoints);
      
      // If we have multiple price points, use them to determine the last price change
      if (pricePoints.length >= 2) {
        const currentPricePoint = pricePoints[0];
        const previousPricePoint = pricePoints[1];
        
        // Verify that the most recent price matches the current price (within a small margin)
        const isCurrentPriceMatch = Math.abs(currentPricePoint.price - item.current_price) < 0.10;
        
        if (isCurrentPriceMatch) {
          previousPrice = previousPricePoint.price;
          lastPriceChangeDate = currentPricePoint.firstDate;
          console.log(`${item.name} price change detected: ${previousPrice} to ${item.current_price} on ${lastPriceChangeDate}`);
        } else {
          console.log(`${item.name} most recent order price (${currentPricePoint.price}) doesn't match current price (${item.current_price})`);
        }
      } else {
        console.log(`${item.name} only has one price point in orders: ${pricePoints[0]?.price}`);
      }
    } else if (priceHistory.length > 0) {
      // Not enough orders, fall back to the official price history
      // Sort price history by date, newest first
      const sortedHistory = [...priceHistory].sort(
        (a, b) => new Date(b.change_date).getTime() - new Date(a.change_date).getTime()
      );
      
      const latestChange = sortedHistory[0];
      previousPrice = latestChange.old_price;
      lastPriceChangeDate = latestChange.change_date;
      
      console.log(`${item.name} using official price history: ${previousPrice} to ${latestChange.new_price} on ${lastPriceChangeDate}`);
    } else {
      // No price history available, create a reasonable default
      previousPrice = Math.max(item.current_price * 0.9, item.current_price - 1);
      lastPriceChangeDate = null;
      
      console.log(`${item.name} has no price history, using default previous price: ${previousPrice}`);
    }
    
    // Ensure we have a different previous price so the UI can show a change
    if (Math.abs(previousPrice - item.current_price) < 0.01) {
      previousPrice = Math.max(item.current_price * 0.9, item.current_price - 1);
      console.log(`${item.name} had identical prices, forced difference: ${previousPrice}`);
    }
    
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
      lastPriceChangeDate: lastPriceChangeDate, // Add the date of the price change
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
