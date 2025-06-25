import React, { useEffect, useState } from 'react';
import { Result, Button, Spin, Typography } from 'antd';
import { CheckCircleOutlined } from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import axios from 'axios';
import api from 'services/api';

const { Title, Paragraph } = Typography;

const SubscriptionSuccess: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [loading, setLoading] = useState(true);
  const [subscription, setSubscription] = useState<any>(null);
  
  useEffect(() => {
    const fetchSubscriptionStatus = async () => {
      try {
        const response = await api.get('/subscriptions/subscription-status');
        setSubscription(response.data);
      } catch (error) {
        console.error('Error fetching subscription status:', error);
      } finally {
        setLoading(false);
      }
    };
    
    fetchSubscriptionStatus();
  }, []);
  
  return (
    <div style={{ padding: '40px', maxWidth: '800px', margin: '0 auto' }}>
      {loading ? (
        <div style={{ textAlign: 'center', padding: '40px' }}>
          <Spin size="large" />
          <Paragraph style={{ marginTop: 24 }}>Verifying your subscription...</Paragraph>
        </div>
      ) : (
        <Result
          icon={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
          title="Subscription Activated Successfully!"
          subTitle={
            subscription?.active
              ? `You are now subscribed to the ${subscription.plan} plan. Your subscription is active until ${new Date(
                  Number(subscription.current_period_end) * 1000
                ).toLocaleDateString()}.`
              : "Your subscription is being processed. It may take a few moments to be fully activated."
          }
          extra={[
            <Button 
              type="primary" 
              key="dashboard" 
              onClick={() => navigate('/dashboard')}
            >
              Go to Dashboard
            </Button>,
            <Button 
              key="manage" 
              onClick={() => navigate('/subscription-management')}
            >
              Manage Subscription
            </Button>,
          ]}
        />
      )}
    </div>
  );
};

export default SubscriptionSuccess;
