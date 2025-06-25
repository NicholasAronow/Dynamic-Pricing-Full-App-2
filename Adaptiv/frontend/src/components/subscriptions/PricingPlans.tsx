import React, { useState, useEffect } from 'react';
import { Card, Button, Row, Col, Typography, Tag, Spin, message } from 'antd';
import { CheckOutlined, LoadingOutlined } from '@ant-design/icons';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import api from 'services/api';

const { Title, Text, Paragraph } = Typography;

interface Plan {
  name: string;
  priceId: string;
  price: string;
  interval: string;
  features: string[];
  recommended?: boolean;
  loading?: boolean;
  disabled?: boolean;
}

const PREMIUM_PRODUCT_ID = 'prod_SZ9VLgjajkW0rM'; // Your Stripe Product ID

const PricingPlans: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState<string | null>(null);
  const [plans, setPlans] = useState<Plan[]>([
    {
      name: 'Free',
      priceId: 'free',
      price: '$0',
      interval: 'forever',
      features: [
        'Basic menu analysis',
        'Simple pricing recommendations',
        'Up to 25 menu items',
        'Weekly reports'
      ],
    },
    {
      name: 'Premium',
      priceId: '',
      price: '$99', // This will be updated from Stripe
      interval: 'per month', // This will be updated from Stripe
      features: [
        'Everything in Free',
        'Advanced analytics',
        'AI-powered recommendations',
        'Unlimited menu items',
        'Real-time analytics',
        'Priority email & phone support',
        'API access for custom integrations'
      ],
      recommended: true,
      loading: true // Set loading state for premium plan
    }
  ]);
  
  // Fetch price information from Stripe
  useEffect(() => {
    const fetchPriceInfo = async () => {
      try {
        const response = await api.get(`/subscriptions/product-prices?productId=${PREMIUM_PRODUCT_ID}`);
        if (response.data && response.data.prices && response.data.prices.length > 0) {
          // Find the active price
          const activePrice = response.data.prices.find((price: any) => price.active);
          
          if (activePrice) {
            setPlans(prevPlans => {
              const updatedPlans = [...prevPlans];
              const premiumPlan = updatedPlans.find(plan => plan.name === 'Premium');
              
              if (premiumPlan) {
                // Format the price display
                const amount = activePrice.unit_amount / 100; // Convert from cents to dollars
                const currency = activePrice.currency.toUpperCase();
                const interval = activePrice.recurring?.interval || 'month';
                
                premiumPlan.priceId = activePrice.id;
                premiumPlan.price = `$${amount}`;
                premiumPlan.interval = `per ${interval}`;
                premiumPlan.loading = false;
              }
              
              return updatedPlans;
            });
          }
        }
      } catch (error) {
        console.error('Error fetching price information:', error);
        message.error('Failed to load subscription prices');
        
        // Set a fallback price ID if there's an error
        setPlans(prevPlans => {
          const updatedPlans = [...prevPlans];
          const premiumPlan = updatedPlans.find(plan => plan.name === 'Premium');
          
          if (premiumPlan) {
            premiumPlan.loading = false;
          }
          
          return updatedPlans;
        });
      }
    };
    
    fetchPriceInfo();
  }, []);

  const handleSubscribe = async (priceId: string) => {
    if (priceId === 'free') {
      message.info('You are already on the Free plan');
      return;
    }
    
    setLoading(priceId);
    try {
      // Log the payload for debugging
      const payload = {
        price_id: priceId,
        success_url: `${window.location.origin}/subscription-success`,
        cancel_url: `${window.location.origin}/subscription-cancel`,
      };
      console.log('Sending checkout request with payload:', payload);
      
      const response = await api.post('/subscriptions/create-checkout-session', payload);
      
      // Redirect to Stripe Checkout
      window.location.href = response.data.url;
    } catch (error: any) {
      console.error('Error creating checkout session:', error);
      if (error.response) {
        // The request was made and the server responded with a status code
        // that falls out of the range of 2xx
        console.error('Error data:', error.response.data);
        console.error('Error status:', error.response.status);
        console.error('Error headers:', error.response.headers);
        message.error(`Subscription error: ${error.response.data.detail || 'Server error'}`);
      } else if (error.request) {
        // The request was made but no response was received
        console.error('Error request:', error.request);
        message.error('No response received from server. Check your connection.');
      } else {
        // Something happened in setting up the request
        console.error('Error message:', error.message);
        message.error('Error setting up subscription request.');
      }
      setLoading(null);
    }
  };

  return (
    <div style={{ padding: '40px 0' }}>
      <Title level={2} style={{ textAlign: 'center', marginBottom: 48 }}>
        Choose the Right Plan for Your Business
      </Title>
      <Paragraph style={{ textAlign: 'center', marginBottom: 48, fontSize: 16 }}>
        Get access to advanced pricing optimization features with our premium plans
      </Paragraph>
      
      <Row gutter={[24, 24]} justify="center">
        {plans.map((plan) => (
          <Col xs={24} sm={24} md={8} key={plan.name}>
            <Card
              hoverable
              style={{
                height: '100%',
                display: 'flex',
                flexDirection: 'column',
                ...(plan.recommended ? { 
                  borderColor: '#1890ff',
                  boxShadow: '0 0 10px rgba(24, 144, 255, 0.2)',
                } : {}),
              }}
              bodyStyle={{ flex: 1, display: 'flex', flexDirection: 'column' }}
            >
              {plan.recommended && (
                <div style={{ 
                  position: 'absolute', 
                  top: 0, 
                  right: 0, 
                  backgroundColor: '#1890ff', 
                  color: 'white',
                  padding: '4px 12px',
                  borderBottomLeftRadius: 8,
                }}>
                  Recommended
                </div>
              )}
              
              <Title level={3} style={{ marginBottom: 8 }}>{plan.name}</Title>
              <div style={{ display: 'flex', alignItems: 'flex-end', marginBottom: 24 }}>
                <Title level={2} style={{ margin: 0 }}>{plan.price}</Title>
                <Text type="secondary" style={{ marginLeft: 8, marginBottom: 6 }}>
                  {plan.interval}
                </Text>
              </div>
              
              <div style={{ flex: 1 }}>
                {plan.features.map((feature, index) => (
                  <div key={index} style={{ marginBottom: 12, display: 'flex' }}>
                    <CheckOutlined style={{ color: '#52c41a', marginRight: 8, marginTop: 4 }} />
                    <Text>{feature}</Text>
                  </div>
                ))}
              </div>
              
              <Button
                type={plan.recommended ? 'primary' : 'default'}
                size="large"
                block
                onClick={() => handleSubscribe(plan.priceId)}
                disabled={plan.disabled || loading !== null}
                style={{ marginTop: 24 }}
              >
                {loading === plan.priceId ? <LoadingOutlined /> : 'Subscribe'}
              </Button>
            </Card>
          </Col>
        ))}
      </Row>
    </div>
  );
};

export default PricingPlans;
