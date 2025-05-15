import React, { useState, useEffect } from 'react';
import { Card, List, Tag, Typography, Spin, Empty, Button, Tooltip, Modal, Form, InputNumber, message } from 'antd';
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

const ActionItemsCard: React.FC = () => {
  const [actionItems, setActionItems] = useState<ActionItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [cogsModalVisible, setCogsModalVisible] = useState<boolean>(false);
  const [currentActionItemId, setCurrentActionItemId] = useState<number | null>(null);
  const [cogsSubmitting, setCogsSubmitting] = useState<boolean>(false);
  const [form] = Form.useForm();
  const navigate = useNavigate();
  
  useEffect(() => {
    const fetchActionItems = async () => {
      try {
        setLoading(true);
        const items = await actionItemsService.getActionItems();
        // Filter to only show non-completed items on the dashboard
        const pendingItems = items.filter(item => item.status !== 'completed');
        setActionItems(pendingItems);
        setError(null);
      } catch (err) {
        console.error('Error fetching action items:', err);
        setError('Failed to load action items');
      } finally {
        setLoading(false);
      }
    };
    
    fetchActionItems();
  }, []);
  
  const handleComplete = async (id: number) => {
    try {
      await actionItemsService.completeActionItem(id);
      // Update the local state
      setActionItems(prevItems => prevItems.filter(item => item.id !== id));
    } catch (err) {
      console.error('Error completing action item:', err);
    }
  };
  
  const handleStart = async (id: number) => {
    try {
      const updatedItem = await actionItemsService.startActionItem(id);
      // Update the local state
      setActionItems(prevItems => 
        prevItems.map(item => item.id === id ? updatedItem : item)
      );
    } catch (err) {
      console.error('Error starting action item:', err);
    }
  };
  
  const getPriorityIcon = (priority: string) => {
    switch (priority) {
      case 'medium':
        return (
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center', 
            background: '#ffe7e7', 
            width: 32, 
            height: 32, 
            borderRadius: '50%', 
            border: '1px solid #ffa39e' 
          }}>
            <FireOutlined style={{ color: '#f5222d', fontSize: 16 }} />
          </div>
        );
      case 'high':
        return (
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center', 
            background: '#e6f7ff', 
            width: 32, 
            height: 32, 
            borderRadius: '50%', 
            border: '1px solid #91d5ff' 
          }}>
            <FlagOutlined style={{ color: '#1890ff', fontSize: 16 }} />
          </div>
        );
      case 'low':
        return (
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center', 
            background: '#f6ffed', 
            width: 32, 
            height: 32, 
            borderRadius: '50%', 
            border: '1px solid #b7eb8f' 
          }}>
            <InfoCircleOutlined style={{ color: '#52c41a', fontSize: 16 }} />
          </div>
        );
      default:
        return <InfoCircleOutlined />;
    }
  };
  
  // Handle opening the COGS modal
  const handleCogsModalOpen = (itemId: number) => {
    setCurrentActionItemId(itemId);
    setCogsModalVisible(true);
  };
  
  // Handle closing the COGS modal
  const handleCogsModalClose = () => {
    setCogsModalVisible(false);
    form.resetFields();
  };
  
  // Handle submitting COGS data
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
  const isCogsActionItem = (item: ActionItem) => {
    return item.title === "Enter COGS for current week" && item.action_type === "data_entry";
  };
  
  const renderActionItem = (item: ActionItem) => {
    const actionTypeConfig = ACTION_TYPE_CONFIG[item.action_type] || ACTION_TYPE_CONFIG.other;
    const isCogs = isCogsActionItem(item);
    
    return (
      <List.Item
        key={item.id}
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
        className="action-item-list-item"
        style={{ cursor: 'pointer', transition: 'background 0.3s ease' }}
        onClick={() => {
          if (isCogs) {
            handleCogsModalOpen(item.id);
          } else {
            navigate(`/action-items/${item.id}`);
          }
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.background = '#f5f5f5';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = 'transparent';
        }}
      >
        <List.Item.Meta
          avatar={getPriorityIcon(item.priority)}
          title={<Text strong>{item.title}</Text>}
          description={
            <div>
              <Text type="secondary" ellipsis style={{ maxWidth: '100%' }}>
                {item.description || 'No description available'}
              </Text>
              {item.status === 'in_progress' && <Tag color="processing" style={{ marginTop: 4 }}>In Progress</Tag>}
            </div>
          }
        />
      </List.Item>
    );
  };
  
  // Get the current week's date range for display in COGS modal
  const weekStart = moment().startOf('week').format('MMM D');
  const weekEnd = moment().endOf('week').format('MMM D, YYYY');
  const weekRange = `${weekStart} - ${weekEnd}`;
  
  return (
    <>
      <Card 
        title={
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>To-Do Items</span>
          </div>
        }
        className="action-items-card"
        style={{ height: '100%' }}
      >
      {loading ? (
        <div style={{ height: '100%', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
          <Spin />
        </div>
      ) : error ? (
        <div style={{ textAlign: 'center', padding: '20px' }}>
          <Text type="danger">{error}</Text>
        </div>
      ) : actionItems.length === 0 ? (
        <Empty 
          description="No action items" 
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      ) : (
        <List
          itemLayout="horizontal"
          dataSource={actionItems}
          renderItem={renderActionItem}
          style={{ 
            maxHeight: '260px', 
            overflowY: 'auto',
            scrollbarWidth: 'thin'
          }}
        />
      )}
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
