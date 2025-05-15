import api from './api';

export interface ActionItem {
  id: number;
  title: string;
  description: string | null;
  priority: 'low' | 'medium' | 'high';
  status: 'pending' | 'in_progress' | 'completed';
  action_type: 'integration' | 'data_entry' | 'analysis' | 'configuration' | 'other';
  created_at: string;
  updated_at: string | null;
  completed_at: string | null;
  user_id: number;
}

export interface ActionItemCreate {
  title: string;
  description?: string;
  priority?: 'low' | 'medium' | 'high';
  status?: 'pending' | 'in_progress' | 'completed';
  action_type?: 'integration' | 'data_entry' | 'analysis' | 'configuration' | 'other';
}

export interface ActionItemUpdate {
  title?: string;
  description?: string;
  priority?: 'low' | 'medium' | 'high';
  status?: 'pending' | 'in_progress' | 'completed';
  action_type?: 'integration' | 'data_entry' | 'analysis' | 'configuration' | 'other';
}

const actionItemsService = {
  /**
   * Get all action items for the current user
   */
  getActionItems: async (): Promise<ActionItem[]> => {
    const response = await api.get('/api/action-items');
    return response.data;
  },

  /**
   * Create a new action item
   */
  createActionItem: async (actionItem: ActionItemCreate): Promise<ActionItem> => {
    const response = await api.post('/api/action-items', actionItem);
    return response.data;
  },

  /**
   * Update an action item
   */
  updateActionItem: async (id: number, actionItem: ActionItemUpdate): Promise<ActionItem> => {
    const response = await api.put(`/api/action-items/${id}`, actionItem);
    return response.data;
  },

  /**
   * Delete an action item
   */
  deleteActionItem: async (id: number): Promise<void> => {
    await api.delete(`/api/action-items/${id}`);
  },

  /**
   * Mark an action item as completed
   */
  completeActionItem: async (id: number): Promise<ActionItem> => {
    return await actionItemsService.updateActionItem(id, { status: 'completed' });
  },

  /**
   * Mark an action item as in progress
   */
  startActionItem: async (id: number): Promise<ActionItem> => {
    return await actionItemsService.updateActionItem(id, { status: 'in_progress' });
  }
};

export default actionItemsService;
