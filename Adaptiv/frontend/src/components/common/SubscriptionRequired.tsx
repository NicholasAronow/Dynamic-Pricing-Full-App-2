import React, { ReactNode, useEffect } from 'react';
import { Card, Typography, Button, Space } from 'antd';
import { LockOutlined, CrownOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useSubscription, SUBSCRIPTION_TIERS } from '../../contexts/SubscriptionContext';
import { useState } from 'react';
import { api } from '../../services/api';
import { message } from 'antd';

interface SubscriptionStatus {
    active: boolean;
    subscription_id?: string;
    current_period_end?: string;
    plan?: string;
  }



interface SubscriptionRequiredProps {
  children: ReactNode;
}


  
const SubscriptionRequired: React.FC<SubscriptionRequiredProps> = ({
  children,
}) => {
  const navigate = useNavigate();
  const { isSubscribed, currentPlan } = useSubscription();
  const [loading, setLoading] = useState(true);
  const [portalLoading, setPortalLoading] = useState(false);
  const [subscription, setSubscription] = useState<SubscriptionStatus | null>(null);
  const { Title, Text, Paragraph } = Typography;
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
  
  const hasAccess = subscription?.active
  
  if (hasAccess) {
    return <>{children}</>;
  }
  
  return (
    <div style={{ position: 'relative' }}>
      {/* The blurred content */}
      <div style={{ 
        filter: 'blur(6px)', 
        pointerEvents: 'none',
        opacity: 0.7,
        userSelect: 'none'
      }}>
        {children}
      </div>
      
      {/* Overlay with subscription message */}
      <div style={{
        position: 'absolute',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '20px',
        zIndex: 10
      }}>
        <Card 
          style={{ 
            maxWidth: 500,
            textAlign: 'center',
            boxShadow: '0 4px 24px rgba(0,0,0,0.12)',
            background: 'rgba(255,255,255,0.95)',
            borderRadius: '12px'
          }}
        >
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            <div style={{ marginBottom: 16 }}>
              <CrownOutlined style={{ fontSize: 48, color: '#9370DB', marginBottom: 16 }} />
              <Title level={3} style={{ margin: 0 }}>
                Premium Feature
              </Title>
              <LockOutlined style={{ marginLeft: 8, color: '#9370DB' }} />
            </div>
            
            <Paragraph style={{ fontSize: 16 }}>
              This feature is available exclusively to premium subscribers.
              Upgrade today to access advanced AI-powered pricing recommendations
              and maximize your revenue.
            </Paragraph>
            
            <Button 
              type="primary"
              size="large"
              onClick={() => navigate('/subscription-plans')}
              style={{
                background: 'linear-gradient(135deg, #B19CD9 0%, #9370DB 50%, #7D53C8 100%)',
                border: 'none',
                height: '48px',
                fontSize: '16px',
                fontWeight: 600,
                borderRadius: '8px',
                boxShadow: '0 4px 14px 0 rgba(147, 112, 219, 0.4)',
              }}
            >
              Upgrade to Premium
            </Button>
            
            <Text type="secondary">
              Already subscribed? Try refreshing the page or contact support.
            </Text>
          </Space>
        </Card>
      </div>
    </div>
  );
};

export default SubscriptionRequired;
