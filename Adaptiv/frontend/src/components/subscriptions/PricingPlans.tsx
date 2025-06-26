import React, { useState, useEffect } from 'react';
import { 
  Card, 
  Button, 
  Row, 
  Col, 
  Typography, 
  Tag, 
  Spin, 
  message, 
  Avatar,
  Divider,
  Badge
} from 'antd';
import { 
  CheckOutlined, 
  LoadingOutlined, 
  StarOutlined,
  RocketOutlined,
  CrownOutlined,
  ThunderboltOutlined,
  GiftOutlined,
} from '@ant-design/icons';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import api from 'services/api';
import { useSubscription, SUBSCRIPTION_TIERS } from '../../contexts/SubscriptionContext';

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
  originalPrice?: string;
  savings?: string;
  description: string;
  icon: React.ReactNode;
  color: string;
  gradient: string;
}

const PREMIUM_PRODUCT_ID = 'prod_SZAVh4qmsRJS6k';

const PricingPlans: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState<string | null>(null);
  const { currentPlan, isSubscribed, subscriptionStatus, loading: subscriptionLoading } = useSubscription();
  const [plans, setPlans] = useState<Plan[]>([
    {
      name: 'Free',
      priceId: 'free',
      price: '$0',
      interval: 'forever',
      description: 'Perfect for getting started with basic features',
      icon: <GiftOutlined />,
      color: '#rgb(180,180,180)',
      gradient: 'linear-gradient(135deg,rgb(208, 208, 208) 0%,rgb(180, 180, 180) 100%)',
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
      price: '$49',
      interval: 'per month',
      description: 'Advanced analytics and unlimited features',
      icon: <RocketOutlined />,
      color: '#9370DB',
      gradient: 'linear-gradient(135deg, #B19CD9 0%, #9370DB 50%, #7D53C8 100%)',
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
      loading: true
    }
  ]);

  interface SubscriptionStatus {
      active: boolean;
      subscription_id?: string;
      current_period_end?: string;
      plan?: string;
    }
  
  const [portalLoading, setPortalLoading] = useState(false);
  const [subscription, setSubscription] = useState<SubscriptionStatus | null>(null);
  const { Title, Text, Paragraph } = Typography;
  
  /**
   * A component that wraps content which requires a subscription.
   * Shows the content normally if user has required subscription tier,
   * otherwise displays a blurred version with an upgrade CTA.
   */
  
  const fetchSubscription = async () => {
      setLoading("true");
      try {
        const response = await api.get('/subscriptions/subscription-status');
        setSubscription(response.data);
      } catch (error) {
        console.error('Error fetching subscription status:', error);
        message.error('Failed to load subscription details');
      } finally {
        setLoading("false");
      }
    };
  
  useEffect(() => {
    fetchSubscription();
  }, []);
  
  useEffect(() => {
    const fetchPriceInfo = async () => {
      try {
        const response = await api.get(`/subscriptions/product-prices?productId=${PREMIUM_PRODUCT_ID}`);
        if (response.data && response.data.prices && response.data.prices.length > 0) {
          const activePrice = response.data.prices.find((price: any) => price.active);
          
          if (activePrice) {
            setPlans(prevPlans => {
              const updatedPlans = [...prevPlans];
              const premiumPlan = updatedPlans.find(plan => plan.name === 'Premium');
              
              if (premiumPlan) {
                const amount = activePrice.unit_amount / 100;
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

  const handleSubscribe = async (priceId: string, planName: string) => {
    // Don't do anything if this is the current plan
    const isPlanCurrent = 
      (planName.toLowerCase() === 'free' && currentPlan === SUBSCRIPTION_TIERS.FREE) || 
      (planName.toLowerCase() === 'premium' && currentPlan === SUBSCRIPTION_TIERS.PREMIUM);
      
    if (isPlanCurrent) {
      return;
    }
    
    // Handle switching to free plan (downgrade)
    if (priceId === 'free') {
      message.info('Please use the Subscription Management page to change your plan');
      navigate('/subscription-management');
      return;
    }
    
    setLoading(priceId);
    try {
      const payload = {
        price_id: priceId,
        success_url: `${window.location.origin}/subscription-success`,
        cancel_url: `${window.location.origin}/subscription-plans`,
      };
      console.log('Sending checkout request with payload:', payload);
      
      const response = await api.post('/subscriptions/create-checkout-session', payload);
      window.location.href = response.data.url;
    } catch (error: any) {
      console.error('Error creating checkout session:', error);
      if (error.response) {
        console.error('Error data:', error.response.data);
        console.error('Error status:', error.response.status);
        console.error('Error headers:', error.response.headers);
        message.error(`Failed to create subscription: ${error.response?.data?.detail || 'Unknown error'}`);
      } else if (error.request) {
        console.error('Error request:', error.request);
        message.error('No response received from server. Check your connection.');
      } else {
        console.error('Error message:', error.message);
        message.error('Error setting up subscription request.');
      }
    } finally {
      setLoading(null);
    }
  };

  const getButtonText = (plan: Plan) => {
    // If this is loading state for this specific plan
    if (loading === plan.priceId) return <LoadingOutlined />;
    
    // If this is the current plan
    if (isPlanActive(plan)) return 'Current Plan';
    
    // Otherwise standard text
    if (plan.name.toLowerCase() === 'free') return 'Get Started Free';
    return 'Subscribe';
  };

  const isPlanActive = (plan: Plan): boolean => {
    return (plan.name.toLowerCase() === 'free' && currentPlan === SUBSCRIPTION_TIERS.FREE) || 
           (plan.name.toLowerCase() === 'premium' && currentPlan === SUBSCRIPTION_TIERS.PREMIUM);
  };

  const getButtonStyle = (plan: Plan) => {
    // If this is the current plan
    if (subscription?.active) {
      return {
        border: '2px solid rgb(170, 170, 170)',  // Gray border
        color: '#666666',             // Gray text
        height: '48px',
        fontSize: '16px',
        fontWeight: 600,
        borderRadius: '8px',
        background: 'rgba(197, 197, 197, 0.1)', // Light gray background
        cursor: 'default',
      };
    }
    
    // For recommended plan
    if (plan.recommended) {
      return {
        background: plan.gradient,
        border: 'none',
        color: 'white',
        height: '48px',
        fontSize: '16px',
        fontWeight: 600,
        borderRadius: '8px',
        boxShadow: '0 4px 14px 0 rgba(147, 112, 219, 0.4)',
      };
    }
    
    // For other plans
    return {
      border: `2px solid ${plan.color}`,
      color: plan.color,
      height: '48px',
      fontSize: '16px',
      fontWeight: 600,
      borderRadius: '8px',
      background: 'white',
    };
  };

  return (
    <div style={{ 
      minHeight: '100vh',
      background: '#fefefe',
      padding: '60px 24px'
    }}>
      <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
        {/* Header Section */}
        <div style={{ textAlign: 'center', marginBottom: 60, color: 'white' }}>
          <Title level={1} style={{ color: '#9370DB', marginBottom: 16, fontSize: '48px' }}>
            Choose Your Perfect Plan
          </Title>
          <Paragraph style={{ 
            color: '#9370DB', 
            fontSize: '20px', 
            maxWidth: '600px', 
            margin: '0 auto 32px',
            lineHeight: '1.6'
          }}>
            Transform your restaurant's pricing strategy with our AI-powered optimization platform
          </Paragraph>
          
          {/* Trust indicators */}
          <div style={{ display: 'flex', justifyContent: 'center', gap: '32px', flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', alignItems: 'center', color: '#9370DB' }}>
              <CheckOutlined style={{ marginRight: 8, fontSize: '16px' }} />
              <Text style={{ color: '#9370DB' }}>30-day money back guarantee</Text>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', color: '#9370DB' }}>
              <ThunderboltOutlined style={{ marginRight: 8, fontSize: '16px' }} />
              <Text style={{ color: '#9370DB' }}>Setup in under 5 minutes</Text>
            </div>
          </div>
        </div>
        
        <Row gutter={[32, 32]} justify="center">
          {plans.map((plan, index) => (
            <Col xs={24} md={12} lg={10} key={plan.name}>
              <Badge.Ribbon 
                text={plan.recommended ? "Most Popular" : ""} 
                color={plan.recommended ? "#9370DB" : "#10b981"}
                style={{ 
                  display: plan.recommended ? 'block' : 'none',
                  fontSize: '14px',
                  fontWeight: 600,
                  padding: '6px 12px',
                  right: '-20px',
                  top: '10px'
                }}
              >
                <Card
                  style={{
                    height: '100%',
                    borderRadius: '16px',
                    border: 'none',
                    boxShadow: plan.recommended 
                      ? '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04), 0 0 0 1px rgba(59, 130, 246, 0.1)'
                      : '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
                    transform: plan.recommended ? 'scale(1.05)' : 'scale(1)',
                    transition: 'all 0.3s ease',
                    background: 'white',
                    position: 'relative',
                    overflow: 'hidden'
                  }}
                  bodyStyle={{ 
                    padding: '32px 24px',
                    height: '100%',
                    display: 'flex',
                    flexDirection: 'column'
                  }}
                  hoverable
                >
                  {/* Plan Header */}
                  <div style={{ textAlign: 'center', marginBottom: 32 }}>
                    <Avatar 
                      size={64}
                      style={{ 
                        background: plan.gradient,
                        marginBottom: 16,
                        border: '3px solid rgba(255,255,255,0.2)'
                      }}
                      icon={plan.icon}
                    />
                    <Title level={3} style={{ margin: 0, color: '#1f2937' }}>
                      {plan.name}
                    </Title>
                    <Text type="secondary" style={{ fontSize: '14px', display: 'block', marginTop: 4 }}>
                      {plan.description}
                    </Text>
                  </div>

                  {/* Pricing */}
                  <div style={{ textAlign: 'center', marginBottom: 32 }}>
                    <Title 
                      level={1} 
                      style={{ 
                        margin: 0, 
                        color: plan.color,
                        fontSize: '48px',
                        fontWeight: 800
                      }}
                    >
                      {plan.loading ? <Spin /> : plan.price}
                    </Title>
                    <Text type="secondary" style={{ fontSize: '16px' }}>
                      {plan.interval}
                    </Text>
                  </div>

                  <Divider style={{ margin: '0 0 24px 0' }} />

                  {/* Features */}
                  <div style={{ flex: 1 }}>
                    {plan.features.map((feature, featureIndex) => (
                      <div 
                        key={featureIndex} 
                        style={{ 
                          display: 'flex', 
                          alignItems: 'flex-start',
                          marginBottom: 16,
                          padding: '8px 0'
                        }}
                      >
                        <CheckOutlined 
                          style={{ 
                            color: plan.color, 
                            marginRight: 12, 
                            marginTop: 2,
                            fontSize: '16px',
                            fontWeight: 600
                          }} 
                        />
                        <Text style={{ fontSize: '15px', color: '#374151', lineHeight: '1.5' }}>
                          {feature}
                        </Text>
                      </div>
                    ))}
                  </div>

                  {/* CTA Button */}
                  <Button
                    type={plan.recommended ? 'primary' : 'default'}
                    size="large"
                    block
                    onClick={() => handleSubscribe(plan.priceId, plan.name)}
                    disabled={plan.disabled || 
                             (loading !== null && loading !== plan.priceId) ||
                             isPlanActive(plan)}
                    style={getButtonStyle(plan)}
                    icon={isPlanActive(plan) ? <CheckOutlined /> : null}
                  >
                    {getButtonText(plan)}
                  </Button>

                  {plan.name === 'Premium' && (
                    <Text 
                      style={{ 
                        textAlign: 'center', 
                        fontSize: '12px', 
                        color: '#6b7280',
                        marginTop: 12,
                        display: 'block'
                      }}
                    >
                      Cancel anytime
                    </Text>
                  )}
                </Card>
              </Badge.Ribbon>
            </Col>
          ))}
        </Row>

        {/* Bottom Section */}
        <div style={{ 
          textAlign: 'center', 
          marginTop: 80, 
          padding: '32px',
          background: 'rgba(255,255,255,0.1)',
          borderRadius: '16px',
          backdropFilter: 'blur(10px)',
          border: '1px solid rgba(255,255,255,0.2)'
        }}>
          <Title level={3} style={{ color: 'white', marginBottom: 16 }}>
            Trusted by 10,000+ restaurants worldwide
          </Title>
          <Text style={{ color: 'rgba(255,255,255,0.8)', fontSize: '16px' }}>
            Join successful restaurant owners who've increased their profits by an average of 23% using our platform
          </Text>
        </div>

        {/* FAQ Teaser */}
        <div style={{ textAlign: 'center', marginTop: 40 }}>
          <Text style={{ color: 'rgba(255,255,255,0.7)', fontSize: '14px' }}>
            Questions? Check out our{' '}
            <a href="/faq" style={{ color: 'white', textDecoration: 'underline' }}>
              FAQ
            </a>
            {' '}or{' '}
            <a href="/contact" style={{ color: 'white', textDecoration: 'underline' }}>
              contact our team
            </a>
          </Text>
        </div>
      </div>
    </div>
  );
};

export default PricingPlans;