import React, { useEffect, useState } from 'react';
import { Card, Button, Typography, Tag, Spin, Divider, message, Result } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import api from 'services/api';

const { Title, Text, Paragraph } = Typography;

interface SubscriptionStatus {
  active: boolean;
  subscription_id?: string;
  current_period_end?: string;
  plan?: string;
}

const SubscriptionManagement: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [portalLoading, setPortalLoading] = useState(false);
  const [subscription, setSubscription] = useState<SubscriptionStatus | null>(null);

  const fetchSubscription = async () => {
    setLoading(true);
    try {
      const response = await api.get('/subscriptions/subscription-status');
      setSubscription(response.data);
    } catch (error) {
      console.error('Error fetching subscription status:', error);
      message.error('Failed to load subscription details');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSubscription();
  }, []);

  const handleCustomerPortal = async () => {
    setPortalLoading(true);
    try {
      const response = await api.post('/subscriptions/customer-portal', {
        return_url: `${window.location.origin}/subscription-management`
      });
      
      // Redirect to Stripe Customer Portal
      window.location.href = response.data.url;
    } catch (error) {
      console.error('Error creating customer portal session:', error);
      message.error('Failed to access customer portal. Please try again later.');
      setPortalLoading(false);
    }
  };

  const handleSubscribe = () => {
    navigate('/subscription-plans');
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '40px' }}>
        <Spin size="large" />
        <Paragraph style={{ marginTop: 24 }}>Loading subscription details...</Paragraph>
      </div>
    );
  }

  if (!subscription?.active) {
    return (
      <Result
        status="info"
        title="No Active Subscription"
        subTitle="You don't have an active subscription yet. Subscribe to access premium features."
        extra={
          <Button type="primary" onClick={handleSubscribe}>
            View Subscription Plans
          </Button>
        }
      />
    );
  }

  const formattedDate = subscription.current_period_end 
    ? new Date(Number(subscription.current_period_end) * 1000).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
      })
    : 'N/A';

  return (
    <div style={{ maxWidth: '800px', margin: '0 auto', padding: '24px' }}>
      <Card bordered>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <Title level={3} style={{ margin: 0 }}>Subscription Details</Title>
          <Button 
            icon={<ReloadOutlined />}
            onClick={fetchSubscription}
          >
            Refresh
          </Button>
        </div>
        
        <Divider />
        
        <div style={{ marginBottom: 16 }}>
          <Text strong>Current Plan:</Text>
          <Tag 
            color="blue" 
            style={{ marginLeft: 8, fontSize: '14px', padding: '4px 8px' }}
          >
            {subscription.plan || 'Unknown'}
          </Tag>
        </div>
        
        <div style={{ marginBottom: 16 }}>
          <Text strong>Status:</Text>
          <Tag 
            color="green" 
            style={{ marginLeft: 8, fontSize: '14px', padding: '4px 8px' }}
          >
            Active
          </Tag>
        </div>
        
        <div style={{ marginBottom: 24 }}>
          <Text strong>Renews On:</Text>
          <Text style={{ marginLeft: 8 }}>{formattedDate}</Text>
        </div>
        
        <Divider />
        
        <div style={{ marginTop: 24 }}>
          <Button 
            type="primary" 
            onClick={handleCustomerPortal}
            loading={portalLoading}
            block
          >
            Manage Subscription
          </Button>
          <Text type="secondary" style={{ display: 'block', marginTop: 8, textAlign: 'center' }}>
            You'll be redirected to the Stripe Customer Portal
          </Text>
        </div>
      </Card>
    </div>
  );
};

export default SubscriptionManagement;
