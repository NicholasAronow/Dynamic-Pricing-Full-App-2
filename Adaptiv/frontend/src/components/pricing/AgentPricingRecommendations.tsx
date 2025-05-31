import React, { useEffect, useState } from 'react';
import {
  Card, 
  Table, 
  Button, 
  Space, 
  Typography, 
  Badge, 
  Tooltip, 
  Modal, 
  Input, 
  Row, 
  Col,
  Statistic,
  Tabs,
  Tag,
  notification
} from 'antd';
import { 
  CheckCircleOutlined, 
  CloseCircleOutlined, 
  QuestionCircleOutlined, 
  ArrowUpOutlined, 
  ArrowDownOutlined, 
  CalendarOutlined 
} from '@ant-design/icons';
import pricingService, { AgentPricingRecommendation } from '../../services/pricingService';
import { useNavigate } from 'react-router-dom';
import dayjs from 'dayjs';

const { TabPane } = Tabs;
const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

interface FeedbackModalProps {
  visible: boolean;
  recommendation: AgentPricingRecommendation | null;
  action: 'accept' | 'reject';
  onSubmit: (action: 'accept' | 'reject', feedback: string) => void;
  onCancel: () => void;
}

const FeedbackModal: React.FC<FeedbackModalProps> = ({ 
  visible, 
  recommendation, 
  action, 
  onSubmit, 
  onCancel 
}) => {
  const [feedback, setFeedback] = useState('');

  useEffect(() => {
    if (visible) {
      setFeedback(''); // Reset feedback when modal opens
    }
  }, [visible]);

  return (
    <Modal
      title={action === 'accept' ? 'Accept Price Recommendation' : 'Reject Price Recommendation'}
      open={visible}
      onCancel={onCancel}
      footer={[
        <Button key="back" onClick={onCancel}>
          Cancel
        </Button>,
        <Button 
          key="submit" 
          type="primary" 
          onClick={() => onSubmit(action, feedback)}
        >
          {action === 'accept' ? 'Accept' : 'Reject'}
        </Button>,
      ]}
    >
      {recommendation && (
        <>
          <p>
            <strong>Item:</strong> {recommendation.item_name}<br />
            <strong>Current Price:</strong> ${recommendation.current_price.toFixed(2)}<br />
            <strong>Recommended Price:</strong> ${recommendation.recommended_price.toFixed(2)}<br />
            <strong>Change:</strong> ${recommendation.price_change_amount.toFixed(2)} ({(recommendation.price_change_percent * 100).toFixed(1)}%)
          </p>
          <div style={{ marginBottom: 16 }}>
            <Text type="secondary">Please provide any feedback or reasoning (optional):</Text>
            <TextArea
              rows={4}
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              placeholder="Add your feedback here..."
            />
          </div>
        </>
      )}
    </Modal>
  );
};

const AgentPricingRecommendations: React.FC = () => {
  const [recommendations, setRecommendations] = useState<AgentPricingRecommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [feedbackModal, setFeedbackModal] = useState<{
    visible: boolean;
    recommendation: AgentPricingRecommendation | null;
    action: 'accept' | 'reject';
  }>({
    visible: false,
    recommendation: null,
    action: 'accept'
  });
  const [activeTab, setActiveTab] = useState('pending');
  
  const navigate = useNavigate();

  const fetchRecommendations = async (status?: string) => {
    setLoading(true);
    try {
      const data = await pricingService.getAgentRecommendations(status);
      setRecommendations(data);
    } catch (error) {
      console.error('Error fetching agent recommendations:', error);
      notification.error({
        message: 'Error',
        description: 'Failed to load pricing recommendations',
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRecommendations(activeTab !== 'all' ? activeTab : undefined);
  }, [activeTab]);

  const handleActionClick = (recommendation: AgentPricingRecommendation, action: 'accept' | 'reject') => {
    setFeedbackModal({
      visible: true,
      recommendation,
      action
    });
  };

  const handleFeedbackSubmit = async (action: 'accept' | 'reject', feedback: string) => {
    if (!feedbackModal.recommendation) return;
    
    try {
      const updatedRecommendation = await pricingService.updateRecommendationAction(
        feedbackModal.recommendation.id,
        action,
        feedback
      );
      
      if (updatedRecommendation) {
        notification.success({
          message: 'Success',
          description: `Successfully ${action === 'accept' ? 'accepted' : 'rejected'} the price recommendation.`,
        });
        
        // Update recommendations list
        fetchRecommendations(activeTab !== 'all' ? activeTab : undefined);
      }
    } catch (error) {
      console.error('Error updating recommendation:', error);
      notification.error({
        message: 'Error',
        description: `Failed to ${action} recommendation.`,
      });
    }
    
    // Close modal
    setFeedbackModal({
      visible: false,
      recommendation: null,
      action: 'accept'
    });
  };

  const getStatusBadge = (status: string, userAction: string | null) => {
    if (userAction === 'accept') {
      return <Badge status="success" text="Accepted" />;
    } else if (userAction === 'reject') {
      return <Badge status="error" text="Rejected" />;
    } else if (status === 'pending') {
      return <Badge status="processing" text="Pending" />;
    } else if (status === 'implemented') {
      return <Badge status="success" text="Implemented" />;
    } else {
      return <Badge status="default" text={status} />;
    }
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'N/A';
    return dayjs(dateString).format('MMM D, YYYY');
  };

  const columns = [
    {
      title: 'Item',
      dataIndex: 'item_name',
      key: 'item_name',
      render: (text: string, record: AgentPricingRecommendation) => (
        <a onClick={() => navigate(`/products/${record.item_id}`)}>{text}</a>
      ),
    },
    {
      title: 'Current Price',
      dataIndex: 'current_price',
      key: 'current_price',
      render: (price: number) => `$${price.toFixed(2)}`,
    },
    {
      title: 'Recommended Price',
      dataIndex: 'recommended_price',
      key: 'recommended_price',
      render: (price: number) => `$${price.toFixed(2)}`,
    },
    {
      title: 'Change',
      dataIndex: 'price_change_amount',
      key: 'price_change_amount',
      render: (amount: number, record: AgentPricingRecommendation) => {
        const isPositive = amount >= 0;
        return (
          <Text type={isPositive ? 'success' : 'danger'}>
            {isPositive ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
            ${Math.abs(amount).toFixed(2)} ({(record.price_change_percent * 100).toFixed(1)}%)
          </Text>
        );
      },
    },
    {
      title: 'Confidence',
      dataIndex: 'confidence_score',
      key: 'confidence_score',
      render: (score: number) => {
        let color = 'green';
        if (score < 0.5) color = 'red';
        else if (score < 0.7) color = 'orange';
        
        return (
          <Tag color={color}>
            {(score * 100).toFixed(0)}%
          </Tag>
        );
      },
    },
    {
      title: 'Reevaluation Date',
      dataIndex: 'reevaluation_date',
      key: 'reevaluation_date',
      render: (date: string | null) => (
        <span>
          <CalendarOutlined style={{ marginRight: 5 }} />
          {formatDate(date)}
        </span>
      ),
    },
    {
      title: 'Status',
      dataIndex: 'implementation_status',
      key: 'implementation_status',
      render: (status: string, record: AgentPricingRecommendation) => 
        getStatusBadge(status, record.user_action),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (text: string, record: AgentPricingRecommendation) => {
        // Only show action buttons for pending recommendations
        if (record.user_action) {
          return null;
        }
        
        return (
          <Space size="small">
            <Button
              type="primary"
              icon={<CheckCircleOutlined />}
              size="small"
              onClick={() => handleActionClick(record, 'accept')}
            >
              Accept
            </Button>
            <Button
              danger
              icon={<CloseCircleOutlined />}
              size="small"
              onClick={() => handleActionClick(record, 'reject')}
            >
              Reject
            </Button>
          </Space>
        );
      },
    },
  ];

  const tabChange = (key: string) => {
    setActiveTab(key);
  };

  return (
    <div style={{ padding: '20px 0' }}>
      <Card>
        <Title level={3}>
          Agent Pricing Recommendations
          <Tooltip title="These recommendations are generated by our AI pricing agents based on your business data, market conditions, and competitive analysis.">
            <QuestionCircleOutlined style={{ fontSize: '16px', marginLeft: '8px' }} />
          </Tooltip>
        </Title>
        
        <Tabs activeKey={activeTab} onChange={tabChange}>
          <TabPane tab="Pending" key="pending">
            <Table 
              dataSource={recommendations} 
              columns={columns} 
              rowKey="id" 
              loading={loading}
              expandable={{
                expandedRowRender: record => (
                  <div style={{ padding: '0 20px' }}>
                    <Title level={5}>Rationale</Title>
                    <Paragraph>{record.rationale}</Paragraph>
                    
                    {record.user_feedback && (
                      <>
                        <Title level={5}>Your Feedback</Title>
                        <Paragraph>{record.user_feedback}</Paragraph>
                      </>
                    )}
                  </div>
                ),
              }}
            />
          </TabPane>
          <TabPane tab="Accepted" key="approved">
            <Table 
              dataSource={recommendations} 
              columns={columns} 
              rowKey="id" 
              loading={loading}
              expandable={{
                expandedRowRender: record => (
                  <div style={{ padding: '0 20px' }}>
                    <Title level={5}>Rationale</Title>
                    <Paragraph>{record.rationale}</Paragraph>
                    
                    {record.user_feedback && (
                      <>
                        <Title level={5}>Your Feedback</Title>
                        <Paragraph>{record.user_feedback}</Paragraph>
                      </>
                    )}
                  </div>
                ),
              }}
            />
          </TabPane>
          <TabPane tab="Rejected" key="rejected">
            <Table 
              dataSource={recommendations} 
              columns={columns} 
              rowKey="id" 
              loading={loading}
              expandable={{
                expandedRowRender: record => (
                  <div style={{ padding: '0 20px' }}>
                    <Title level={5}>Rationale</Title>
                    <Paragraph>{record.rationale}</Paragraph>
                    
                    {record.user_feedback && (
                      <>
                        <Title level={5}>Your Feedback</Title>
                        <Paragraph>{record.user_feedback}</Paragraph>
                      </>
                    )}
                  </div>
                ),
              }}
            />
          </TabPane>
          <TabPane tab="All Recommendations" key="all">
            <Table 
              dataSource={recommendations} 
              columns={columns} 
              rowKey="id" 
              loading={loading}
              expandable={{
                expandedRowRender: record => (
                  <div style={{ padding: '0 20px' }}>
                    <Title level={5}>Rationale</Title>
                    <Paragraph>{record.rationale}</Paragraph>
                    
                    {record.user_feedback && (
                      <>
                        <Title level={5}>Your Feedback</Title>
                        <Paragraph>{record.user_feedback}</Paragraph>
                      </>
                    )}
                  </div>
                ),
              }}
            />
          </TabPane>
        </Tabs>
      </Card>
      
      <FeedbackModal
        visible={feedbackModal.visible}
        recommendation={feedbackModal.recommendation}
        action={feedbackModal.action}
        onSubmit={handleFeedbackSubmit}
        onCancel={() => setFeedbackModal({ ...feedbackModal, visible: false })}
      />
    </div>
  );
};

export default AgentPricingRecommendations;
