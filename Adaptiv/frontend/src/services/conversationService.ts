import api from './api';

// Types
export interface Conversation {
  id: number;
  title?: string;
  created_at: string;
  updated_at: string;
  is_active: boolean;
  message_count?: number;
  participating_agents?: string[];
}

export interface ConversationMessage {
  id: number;
  conversation_id: number;
  role: 'user' | 'assistant';
  content: string;
  agent_name?: string;
  tools_used?: string[];
  created_at: string;
}

export interface ConversationWithMessages {
  conversation: Conversation;
  messages: ConversationMessage[];
}

export interface CreateConversationRequest {
  title?: string;
}

export interface UpdateConversationRequest {
  title: string;
}

export interface CreateMessageRequest {
  role: 'user' | 'assistant';
  content: string;
  agent_name?: string;
  tools_used?: string[];
}

class ConversationService {
  private baseUrl = '/api/conversations';

  /**
   * Create a new conversation
   */
  async createConversation(request: CreateConversationRequest = {}): Promise<Conversation> {
    try {
      const response = await api.post(this.baseUrl, request);
      return response.data;
    } catch (error: any) {
      console.error('Error creating conversation:', error);
      throw new Error(error.response?.data?.detail || 'Failed to create conversation');
    }
  }

  /**
   * Get all conversations for the current user
   */
  async getConversations(limit: number = 50, includeInactive: boolean = false): Promise<Conversation[]> {
    try {
      const response = await api.get(this.baseUrl, {
        params: { limit, include_inactive: includeInactive }
      });
      return response.data;
    } catch (error: any) {
      console.error('Error getting conversations:', error);
      throw new Error(error.response?.data?.detail || 'Failed to get conversations');
    }
  }

  /**
   * Get a specific conversation with its messages
   */
  async getConversation(conversationId: number, messageLimit: number = 100): Promise<ConversationWithMessages> {
    try {
      const response = await api.get(`${this.baseUrl}/${conversationId}`, {
        params: { message_limit: messageLimit }
      });
      return response.data;
    } catch (error: any) {
      console.error('Error getting conversation:', error);
      throw new Error(error.response?.data?.detail || 'Failed to get conversation');
    }
  }

  /**
   * Update a conversation's title
   */
  async updateConversation(conversationId: number, request: UpdateConversationRequest): Promise<Conversation> {
    try {
      const response = await api.put(`${this.baseUrl}/${conversationId}`, request);
      return response.data;
    } catch (error: any) {
      console.error('Error updating conversation:', error);
      throw new Error(error.response?.data?.detail || 'Failed to update conversation');
    }
  }

  /**
   * Delete a conversation
   */
  async deleteConversation(conversationId: number): Promise<void> {
    try {
      await api.delete(`${this.baseUrl}/${conversationId}`);
    } catch (error: any) {
      console.error('Error deleting conversation:', error);
      throw new Error(error.response?.data?.detail || 'Failed to delete conversation');
    }
  }

  /**
   * Archive a conversation
   */
  async archiveConversation(conversationId: number): Promise<Conversation> {
    try {
      const response = await api.post(`${this.baseUrl}/${conversationId}/archive`);
      return response.data;
    } catch (error: any) {
      console.error('Error archiving conversation:', error);
      throw new Error(error.response?.data?.detail || 'Failed to archive conversation');
    }
  }

  /**
   * Add a message to a conversation
   */
  async addMessage(conversationId: number, request: CreateMessageRequest): Promise<ConversationMessage> {
    try {
      const response = await api.post(`${this.baseUrl}/${conversationId}/messages`, request);
      return response.data;
    } catch (error: any) {
      console.error('Error adding message:', error);
      throw new Error(error.response?.data?.detail || 'Failed to add message');
    }
  }

  /**
   * Get conversation context for LangGraph
   */
  async getConversationContext(conversationId: number, contextLimit: number = 10): Promise<any[]> {
    try {
      const response = await api.get(`${this.baseUrl}/${conversationId}/context`, {
        params: { context_limit: contextLimit }
      });
      return response.data.context;
    } catch (error: any) {
      console.error('Error getting conversation context:', error);
      throw new Error(error.response?.data?.detail || 'Failed to get conversation context');
    }
  }

  /**
   * Generate a conversation title based on the first user message
   */
  generateConversationTitle(firstMessage: string): string {
    // Take first 50 characters and add ellipsis if longer
    const maxLength = 50;
    if (firstMessage.length <= maxLength) {
      return firstMessage;
    }
    return firstMessage.substring(0, maxLength).trim() + '...';
  }

  /**
   * Format agent name for display
   */
  formatAgentName(agentName?: string): string {
    if (!agentName) return 'Ada';
    
    const agentDisplayNames: { [key: string]: string } = {
      'pricing_orchestrator': '💼 Pricing Expert',
      'web_researcher': '🔍 Market Researcher',
      'algorithm_selector': '⚙️ Algorithm Specialist',
      'database_agent': '🗄️ Database Specialist'
    };
    
    return agentDisplayNames[agentName] || `🤖 ${agentName}`;
  }

  /**
   * Format tools for display
   */
  formatToolName(toolName: string): string {
    return toolName
      .replace(/_/g, ' ')
      .replace(/\b\w/g, l => l.toUpperCase());
  }

  /**
   * Check if a conversation is recent (within last 24 hours)
   */
  isRecentConversation(conversation: Conversation): boolean {
    const oneDayAgo = new Date();
    oneDayAgo.setDate(oneDayAgo.getDate() - 1);
    return new Date(conversation.updated_at) > oneDayAgo;
  }

  /**
   * Format relative time for display
   */
  formatRelativeTime(dateString: string): string {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffMins < 1) {
      return 'Just now';
    } else if (diffMins < 60) {
      return `${diffMins}m ago`;
    } else if (diffHours < 24) {
      return `${diffHours}h ago`;
    } else if (diffDays < 7) {
      return `${diffDays}d ago`;
    } else {
      return date.toLocaleDateString();
    }
  }

  /**
   * Group conversations by date
   */
  groupConversationsByDate(conversations: Conversation[]): { [key: string]: Conversation[] } {
    const groups: { [key: string]: Conversation[] } = {};
    
    conversations.forEach(conversation => {
      const date = new Date(conversation.updated_at);
      const today = new Date();
      const yesterday = new Date();
      yesterday.setDate(yesterday.getDate() - 1);
      
      let groupKey: string;
      
      if (date.toDateString() === today.toDateString()) {
        groupKey = 'Today';
      } else if (date.toDateString() === yesterday.toDateString()) {
        groupKey = 'Yesterday';
      } else {
        groupKey = date.toLocaleDateString();
      }
      
      if (!groups[groupKey]) {
        groups[groupKey] = [];
      }
      groups[groupKey].push(conversation);
    });
    
    return groups;
  }
}

export default new ConversationService();
