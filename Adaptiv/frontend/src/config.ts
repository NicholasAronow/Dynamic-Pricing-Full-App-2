// Type declarations for configuration values
export type RequestHeaders = {
  'Content-Type': string;
  'Accept': string;
};

export type FeatureFlags = {
  AGENTS_ENABLED: boolean;
  EXPERIMENTS_ENABLED: boolean;
  COMPETITOR_ANALYSIS_ENABLED: boolean;
};

export type AgentConfig = {
  POLL_INTERVAL: number;
  MAX_POLL_TIME: number;
};

// API configuration
export const API_BASE_URL: string = process.env.REACT_APP_API_URL || 'http://localhost:8001';

// Authentication configuration
export const TOKEN_KEY: string = 'auth_token';
export const USER_KEY: string = 'user_data';

// Request configuration
export const DEFAULT_TIMEOUT: number = 30000; // 30 seconds
export const REQUEST_HEADERS: RequestHeaders = {
  'Content-Type': 'application/json',
  'Accept': 'application/json'
};

// Application information
export const APP_VERSION: string = '1.0.0';
export const APP_NAME: string = 'Adaptiv Dynamic Pricing';

// Feature flags
export const FEATURES: FeatureFlags = {
  AGENTS_ENABLED: true,
  EXPERIMENTS_ENABLED: true,
  COMPETITOR_ANALYSIS_ENABLED: true,
};

// Agent configuration
export const AGENT_CONFIG: AgentConfig = {
  POLL_INTERVAL: 10000, // 10 seconds
  MAX_POLL_TIME: 600000, // 10 minutes
};

