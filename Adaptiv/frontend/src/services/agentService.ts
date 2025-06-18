import axios from 'axios';
import { api } from './api';
import { API_BASE_URL } from '../config';

// Define types for the service
export interface ExperimentRecommendation {
  id?: number;
  summary?: string;
  start_date?: string;
  evaluation_date?: string;
  recommendations?: {
    implementation?: Array<{
      product_id: number;
      product_name: string;
      current_price: number;
      new_price: number;
    }>;
  };
  created_at?: string;
}

export interface CompetitorReport {
  id?: number;
  summary?: string;
  insights?: {
    insights?: {
      insights?: Array<{
        title: string;
        description: string;
      }>;
      positioning?: string;
    };
    positioning?: string;
  };
  created_at?: string;
}

export interface CustomerReport {
  id?: number;
  summary?: string;
  demographics?: Array<{
    name: string;
    characteristics: string[];
    price_sensitivity: number;
  }>;
  events?: Array<{
    name: string;
    date: string;
    projected_impact: string;
    impact_level: number;
  }>;
  created_at?: string;
}

export interface MarketReport {
  id?: number;
  summary?: string;
  supply_chain?: Array<{
    factor: string;
    impact: string;
    trend: 'increasing' | 'decreasing' | 'stable';
  }>;
  market_trends?: {
    cost_trends?: Array<{
      input_category: string;
      trend: string;
      forecast: string;
    }>;
  };
  created_at?: string;
}

export interface PricingReport {
  id?: number;
  summary?: string;
  recommended_changes?: Array<{
    product_id: number;
    product_name: string;
    current_price: number;
    recommended_price: number;
    change_percentage: number;
    rationale: string;
  }>;
  rationale?: {
    implementation?: {
      timing: string;
      sequencing: string;
      monitoring: string;
    };
  };
  created_at?: string;
}

export interface AgentReport {
  competitor_report?: CompetitorReport;
  customer_report?: CustomerReport;
  market_report?: MarketReport;
  pricing_report?: PricingReport;
  experiment_recommendation?: ExperimentRecommendation;
}

export interface AgentResponseData {
  message: string;
  success: boolean;
  data?: any;
}

export interface AgentProgressData {
  process_id: string;
  status: 'started' | 'running' | 'completed' | 'error';
  progress_percent: number;
  message: string;
  current_step: string;
  steps: {
    competitor_agent: {
      status: 'pending' | 'running' | 'completed' | 'error';
      report_id?: number;
    };
    customer_agent: {
      status: 'pending' | 'running' | 'completed' | 'error';
      report_id?: number;
    };
    market_agent: {
      status: 'pending' | 'running' | 'completed' | 'error';
      report_id?: number;
    };
    pricing_agent: {
      status: 'pending' | 'running' | 'completed' | 'error';
      report_id?: number;
    };
    experiment_agent: {
      status: 'pending' | 'running' | 'completed' | 'error';
      report_id?: number;
    };
  };
  error?: string;
}

// Service functions
const agentService = {
  // Run the full agent process
  runFullAgentProcess: async (): Promise<AgentResponseData> => {
    try {
      // Use the centralized api service instead of direct axios
      const response = await api.post(`agents-sdk/run-full-process`);
      return response.data;
    } catch (error) {
      console.error('Error running full agent process:', error);
      throw error;
    }
  },

  // Get the latest reports from all agents
  getLatestReports: async (): Promise<AgentReport> => {
    const maxRetries = 1; // Only retry once
    let retryCount = 0;
    
    const attemptRequest = async (): Promise<AgentReport> => {
      try {
        // Ensure the Authorization header is set for this specific request
        const token = localStorage.getItem('token');
        if (token) {
          // Authorization is handled by the api service automatically
          // No need to manually set the Authorization header
        }
        
        // Use the centralized api service instead of direct axios
        const response = await api.get(`agents-sdk/latest-reports`);
        return response.data;
      } catch (error: any) {
        // Check if this is a 401 error that should be retried
        if (error.response?.status === 401 && error.shouldRetry && retryCount < maxRetries) {
          console.log(`Retrying agent reports request (attempt ${retryCount + 1})`);
          retryCount++;
          return attemptRequest();
        }
        
        console.error('Error getting latest agent reports:', error);
        throw error;
      }
    };
    
    return attemptRequest();
  },

  // Run a specific agent
  runAgent: async (agentType: string): Promise<AgentResponseData> => {
    try {
      // Use the centralized api service instead of direct axios
      const response = await api.post(`agents-sdk/run-agent`, { agent_type: agentType });
      return response.data;
    } catch (error) {
      console.error(`Error running ${agentType} agent:`, error);
      throw error;
    }
  },

  // Get a specific report by type
  getReportByType: async (reportType: string): Promise<any> => {
    try {
      // Use the centralized api service instead of direct axios
      const response = await api.get(`agents-sdk/report/${reportType}`);
      return response.data;
    } catch (error) {
      console.error(`Error getting ${reportType} report:`, error);
      throw error;
    }
  },

  // Implement price recommendations from the pricing agent
  implementRecommendations: async (recommendationIds: number[]): Promise<AgentResponseData> => {
    try {
      // Use the centralized api service instead of direct axios
      const response = await api.post(`agents-sdk/implement-recommendations`, {
        recommendation_ids: recommendationIds
      });
      return response.data;
    } catch (error) {
      console.error('Error implementing recommendations:', error);
      throw error;
    }
  },

  // Get the status of a specific agent process
  getProcessStatus: async (processId: string): Promise<AgentProgressData> => {
    try {
      // Use the centralized api service instead of direct axios
      const response = await api.get(`agents-sdk/process/${processId}`);
      return response.data;
    } catch (error) {
      console.error('Error getting process status:', error);
      throw error;
    }
  },

  // Get the latest agent process for the current user
  getLatestProcess(): Promise<AgentProgressData> {
    // Use the centralized api service instead of direct axios
    return api.get(`agents/process/latest`)
      .then(response => {
        return response.data.data;
      })
      .catch(error => {
        console.error('Error getting latest process:', error);
        throw error;
      });
  },

  // Handle price change recommendation approval or denial
  handlePriceRecommendation(productId: number, approved: boolean): Promise<AgentResponseData> {
    // Use the centralized api service instead of direct axios
    return api.post(`agents-sdk/pricing/recommendation`, {
      product_id: productId,
      approved: approved,
      action_taken: new Date().toISOString()
    })
    .then(response => {
      return response.data;
    })
    .catch(error => {
      console.error('Error handling price recommendation:', error);
      throw error;
    });
  },
};

export default agentService;
