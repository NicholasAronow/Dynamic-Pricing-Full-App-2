import { useState, useEffect } from 'react';
import axios from 'axios';
import { useSubscription } from '../contexts/SubscriptionContext';
import api from 'services/api';

interface MarketInsight {
  market_position: number;
  pricing_efficiency: number;
  revenue_potential: number;
  competitor_pricing_data: Array<{
    category: string;
    your_price: number;
    market_average: number;
    recommendation: string;
  }>;
}

interface AIRecommendation {
  product: string;
  current_price: number;
  recommended_price: number;
  expected_impact: string;
  confidence: string;
  reasoning: string;
}

interface AIRecommendations {
  ai_recommendations: AIRecommendation[];
  overall_potential: string;
}

interface RealTimeMetrics {
  timestamp: string;
  current_hour_sales: number;
  current_hour_orders: number;
  trending_items: Array<{
    name: string;
    orders_last_hour: number;
  }>;
  live_metrics: {
    avg_order_value: number;
    sales_vs_yesterday: string;
    busiest_time_today: string;
  };
}

interface PremiumAnalyticsHook {
  marketInsights: MarketInsight | null;
  aiRecommendations: AIRecommendations | null;
  realTimeMetrics: RealTimeMetrics | null;
  loadingMarketInsights: boolean;
  loadingAIRecommendations: boolean;
  loadingRealTimeMetrics: boolean;
  errorMarketInsights: string | null;
  errorAIRecommendations: string | null;
  errorRealTimeMetrics: string | null;
  refreshMarketInsights: () => Promise<void>;
  refreshAIRecommendations: () => Promise<void>;
  refreshRealTimeMetrics: () => Promise<void>;
}

/**
 * Custom hook for accessing premium analytics features
 * Will automatically handle subscription tier restrictions
 */
export const usePremiumAnalytics = (): PremiumAnalyticsHook => {
  const { hasAccess, isSubscribed } = useSubscription();
  
  const [marketInsights, setMarketInsights] = useState<MarketInsight | null>(null);
  const [aiRecommendations, setAIRecommendations] = useState<AIRecommendations | null>(null);
  const [realTimeMetrics, setRealTimeMetrics] = useState<RealTimeMetrics | null>(null);
  
  const [loadingMarketInsights, setLoadingMarketInsights] = useState<boolean>(false);
  const [loadingAIRecommendations, setLoadingAIRecommendations] = useState<boolean>(false);
  const [loadingRealTimeMetrics, setLoadingRealTimeMetrics] = useState<boolean>(false);
  
  const [errorMarketInsights, setErrorMarketInsights] = useState<string | null>(null);
  const [errorAIRecommendations, setErrorAIRecommendations] = useState<string | null>(null);
  const [errorRealTimeMetrics, setErrorRealTimeMetrics] = useState<string | null>(null);

  // Market insights available to Basic and Premium subscribers
  const fetchMarketInsights = async () => {
    if (!hasAccess('advanced_analytics')) {
      setErrorMarketInsights('Market insights require a Basic subscription or higher');
      return;
    }
    
    setLoadingMarketInsights(true);
    setErrorMarketInsights(null);
    
    try {
      const response = await api.get('/premium-analytics/market-insights');
      setMarketInsights(response.data);
    } catch (error) {
      console.error('Error fetching market insights:', error);
      setErrorMarketInsights('Failed to load market insights');
    } finally {
      setLoadingMarketInsights(false);
    }
  };

  // AI recommendations available to Premium subscribers only
  const fetchAIRecommendations = async () => {
    if (!hasAccess('ai_recommendations')) {
      setErrorAIRecommendations('AI recommendations require a Premium subscription');
      return;
    }
    
    setLoadingAIRecommendations(true);
    setErrorAIRecommendations(null);
    
    try {
      const response = await api.get('/premium-analytics/ai-recommendations');
      setAIRecommendations(response.data);
    } catch (error) {
      console.error('Error fetching AI recommendations:', error);
      setErrorAIRecommendations('Failed to load AI recommendations');
    } finally {
      setLoadingAIRecommendations(false);
    }
  };

  // Real-time metrics available to Premium subscribers only
  const fetchRealTimeMetrics = async () => {
    if (!hasAccess('real_time_analytics')) {
      setErrorRealTimeMetrics('Real-time analytics require a Premium subscription');
      return;
    }
    
    setLoadingRealTimeMetrics(true);
    setErrorRealTimeMetrics(null);
    
    try {
      const response = await api.get('/premium-analytics/real-time-metrics');
      setRealTimeMetrics(response.data);
    } catch (error) {
      console.error('Error fetching real-time metrics:', error);
      setErrorRealTimeMetrics('Failed to load real-time metrics');
    } finally {
      setLoadingRealTimeMetrics(false);
    }
  };

  // Load initial data if the user has access
  useEffect(() => {
    if (hasAccess('advanced_analytics')) {
      fetchMarketInsights();
    }
    
    if (hasAccess('ai_recommendations')) {
      fetchAIRecommendations();
    }
    
    if (hasAccess('real_time_analytics')) {
      fetchRealTimeMetrics();
    }
  }, [isSubscribed()]);

  return {
    marketInsights,
    aiRecommendations,
    realTimeMetrics,
    loadingMarketInsights,
    loadingAIRecommendations,
    loadingRealTimeMetrics,
    errorMarketInsights,
    errorAIRecommendations,
    errorRealTimeMetrics,
    refreshMarketInsights: fetchMarketInsights,
    refreshAIRecommendations: fetchAIRecommendations,
    refreshRealTimeMetrics: fetchRealTimeMetrics,
  };
};
