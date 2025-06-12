import React, { useState, useEffect } from 'react';
import { Card, List, Tag, Typography, Spin, Empty, Button, Tooltip, Modal, Form, InputNumber, message, Alert, Badge } from 'antd';
import { 
  CheckCircleOutlined, 
  ClockCircleOutlined, 
  ExclamationCircleOutlined,
  CheckOutlined,
  PlayCircleOutlined,
  InfoCircleOutlined,
  FireOutlined,
  FlagOutlined,
  AlertOutlined,
  DollarOutlined
} from '@ant-design/icons';
import actionItemsService, { ActionItem } from '../../services/actionItemsService';
import competitorService from '../../services/competitorService';
import pricingService from '../../services/pricingService';
import { useNavigate } from 'react-router-dom';
import moment from 'moment';
import cogsService from '../../services/cogsService';

const { Title, Text } = Typography;

// Priority colors for visual indicator
const PRIORITY_COLORS = {
  low: 'green',
  medium: 'blue',
  high: 'red'
};

// Action type icons/colors for visual distinction
const ACTION_TYPE_CONFIG: Record<string, { color: string, label: string }> = {
  integration: { color: 'purple', label: 'Integration' },
  data_entry: { color: 'cyan', label: 'Data Entry' },
  analysis: { color: 'orange', label: 'Analysis' },
  configuration: { color: 'geekblue', label: 'Configuration' },
  other: { color: 'default', label: 'Other' }
};

// Style definitions for our UI components
const styles = {
  actionItemContainer: {
    border: '1px solid #f0f0f0',
    borderRadius: '8px',
    marginBottom: '10px',
    padding: '12px',
    transition: 'all 0.3s ease',
    boxShadow: '0 1px 3px rgba(0,0,0,0.02)',
    cursor: 'pointer',
    backgroundColor: '#fff'
  },
  pulsingDot: (color: string) => ({
    width: '10px',
    height: '10px',
    borderRadius: '50%',
    backgroundColor: color,
    position: 'relative' as const,
    marginRight: '12px'
  }),
  pulsingDotAfter: (color: string) => ({
    content: '""',
    position: 'absolute' as const,
    top: '-4px',
    left: '-4px',
    right: '-4px',
    bottom: '-4px',
    borderRadius: '50%',
    border: `2px solid ${color}`,
    opacity: 0.5,
    animation: 'pulse 2s infinite'
  }),
  actionItemHeader: {
    display: 'flex',
    alignItems: 'center',
    marginBottom: '3px'
  },
  actionItemTitle: {
    fontWeight: 500,
    fontSize: '15px'
  },
  actionTypeTag: {
    marginLeft: 'auto',
    fontSize: '12px',
    border: 'none',
    padding: '0 8px'
  }
};

// Add the pulse animation using a style element
const PulseAnimation = () => {
  return (
    <style>
      {`
        @keyframes pulse {
          0% {
            transform: scale(0.8);
            opacity: 0.5;
          }
          70% {
            transform: scale(1.2);
            opacity: 0;
          }
          100% {
            transform: scale(0.8);
            opacity: 0;
          }
        }
        .action-item-container:hover {
          background: #f9f9f9;
          box-shadow: 0 2px 6px rgba(0,0,0,0.06);
        }

        /* Enhanced animation for red dots */
        .red-dot {
          animation: glow 1.5s ease-in-out infinite alternate;
        }
        
        @keyframes glow {
          from { box-shadow: 0 0 2px rgba(255, 0, 0, 0.5); }
          to { box-shadow: 0 0 10px rgba(255, 0, 0, 0.8); }
        }
        
        .pulsing-dot::after {
          content: '';
          position: absolute;
          top: -4px;
          left: -4px;
          right: -4px;
          bottom: -4px;
          border-radius: 50%;
          opacity: 0.5;
          animation: pulse 2s infinite;
        }
      `}
    </style>
  );
};

// Interface for conditional action items that don't exist in the database
interface ConditionalActionItem {
  id: string; // String ID to differentiate from number IDs in the database
  title: string;
  description: string;
  priority: string;
  status: string;
  action_type: string;
  conditional: boolean; // Flag to identify this as a conditional item
  route?: string; // Optional route to navigate to when clicked
}

const ActionItemsCard: React.FC = () => {
  const [actionItems, setActionItems] = useState<(ActionItem | ConditionalActionItem)[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [cogsModalVisible, setCogsModalVisible] = useState<boolean>(false);
  const [currentActionItemId, setCurrentActionItemId] = useState<number | null>(null);
  const [cogsSubmitting, setCogsSubmitting] = useState<boolean>(false);
  const [hasCompetitorsSet, setHasCompetitorsSet] = useState<boolean>(true); // Default to true to avoid showing the to-do item until we know
  const [hasPendingRecommendations, setHasPendingRecommendations] = useState<boolean>(false);
  const [form] = Form.useForm();
  const navigate = useNavigate();
  
  useEffect(() => {
    const fetchActionItems = async () => {
      try {
        setLoading(true);
        
        // Check if competitors are set up
        try {
          const competitors = await competitorService.getCompetitors();
          // If no competitors or the array is empty, competitors are not set up
          setHasCompetitorsSet(competitors && competitors.length > 0);
        } catch (err) {
          console.error('Error checking competitor status:', err);
          // Default to true to avoid showing incorrect to-do item on error
          setHasCompetitorsSet(true);
        }
        
        // Check if there are pending price recommendations
        try {
          const recommendations = await pricingService.getAgentRecommendations();
          // Check if there are any recommendations without a user_action
          const pending = recommendations.filter(rec => !rec.user_action);
          setHasPendingRecommendations(pending.length > 0);
        } catch (err) {
          console.error('Error checking pricing recommendations:', err);
          // Default to false to avoid showing incorrect to-do item on error
          setHasPendingRecommendations(false);
        }
        
        // Fetch regular action items from the database
        const items = await actionItemsService.getActionItems();
        // Filter to only show non-completed items on the dashboard
        const pendingItems = items.filter(item => item.status !== 'completed');
        
        // Create conditional items based on our checks
        const conditionalItems: ConditionalActionItem[] = [];
        
        // Add competitor setup to-do if needed
        if (!hasCompetitorsSet) {
          conditionalItems.push({
            id: 'setup-competitors',
            title: 'Set up competitors',
            description: 'Add competitor information to enable competitive analysis',
            priority: 'high',
            status: 'pending',
            action_type: 'configuration',
            conditional: true,
            route: '/competitors'
          });
        }
        
        // Add price recommendation review to-do if needed
        if (hasPendingRecommendations) {
          conditionalItems.push({
            id: 'review-price-recommendations',
            title: 'Review new price recommendations',
            description: 'Review and approve or reject pending price changes',
            priority: 'high',
            status: 'pending',
            action_type: 'analysis',
            conditional: true,
            route: '/agents'
          });
        }
        
        // Combine database and conditional items
        setActionItems([...pendingItems, ...conditionalItems]);
        setError(null);
      } catch (err) {
        console.error('Error fetching action items:', err);
        setError('Failed to load action items');
      } finally {
        setLoading(false);
      }
    };
    
    fetchActionItems();
  }, [hasCompetitorsSet, hasPendingRecommendations]);
  
  const handleComplete = async (id: number | string) => {
    try {
      // For conditional items (string IDs), just remove them from state
      if (typeof id === 'string') {
        setActionItems(prevItems => prevItems.filter(item => item.id !== id));
        return;
      }
      
      // For database items (number IDs), call the API
      await actionItemsService.completeActionItem(id as number);
      // Update the local state
      setActionItems(prevItems => prevItems.filter(item => item.id !== id));
    } catch (err) {
      console.error('Error completing action item:', err);
    }
  };
  
  const handleStart = async (id: number | string) => {
    try {
      // Handle conditional items (string IDs)
      if (typeof id === 'string') {
        // For conditional items, just update the status locally
        setActionItems(prevItems =>
          prevItems.map(item => item.id === id ? {...item, status: 'in_progress'} : item)
        );
        return;
      }
      
      // For database items (number IDs), call the API
      const updatedItem = await actionItemsService.startActionItem(id as number);
      // Update the local state
      setActionItems(prevItems => 
        prevItems.map(item => item.id === id ? updatedItem : item)
      );
    } catch (err) {
      console.error('Error starting action item:', err);
    }
  };
  
  // Helper function to get priority color
  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high':
        return '#f5222d';
      case 'medium':
        return '#faad14';
      case 'low':
        return '#1890ff';
      default:
        return '#8c8c8c';
    }
  };
  
  const handleCogsModalOpen = (itemId: number | string | null) => {
    // Only proceed if we have a numeric ID
    if (itemId === null || typeof itemId === 'string') return;
    setCurrentActionItemId(itemId);
    setCogsModalVisible(true);
  };
  
  const handleCogsModalClose = () => {
    setCogsModalVisible(false);
    form.resetFields();
  };
  
  const handleCogsSubmit = async (values: { amount: number }) => {
    if (!currentActionItemId) return;
    
    try {
      setCogsSubmitting(true);
      const success = await cogsService.submitCOGS(values.amount);
      
      if (success) {
        message.success('Cost of goods sold data submitted successfully!');
        
        // Mark the action item as completed
        await handleComplete(currentActionItemId);
        
        // Close the modal
        handleCogsModalClose();
      } else {
        message.error('Failed to submit cost of goods sold data. Please try again.');
      }
    } catch (error) {
      console.error('Error submitting COGS:', error);
      message.error('An error occurred while submitting data.');
    } finally {
      setCogsSubmitting(false);
    }
  };
  
  // Helper to check if an action item is the COGS entry item
  const isCogsActionItem = (item: ActionItem | ConditionalActionItem) => {
    return item.title === "Enter COGS for current week" && item.action_type === "data_entry";
  };
  
  const renderActionItem = (item: ActionItem | ConditionalActionItem) => {
    const actionTypeConfig = ACTION_TYPE_CONFIG[item.action_type] || ACTION_TYPE_CONFIG.other;
    const isCogs = isCogsActionItem(item);
    const priorityColor = getPriorityColor(item.priority);
    
    return (
      <List.Item
        key={item.id}
        style={styles.actionItemContainer}
        className="action-item-container"
        actions={[
          item.status === 'in_progress' && (
            <Tooltip title="Mark as complete">
              <Button 
                type="text" 
                icon={<CheckOutlined />} 
                onClick={(e) => {
                  e.stopPropagation();
                  handleComplete(item.id);
                }}
              />
            </Tooltip>
          )
        ]}
        onClick={() => {
          if (isCogs) {
            // Only call handleCogsModalOpen if item.id is a number
            if (typeof item.id === 'number') {
              handleCogsModalOpen(item.id);
            }
          } else if ('conditional' in item && item.route) {
            // For conditional items with routes, navigate to that route
            navigate(item.route);
          } else {
            // For regular database items
            navigate(`/action-items/${item.id}`);
          }
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', width: '100%' }}>
          {/* Pulsing dot with CSS animation */}
          <div 
            style={styles.pulsingDot(priorityColor)} 
            className={`pulsing-dot ${item.priority === 'high' ? 'red-dot' : ''}`} 
          />
          
          <div style={{ flex: 1 }}>
            <div style={styles.actionItemHeader}>
              <Text strong style={styles.actionItemTitle}>{item.title}</Text>
            </div>
            
            <Text type="secondary" style={{ fontSize: '13px', display: 'block', marginBottom: '8px' }}>
              {item.description}
            </Text>
            
            <div>
            </div>
          </div>
        </div>
      </List.Item>
    );
  };
  
  // Get the current week's date range for display in COGS modal
  const weekStart = moment().startOf('week').format('MMM D');
  const weekEnd = moment().endOf('week').format('MMM D, YYYY');
  const weekRange = `${weekStart} - ${weekEnd}`;
  
  // Create extra button for the card header (if needed)
  const extraButton = null;

  return (
    <>
      <PulseAnimation />
      <Card 
        title={
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <span>To-Do Items</span>
            {actionItems.length > 0 && (
              <Badge 
                count={actionItems.length} 
                style={{ 
                  backgroundColor: '#f5222d',
                  marginLeft: '8px',
                  boxShadow: '0 0 0 1px #fff'
                }} 
              />
            )}
          </div>
        }
        extra={extraButton} 
        className="dashboard-card" 
        bordered={false} 
        headStyle={{ backgroundColor: '#fff' }}
        style={{ 
          backgroundColor: 'transparent',
          border: '1.2px solid rgb(238, 238, 238)',
          boxShadow: 'none',
        }}
        bodyStyle={{ padding: '16px', backgroundColor: 'transparent' }}
      >
        <div style={{ 
          flex: 1, 
          display: 'flex', 
          flexDirection: 'column', 
          minHeight: '350px',
          overflowY: 'auto',
          scrollbarWidth: 'thin'
        }}>
          {loading ? (
            <div style={{ flex: 1, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
              <Spin size="large" />
            </div>
          ) : error ? (
            <Alert message={error} type="error" showIcon />
          ) : actionItems.length === 0 ? (
            <Empty description="No action items" style={{ margin: 'auto' }} />
          ) : (
            <List
              dataSource={actionItems}
              renderItem={renderActionItem}
              style={{ flex: 1 }}
            />
          )}
        </div>
      </Card>
      
      {/* COGS Entry Modal */}
      <Modal
        title={<Typography.Title level={4} style={{ margin: 0 }}>Enter Weekly Cost of Goods Sold</Typography.Title>}
        open={cogsModalVisible}
        onCancel={handleCogsModalClose}
        footer={null}
        width={500}
      >
        <div style={{ marginBottom: '20px' }}>
          <Typography.Text>Please enter your total cost of goods sold for the current week:</Typography.Text>
          <div style={{ marginTop: '8px' }}>
            <Typography.Text strong>{weekRange}</Typography.Text>
          </div>
        </div>
        
        <Form
          form={form}
          layout="vertical"
          onFinish={handleCogsSubmit}
        >
          <Form.Item
            name="amount"
            label="Total COGS Amount"
            rules={[{ required: true, message: 'Please enter the COGS amount' }]}
          >
            <InputNumber
              prefix={<DollarOutlined />}
              style={{ width: '100%' }}
              min={0}
              step={100}
              placeholder="Enter amount"
              stringMode
            />
          </Form.Item>
          
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '20px' }}>
            <Button onClick={handleCogsModalClose}>Cancel</Button>
            <Button type="primary" htmlType="submit" loading={cogsSubmitting}>Submit</Button>
          </div>
        </Form>
      </Modal>
    </>
  );
};

export default ActionItemsCard;
