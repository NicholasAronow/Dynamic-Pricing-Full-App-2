// Type declarations for config module
declare module 'config' {
  // API configuration
  export const API_BASE_URL: string;

  // Authentication configuration
  export const TOKEN_KEY: string;
  export const USER_KEY: string;

  // Request configuration
  export const DEFAULT_TIMEOUT: number;
  export const REQUEST_HEADERS: {
    'Content-Type': string;
    'Accept': string;
  };

  // Application information
  export const APP_VERSION: string;
  export const APP_NAME: string;

  // Feature flags
  export const FEATURES: {
    AGENTS_ENABLED: boolean;
    EXPERIMENTS_ENABLED: boolean;
    COMPETITOR_ANALYSIS_ENABLED: boolean;
  };

  // Agent configuration
  export const AGENT_CONFIG: {
    POLL_INTERVAL: number;
    MAX_POLL_TIME: number;
  };
}
