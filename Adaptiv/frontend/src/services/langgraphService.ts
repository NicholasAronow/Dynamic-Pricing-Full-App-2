import api from './api';

// Types
export interface AgentResult {
  agent_name: string;
  result: string;
  confidence: number;
  execution_time: number;
  metadata: Record<string, any>;
}

export interface MultiAgentResponse {
  final_result: string;
  execution_path: string[];
  total_execution_time: number;
  metadata: Record<string, any>;
  messages: Array<Record<string, any>>;
}

export interface MultiAgentRequest {
  task: string;
  context?: string;
  architecture: 'supervisor' | 'swarm';
  previous_messages?: Array<{role: string; content: string}>;
}

export interface ArchitectureInfo {
  name: string;
  title: string;
  description: string;
  agents: string[];
  best_for: string;
}

export interface HealthCheckResponse {
  status: string;
  service: string;
  architectures_available: string[];
}

export interface TestResponse {
  status: string;
  test_completed: boolean;
  execution_time: number;
  agents_executed: number;
  sample_result: string;
}

class LangGraphService {
  private baseUrl = 'langgraph';

  /**
   * Execute a multi-agent task
   */
  async executeTask(request: MultiAgentRequest): Promise<MultiAgentResponse> {
    try {
      const response = await api.post(`${this.baseUrl}/execute`, request);
      return response.data;
    } catch (error: any) {
      console.error('Error executing multi-agent task:', error);
      throw new Error(error.response?.data?.detail || 'Failed to execute task');
    }
  }

  /**
   * Get available architectures
   */
  async getArchitectures(): Promise<ArchitectureInfo[]> {
    try {
      const response = await api.get(`${this.baseUrl}/architectures`);
      return response.data;
    } catch (error: any) {
      console.error('Error getting architectures:', error);
      throw new Error(error.response?.data?.detail || 'Failed to get architectures');
    }
  }

  /**
   * Health check
   */
  async healthCheck(): Promise<HealthCheckResponse> {
    try {
      const response = await api.get(`${this.baseUrl}/health`);
      return response.data;
    } catch (error: any) {
      console.error('Error checking health:', error);
      throw new Error(error.response?.data?.detail || 'Health check failed');
    }
  }

  /**
   * Test the multi-agent system
   */
  async testSystem(): Promise<TestResponse> {
    try {
      const response = await api.post(`${this.baseUrl}/test`);
      return response.data;
    } catch (error: any) {
      console.error('Error testing system:', error);
      throw new Error(error.response?.data?.detail || 'System test failed');
    }
  }

  /**
   * Execute a research task using supervisor architecture
   */
  async executeResearchTask(query: string, context?: string): Promise<MultiAgentResponse> {
    return this.executeTask({
      task: `Research and analyze: ${query}`,
      context: context || '',
      architecture: 'supervisor'
    });
  }

  /**
   * Execute an analysis task using swarm architecture
   */
  async executeAnalysisTask(data: string, context?: string): Promise<MultiAgentResponse> {
    return this.executeTask({
      task: `Analyze this data and provide insights: ${data}`,
      context: context || '',
      architecture: 'swarm'
    });
  }

  /**
   * Get recommendations using supervisor architecture
   */
  async getRecommendations(problem: string, context?: string): Promise<MultiAgentResponse> {
    return this.executeTask({
      task: `Provide recommendations for: ${problem}`,
      context: context || '',
      architecture: 'supervisor'
    });
  }

  /**
   * Format agent results for display
   */
  formatResults(response: MultiAgentResponse): {
    summary: string;
    executionPath: string;
    totalTime: string;
    messageCount: number;
    architecture: string;
  } {
    return {
      summary: response.final_result,
      executionPath: response.execution_path.join(' → '),
      totalTime: `${response.total_execution_time.toFixed(2)}s`,
      messageCount: response.messages.length,
      architecture: response.metadata.architecture || 'unknown'
    };
  }

  /**
   * Stream multi-agent task execution with real-time updates
   */
  async *streamTask(request: MultiAgentRequest): AsyncGenerator<any, void, unknown> {
    try {
      const token = localStorage.getItem('token');
      
      // Use the same base URL as your api instance
      const baseURL = api.defaults.baseURL || '';
      const url = `${baseURL}${this.baseUrl}/stream`;
      
      console.log('Streaming URL:', url); // Debug log
      
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': token ? `Bearer ${token}` : ''
        },
        body: JSON.stringify(request)
      });
  
      if (!response.ok) {
        const errorText = await response.text();
        console.error('Stream response error:', errorText);
        throw new Error(`HTTP error! status: ${response.status}`);
      }
  
      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No response body reader available');
      }
  
      const decoder = new TextDecoder();
      let buffer = '';
  
      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
  
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || ''; // Keep incomplete line in buffer
  
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6).trim(); // Remove 'data: ' prefix and trim
              if (data) {
                try {
                  const parsed = JSON.parse(data);
                  yield parsed;
                } catch (e) {
                  console.warn('Failed to parse SSE data:', data, e);
                }
              }
            }
          }
        }
      } finally {
        reader.releaseLock();
      }
    } catch (error: any) {
      console.error('Error streaming task:', error);
      throw new Error(error.message || 'Failed to stream task');
    }
  }

  /**
   * Get architecture recommendations based on task type
   */
  getArchitectureRecommendation(taskType: 'pricing' | 'market_analysis' | 'comprehensive' | 'flexible'): {
    architecture: 'supervisor' | 'swarm';
    reason: string;
  } {
    switch (taskType) {
      case 'pricing':
        return {
          architecture: 'supervisor',
          reason: 'Structured pricing analysis benefits from sequential market → data → strategy workflow'
        };
      case 'market_analysis':
        return {
          architecture: 'swarm',
          reason: 'Dynamic agent handoffs allow flexible exploration of market conditions'
        };
      case 'comprehensive':
        return {
          architecture: 'supervisor',
          reason: 'Comprehensive analysis requires coordinated multi-agent processing'
        };
      case 'flexible':
        return {
          architecture: 'swarm',
          reason: 'Swarm architecture adapts to task requirements with intelligent handoffs'
        };
      default:
        return {
          architecture: 'supervisor',
          reason: 'Default choice for structured dynamic pricing tasks'
        };
    }
  }
}

export default new LangGraphService();
