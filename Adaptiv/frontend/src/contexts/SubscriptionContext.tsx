import React, { createContext, useState, useContext, useEffect, ReactNode } from 'react';
import axios from 'axios';
import api from 'services/api';

// Define subscription tiers and their features
export const SUBSCRIPTION_TIERS = {
  FREE: 'free',
  PREMIUM: 'premium',
};

// Features available for each subscription tier
export const SUBSCRIPTION_FEATURES = {
  // Basic features available to all users
  view_dashboard: [SUBSCRIPTION_TIERS.FREE, SUBSCRIPTION_TIERS.PREMIUM],
  manage_items: [SUBSCRIPTION_TIERS.FREE, SUBSCRIPTION_TIERS.PREMIUM],
  view_reports: [SUBSCRIPTION_TIERS.FREE, SUBSCRIPTION_TIERS.PREMIUM],
  
  // Premium features
  competitor_tracking: [SUBSCRIPTION_TIERS.PREMIUM],
  advanced_analytics: [SUBSCRIPTION_TIERS.PREMIUM],
  ai_recommendations: [SUBSCRIPTION_TIERS.PREMIUM],
  unlimited_items: [SUBSCRIPTION_TIERS.PREMIUM],
  api_access: [SUBSCRIPTION_TIERS.PREMIUM],
  real_time_analytics: [SUBSCRIPTION_TIERS.PREMIUM],
};

type SubscriptionFeature = keyof typeof SUBSCRIPTION_FEATURES;

interface SubscriptionStatus {
  active: boolean;
  subscription_id?: string;
  current_period_end?: string;
  plan?: string;
}

interface SubscriptionContextProps {
  subscriptionStatus: SubscriptionStatus | null;
  loading: boolean;
  refreshSubscription: () => Promise<void>;
  hasAccess: (feature: SubscriptionFeature) => boolean;
  isSubscribed: () => boolean;
  currentPlan: string;
}

const SubscriptionContext = createContext<SubscriptionContextProps | undefined>(undefined);

interface SubscriptionProviderProps {
  children: ReactNode;
}

export const SubscriptionProvider: React.FC<SubscriptionProviderProps> = ({ children }) => {
  const [subscriptionStatus, setSubscriptionStatus] = useState<SubscriptionStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [currentPlan, setCurrentPlan] = useState<string>(SUBSCRIPTION_TIERS.FREE);

  const refreshSubscription = async () => {
    setLoading(true);
    try {
      const response = await api.get('/subscriptions/subscription-status');
      setSubscriptionStatus(response.data);
      
      // Set the current plan (convert to lowercase for standardization)
      if (response.data.active && response.data.plan) {
        setCurrentPlan(response.data.plan.toLowerCase());
      } else {
        setCurrentPlan(SUBSCRIPTION_TIERS.FREE);
      }
    } catch (error) {
      console.error('Error fetching subscription status:', error);
      setCurrentPlan(SUBSCRIPTION_TIERS.FREE);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshSubscription();
  }, []);

  // Check if the user has access to a specific feature
  const hasAccess = (feature: SubscriptionFeature): boolean => {
    const allowedTiers = SUBSCRIPTION_FEATURES[feature];
    if (!allowedTiers) return false;
    
    return allowedTiers.includes(currentPlan);
  };

  // Check if the user has an active subscription (beyond free tier)
  const isSubscribed = (): boolean => {
    return subscriptionStatus?.active === true && currentPlan !== SUBSCRIPTION_TIERS.FREE;
  };

  const value = {
    subscriptionStatus,
    loading,
    refreshSubscription,
    hasAccess,
    isSubscribed,
    currentPlan,
  };

  return (
    <SubscriptionContext.Provider value={value}>
      {children}
    </SubscriptionContext.Provider>
  );
};

// Custom hook to use the subscription context
export const useSubscription = (): SubscriptionContextProps => {
  const context = useContext(SubscriptionContext);
  if (context === undefined) {
    throw new Error('useSubscription must be used within a SubscriptionProvider');
  }
  return context;
};
