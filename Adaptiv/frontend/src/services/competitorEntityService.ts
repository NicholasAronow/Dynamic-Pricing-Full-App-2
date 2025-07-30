import { api } from './api';

// TypeScript interfaces for CompetitorEntity
export interface CompetitorEntity {
  id: number;
  user_id: number;
  name: string;
  address?: string;
  category?: string;
  phone?: string;
  website?: string;
  distance_km?: number;
  latitude?: number;
  longitude?: number;
  menu_url?: string;
  score?: number;
  is_selected: boolean;
  created_at: string;
  updated_at?: string;
  items?: CompetitorItem[];
}

export interface CompetitorEntityCreate {
  name: string;
  address?: string;
  category?: string;
  phone?: string;
  website?: string;
  distance_km?: number;
  latitude?: number;
  longitude?: number;
  menu_url?: string;
  score?: number;
  is_selected?: boolean;
}

export interface CompetitorEntityUpdate {
  name?: string;
  address?: string;
  category?: string;
  phone?: string;
  website?: string;
  distance_km?: number;
  latitude?: number;
  longitude?: number;
  menu_url?: string;
  score?: number;
  is_selected?: boolean;
}

export interface CompetitorItem {
  id: number;
  competitor_id: number;
  competitor_name: string;
  item_name: string;
  description?: string;
  category: string;
  price: number;
  similarity_score?: number;
  url?: string;
  created_at: string;
  updated_at: string;
  competitor?: CompetitorEntity;
}

export interface CompetitorStats {
  competitor_id: number;
  competitor_name: string;
  total_items: number;
  price_stats: {
    min_price: number;
    max_price: number;
    avg_price: number;
  };
  category_breakdown: Array<{
    category: string;
    item_count: number;
    avg_price: number;
  }>;
}

export interface CompetitorScrapeRequest {
  restaurant_name: string;
  location?: string;
}

export interface CompetitorScrapeResponse {
  task_id: string;
  message: string;
  status: string;
}

export interface CompetitorScrapeStatusResponse {
  task_id: string;
  status: string;
  result?: {
    success: boolean;
    competitor_id?: number;
    items_added: number;
    message?: string;
    error?: string;
  };
  error?: string;
}

class CompetitorEntityService {
  private baseUrl = '/api/competitor-entities';

  // Get all competitor entities
  async getCompetitorEntities(params?: {
    include_items?: boolean;
    skip?: number;
    limit?: number;
  }): Promise<CompetitorEntity[]> {
    try {
      const response = await api.get(this.baseUrl, { params });
      console.log('Raw response:', response);
      
      // Handle the response based on whether it's already parsed or not
      if (response.data && Array.isArray(response.data)) {
        return response.data;
      } else if (Array.isArray(response)) {
        return response;
      } else {
        console.error('Unexpected response format:', response);
        return [];
      }
    } catch (error) {
      console.error('Error fetching competitor entities:', error);
      throw error;
    }
  }

  // Get a specific competitor entity
  async getCompetitorEntity(
    competitorId: number,
    includeItems: boolean = false
  ): Promise<CompetitorEntity> {
    try {
      const response = await api.get(`${this.baseUrl}/${competitorId}`, {
        params: { include_items: includeItems }
      });
      return response.data;
    } catch (error) {
      console.error('Error fetching competitor entity:', error);
      throw error;
    }
  }

  // Create a new competitor entity
  async createCompetitorEntity(data: CompetitorEntityCreate): Promise<CompetitorEntity> {
    try {
      const response = await api.post(this.baseUrl, data);
      return response.data;
    } catch (error) {
      console.error('Error creating competitor entity:', error);
      throw error;
    }
  }

  // Update a competitor entity
  async updateCompetitorEntity(
    competitorId: number,
    data: CompetitorEntityUpdate
  ): Promise<CompetitorEntity> {
    try {
      const response = await api.put(`${this.baseUrl}/${competitorId}`, data);
      return response.data;
    } catch (error) {
      console.error('Error updating competitor entity:', error);
      throw error;
    }
  }

  // Delete a competitor entity
  async deleteCompetitorEntity(competitorId: number): Promise<void> {
    try {
      await api.delete(`${this.baseUrl}/${competitorId}`);
    } catch (error) {
      console.error('Error deleting competitor entity:', error);
      throw error;
    }
  }

  // Select competitor for tracking
  async selectCompetitorForTracking(competitorId: number): Promise<{
    message: string;
    competitor: CompetitorEntity;
  }> {
    try {
      const response = await api.post(`${this.baseUrl}/${competitorId}/select`);
      return response.data;
    } catch (error) {
      console.error('Error selecting competitor for tracking:', error);
      throw error;
    }
  }

  // Unselect competitor from tracking
  async unselectCompetitorFromTracking(competitorId: number): Promise<{
    message: string;
    competitor: CompetitorEntity;
  }> {
    try {
      const response = await api.post(`${this.baseUrl}/${competitorId}/unselect`);
      return response.data;
    } catch (error) {
      console.error('Error unselecting competitor from tracking:', error);
      throw error;
    }
  }

  // Get items for a specific competitor
  async getCompetitorItems(
    competitorId: number,
    params?: {
      category?: string;
      skip?: number;
      limit?: number;
    }
  ): Promise<CompetitorItem[]> {
    try {
      const response = await api.get('/api/competitor-items', { 
        params: { ...params, competitor_id: competitorId }
      });
      return response.data;
    } catch (error) {
      console.error('Error fetching competitor items:', error);
      throw error;
    }
  }

  // Get statistics for a competitor
  async getCompetitorStats(competitorId: number): Promise<CompetitorStats> {
    try {
      const response = await api.get(`${this.baseUrl}/${competitorId}/stats`);
      return response.data;
    } catch (error) {
      console.error('Error fetching competitor stats:', error);
      throw error;
    }
  }

  // Get all selected competitors
  async getSelectedCompetitors(): Promise<CompetitorEntity[]> {
    try {
      const response = await api.get(`${this.baseUrl}/selected`);
      return response.data;
    } catch (error) {
      console.error('Error fetching selected competitors:', error);
      throw error;
    }
  }

  // Migrate legacy competitor data
  async migrateLegacyData(): Promise<{
    message: string;
    details: {
      migrated_competitors: number;
      existing_competitors: number;
      total_processed: number;
    };
  }> {
    try {
      const response = await api.post(`${this.baseUrl}/migrate-legacy-data`);
      return response.data;
    } catch (error) {
      console.error('Error migrating legacy data:', error);
      throw error;
    }
  }

  // Toggle competitor selection (utility method)
  async toggleCompetitorSelection(
    competitorId: number,
    isSelected: boolean
  ): Promise<CompetitorEntity> {
    if (isSelected) {
      const result = await this.selectCompetitorForTracking(competitorId);
      return result.competitor;
    } else {
      const result = await this.unselectCompetitorFromTracking(competitorId);
      return result.competitor;
    }
  }

  // Get competitor summary data (for dashboard/overview)
  async getCompetitorSummary(): Promise<{
    total_competitors: number;
    selected_competitors: number;
    total_items: number;
    recent_activity: Array<{
      competitor_name: string;
      action: string;
      timestamp: string;
    }>;
  }> {
    try {
      const response = await api.get(`${this.baseUrl}/summary`);
      return response.data;
    } catch (error) {
      console.error('Error fetching competitor summary:', error);
      // Return default values on error
      return {
        total_competitors: 0,
        selected_competitors: 0,
        total_items: 0,
        recent_activity: []
      };
    }
  }

  // Scrape competitor data using the restaurant menu scraper
  async scrapeCompetitor(request: CompetitorScrapeRequest): Promise<CompetitorScrapeResponse> {
    try {
      const response = await api.post(`${this.baseUrl}/scrape`, request);
      console.log('Scrape response:', response.data);
      return response.data;
    } catch (error) {
      console.error('Error scraping competitor:', error);
      throw error;
    }
  }

  // Check the status of a scraping task
  async getScrapeStatus(taskId: string): Promise<CompetitorScrapeStatusResponse> {
    try {
      const response = await api.get(`${this.baseUrl}/scrape/status/${taskId}`);
      console.log('Scrape status response:', response.data);
      return response.data;
    } catch (error) {
      console.error('Error getting scrape status:', error);
      throw error;
    }
  }
}

export default new CompetitorEntityService();
