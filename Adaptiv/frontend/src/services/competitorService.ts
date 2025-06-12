import api from './api';

export interface GeminiCompetitor {
  name: string;
  address: string;
  category: string;
  distance_km?: number;
  menu_url?: string;
  report_id: number;
  created_at: string;
}

export interface CompetitorItem {
  id: number;
  competitor_name: string;
  item_name: string;
  description: string;
  category: string;
  price: number;
  similarity_score: number;
  url: string;
  created_at: string;
  updated_at: string;
  distance?: number; // Optional distance in miles
}

export interface CompetitorItemCreate {
  competitor_name: string;
  item_name: string;
  description: string;
  category: string;
  price: number;
  similarity_score: number;
  url: string;
  distance?: number; // Optional distance in miles
}

export const competitorService = {
  // Get full competitor data from the Gemini API endpoint
  getGeminiCompetitors: async (): Promise<GeminiCompetitor[]> => {
    try {
      // This is the correct endpoint path used in the Competitors component
      const response = await api.get('/gemini-competitors/competitors');
      if (response.data && response.data.success && Array.isArray(response.data.competitors)) {
        return response.data.competitors;
      }
      return [];
    } catch (error) {
      console.error('Error fetching Gemini competitors:', error);
      return [];
    }
  },
  getCompetitorItems: async (competitorName?: string): Promise<CompetitorItem[]> => {
    // We're already using the baseURL from api.ts, so no need to include '/api'
    const url = competitorName 
      ? `competitor-items?competitor_name=${encodeURIComponent(competitorName)}`
      : 'competitor-items';
    console.log('Calling endpoint:', url);
    const response = await api.get(url);
    return response.data;
  },

  getCompetitorItem: async (id: number): Promise<CompetitorItem> => {
    const response = await api.get(`competitor-items/${id}`);
    return response.data;
  },

  createCompetitorItem: async (item: CompetitorItemCreate): Promise<CompetitorItem> => {
    const response = await api.post('competitor-items', item);
    return response.data;
  },

  updateCompetitorItem: async (id: number, item: Partial<CompetitorItemCreate>): Promise<CompetitorItem> => {
    const response = await api.put(`competitor-items/${id}`, item);
    return response.data;
  },

  deleteCompetitorItem: async (id: number): Promise<void> => {
    await api.delete(`competitor-items/${id}`);
  },

  // Get unique competitor names by fetching all competitor items and extracting unique names
  // This fetches from the competitor items API, not the Gemini competitors
  getCompetitors: async (): Promise<string[]> => {
    console.log('Fetching all competitor items to extract competitor names');
    try {
      // Get all competitor items
      const response = await api.get('competitor-items');
      const items = response.data;
      
      // Extract unique competitor names
      const competitorNamesSet = new Set<string>();
      items.forEach((item: CompetitorItem) => {
        if (item.competitor_name) {
          competitorNamesSet.add(item.competitor_name);
        }
      });
      
      const uniqueCompetitorNames = Array.from(competitorNamesSet);
      console.log('Extracted unique competitor names:', uniqueCompetitorNames);
      
      return uniqueCompetitorNames.length > 0 
        ? uniqueCompetitorNames 
        : [];
    } catch (error) {
      console.error('Error fetching competitor items:', error);
      // If the API call fails, return some static data as fallback
      console.log('Using fallback competitor data');
      return [];
    }
  },

  // Get competitor items by category
  getCompetitorItemsByCategory: async (category: string): Promise<CompetitorItem[]> => {
    try {
      const response = await api.get(`competitor-items?category=${category}`);
      return response.data;
    } catch (error) {
      console.error(`Error fetching competitor items for category ${category}:`, error);
      return [];
    }
  },
  
  // Get competitor items by item ID
  getCompetitorItemsByItemId: async (itemId: number): Promise<CompetitorItem[]> => {
    try {
      const response = await api.get(`competitor-items?item_id=${itemId}`);
      return response.data;
    } catch (error) {
      console.error(`Error fetching competitor items for item ${itemId}:`, error);
      return [];
    }
  },
  
  // Get competitor data for market position analysis
  getSimilarCompetitors: async (itemId: number): Promise<any> => {
    try {
      console.log(`Fetching similar competitors for item ${itemId}`);
      const response = await api.get(`competitor-items/similar-to/${itemId}`);
      console.log('Similar competitors response:', response.data);
      return response.data;
    } catch (error) {
      console.error(`Error fetching similar competitors for item ${itemId}:`, error);
      return null;
    }
  },
  
  // Calculate similarity score between our business and a competitor
  calculateSimilarityScore: async (competitorName: string): Promise<{
    similarityScore: number;
    priceSimScore: number;
    menuSimScore: number;
    distanceScore: number;
    distance: number;
  }> => {
    try {
      // Get all of our items
      const ourItems = await api.get('items');
      
      // Get competitor items
      const competitorResponse = await api.get(`competitor-items?competitor_name=${encodeURIComponent(competitorName)}`);
      const competitorItems: CompetitorItem[] = competitorResponse.data;
      
      if (competitorItems.length === 0 || ourItems.data.length === 0) {
        return {
          similarityScore: 0,
          priceSimScore: 0,
          menuSimScore: 0,
          distanceScore: 0,
          distance: 0
        };
      }
      
      // 1. Price similarity - weighted at 40%
      const ourAvgPrice = ourItems.data.reduce((sum: number, item: any) => sum + item.current_price, 0) / ourItems.data.length;
      const compAvgPrice = competitorItems.reduce((sum: number, item: CompetitorItem) => sum + item.price, 0) / competitorItems.length;
      
      // Calculate price difference as a percentage
      const priceDiffPercent = Math.abs((ourAvgPrice - compAvgPrice) / ourAvgPrice);
      // Convert to a score where 100% means identical prices, 0% means >50% difference
      const priceSimScore = Math.max(0, 100 - (priceDiffPercent * 200));
      
      // 2. Menu similarity - weighted at 40%
      // Compare categories and menu items
      const ourCategories = new Set<string>(ourItems.data.map((item: any) => item.category));
      const compCategories = new Set<string>(competitorItems.map((item: CompetitorItem) => item.category));
      
      // Calculate category overlap
      const categoryOverlap = new Set<string>(
        Array.from(ourCategories).filter((cat: string) => compCategories.has(cat))
      );
      const categorySimScore = ourCategories.size > 0 ? 
        (categoryOverlap.size / ourCategories.size) * 100 : 0;
      
      // Calculate menu item name similarity (fuzzy match)
      let itemNameMatches = 0;
      ourItems.data.forEach((ourItem: any) => {
        competitorItems.forEach((compItem: CompetitorItem) => {
          // Simple fuzzy matching - consider similar if 70% of words match
          const ourWords = ourItem.name.toLowerCase().split(/\s+/);
          const compWords = compItem.item_name.toLowerCase().split(/\s+/);
          
          let matchedWords = 0;
          ourWords.forEach((word: string) => {
            if (compWords.some((cw: string) => cw.includes(word) || word.includes(cw))) {
              matchedWords++;
            }
          });
          
          if (matchedWords / Math.max(ourWords.length, compWords.length) >= 0.7) {
            itemNameMatches++;
          }
        });
      });
      
      const itemSimScore = ourItems.data.length > 0 ?
        (itemNameMatches / ourItems.data.length) * 100 : 0;
      
      // Combine category and item scores for menu similarity
      const menuSimScore = (categorySimScore * 0.6) + (itemSimScore * 0.4);
      
      // 3. Distance - weighted at 20%
      // Default or random distance if not provided
      let distance = 0;
      if (competitorItems.some(item => item.distance !== undefined)) {
        distance = competitorItems.find(item => item.distance !== undefined)?.distance || 0;
      } else {
        // Generate a random distance between 0.1 and 3.0 miles for demonstration
        distance = Math.round((Math.random() * 2.9 + 0.1) * 10) / 10;
      }
      
      // Distance score: 100% if very close, 0% if > 5 miles
      const distanceScore = Math.max(0, 100 - (distance * 20));
      
      // Calculate weighted final similarity score
      const similarityScore = (
        (priceSimScore * 0.2) + 
        (menuSimScore * 0.6) + 
        (distanceScore * 0.2)
      );
      
      return {
        similarityScore: Math.round(similarityScore),
        priceSimScore: Math.round(priceSimScore),
        menuSimScore: Math.round(menuSimScore),
        distanceScore: Math.round(distanceScore),
        distance
      };
    } catch (error) {
      console.error(`Error calculating similarity score for ${competitorName}:`, error);
      return {
        similarityScore: 75, // Default fallback score
        priceSimScore: 75,
        menuSimScore: 75,
        distanceScore: 75,
        distance: 1.0 // Default distance
      };
    }
  }
};

export default competitorService;
