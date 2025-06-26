import React, { useState, useEffect } from 'react';
import { 
  Form, 
  Input, 
  Button, 
  Select, 
  Typography, 
  Card, 
  notification,
  Spin,
  Alert,
  Row,
  Col,
  message,
  Result,
  Avatar
} from 'antd';
import { BankOutlined, CalendarOutlined, CheckCircleOutlined, CreditCardOutlined, CrownOutlined, EnvironmentOutlined, QuestionCircleOutlined } from '@ant-design/icons';
import { api } from '../../services/api';
import { Tag, Divider } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;
const { TextArea } = Input;

interface BusinessProfileData {
  business_name: string;
  industry: string;
  company_size: string;
  founded_year?: number;
  description?: string;
  // Address fields
  street_address?: string;
  city?: string;
  state?: string;
  postal_code?: string;
  country?: string;
}

const BusinessProfile: React.FC = () => {
  const [form] = Form.useForm();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // State to store profile data
  const [, setProfile] = useState<BusinessProfileData | null>(null);
  const [mode, setMode] = useState<'create' | 'edit'>('create');

  const currentYear = new Date().getFullYear();
  const yearsArray = Array.from({ length: 100 }, (_, i) => currentYear - i);

  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [portalLoading, setPortalLoading] = useState(false);
  const [subscription, setSubscription] = useState<SubscriptionStatus | null>(null);

  interface SubscriptionStatus {
    active: boolean;
    subscription_id?: string;
    current_period_end?: string;
    plan?: string;
  }

  useEffect(() => {
    fetchProfile();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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

  const fetchProfile = async () => {
    try {
      setLoading(true);
      const response = await api.get('profile/business');
      setProfile(response.data);
      form.setFieldsValue(response.data);
      setMode('edit');
    } catch (err: any) {
      if (err.response?.status !== 404) {
        setError('Failed to load profile. Please try again.');
      }
      // 404 means no profile yet, which is fine for new users
    } finally {
      setLoading(false);
    }
  };

  const onFinish = async (values: BusinessProfileData) => {
    try {
      setSubmitting(true);
      setError(null);
      
      if (mode === 'create') {
        await api.post('profile/business', values);
        notification.success({
          message: 'Success',
          description: 'Business profile created successfully!',
        });
      } else {
        await api.put('profile/business', values);
        notification.success({
          message: 'Success',
          description: 'Business profile updated successfully!',
        });
      }
      
      setProfile(values);
      setMode('edit');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save profile. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 'calc(100vh - 200px)' }}>
        <Spin size="large" />
      </div>
    );
  }

  

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

  // Format the date outside the render to use in both cases
  const formattedDate = subscription?.active && subscription.current_period_end 
    ? new Date(Number(subscription.current_period_end) * 1000).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
      })
    : 'N/A';

  

    return (
      <div style={{ maxWidth: '80%', margin: '0 auto', padding: '24px' }}>
        {/* Header Section */}
        <div style={{ 
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          borderRadius: '16px',
          padding: '40px 32px',
          marginBottom: 32,
          color: 'white',
          textAlign: 'center'
        }}>
          <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 16 }}>
            <Avatar 
              size={64}
              style={{ 
                backgroundColor: 'rgba(255,255,255,0.2)', 
                border: '3px solid rgba(255,255,255,0.3)'
              }}
              icon={<BankOutlined style={{ fontSize: '28px', color: 'white' }} />}
            />
          </div>
          <Title level={2} style={{ color: 'white', margin: 0, marginBottom: 8 }}>
            Business Profile
          </Title>
          <Text style={{ color: 'rgba(255,255,255,0.9)', fontSize: '16px' }}>
            {mode === 'create' ? 'Create your business profile to get started' : 'Update your business profile information'}
          </Text>
        </div>
  
        <Row gutter={[32, 32]}>
          {/* Main Profile Form */}
          <Col xs={24} lg={16}>
            <Card 
              style={{ 
                borderRadius: '12px',
                boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
                border: '1px solid #e5e7eb'
              }}
              bodyStyle={{ padding: '32px' }}
            >
              {error && (
                <Alert
                  message="Error"
                  description={error}
                  type="error"
                  showIcon
                  style={{ 
                    marginBottom: 24,
                    borderRadius: '8px',
                    border: '1px solid #fca5a5'
                  }}
                  closable
                  onClose={() => setError(null)}
                />
              )}
              
              <Form
                form={form}
                layout="vertical"
                onFinish={onFinish}
                initialValues={{
                  business_name: '',
                  industry: '',
                  company_size: '',
                  founded_year: undefined,
                  description: '',
                  street_address: '',
                  city: '',
                  state: '',
                  postal_code: '',
                  country: 'USA',
                }}
              >
                {/* Business Information Section */}
                <div style={{ marginBottom: 32 }}>
                  <Title level={4} style={{ color: '#1f2937', marginBottom: 16, display: 'flex', alignItems: 'center' }}>
                    <BankOutlined style={{ marginRight: 8, color: '#6366f1' }} />
                    Business Information
                  </Title>
                  
                  <Form.Item
                    name="business_name"
                    label={<Text strong style={{ color: '#374151' }}>Business Name</Text>}
                    rules={[{ required: true, message: 'Please enter your business name' }]}
                  >
                    <Input 
                      prefix={<BankOutlined style={{ color: '#9ca3af' }} />} 
                      placeholder="Enter your business name"
                      size="large"
                      style={{ borderRadius: '8px', border: '2px solid #e5e7eb' }}
                    />
                  </Form.Item>
                  
                  <Row gutter={16}>
                    <Col xs={24} md={12}>
                      <Form.Item
                        name="industry"
                        label={<Text strong style={{ color: '#374151' }}>Industry</Text>}
                        rules={[{ required: true, message: 'Please select your industry' }]}
                      >
                        <Select 
                          placeholder="Select your industry"
                          size="large"
                          style={{ borderRadius: '8px' }}
                        >
                          <Option value="Cafe">Cafe</Option>
                          <Option value="Coffee Shop">Coffee Shop</Option>
                          <Option value="Bakery">Bakery</Option>
                          <Option value="Restaurant">Restaurant</Option>
                          <Option value="Fast Food">Fast Food</Option>
                          <Option value="Food Truck">Food Truck</Option>
                          <Option value="Pizzeria">Pizzeria</Option>
                          <Option value="Bar">Bar</Option>
                          <Option value="Brewery">Brewery</Option>
                          <Option value="Ice Cream Shop">Ice Cream Shop</Option>
                          <Option value="Juice Bar">Juice Bar</Option>
                          <Option value="Deli">Deli</Option>
                          <Option value="Catering">Catering</Option>
                          <Option value="Other Food Service">Other Food Service</Option>
                        </Select>
                      </Form.Item>
                    </Col>
                    
                    <Col xs={24} md={12}>
                      <Form.Item
                        name="company_size"
                        label={<Text strong style={{ color: '#374151' }}>Company Size</Text>}
                        rules={[{ required: true, message: 'Please select company size' }]}
                      >
                        <Select 
                          placeholder="Select company size"
                          size="large"
                          style={{ borderRadius: '8px' }}
                        >
                          <Option value="1-10">1-10 employees</Option>
                          <Option value="11-50">11-50 employees</Option>
                          <Option value="51-200">51-200 employees</Option>
                          <Option value="201-500">201-500 employees</Option>
                          <Option value="501-1000">501-1000 employees</Option>
                          <Option value="1001+">1001+ employees</Option>
                        </Select>
                      </Form.Item>
                    </Col>
                  </Row>
                  
                  <Form.Item
                    name="founded_year"
                    label={<Text strong style={{ color: '#374151' }}>Year Founded</Text>}
                  >
                    <Select 
                      placeholder="Select year founded"
                      size="large"
                      style={{ borderRadius: '8px' }}
                    >
                      {yearsArray.map(year => (
                        <Option key={year} value={year}>{year}</Option>
                      ))}
                    </Select>
                  </Form.Item>
                  
                  <Form.Item
                    name="description"
                    label={<Text strong style={{ color: '#374151' }}>Company Description</Text>}
                  >
                    <TextArea 
                      rows={4} 
                      placeholder="Brief description of your company"
                      style={{ borderRadius: '8px', border: '2px solid #e5e7eb' }}
                    />
                  </Form.Item>
                </div>
  
                {/* Location Section */}
                <div style={{ 
                  padding: '24px',
                  background: '#f8fafc',
                  borderRadius: '12px',
                  border: '1px solid #e2e8f0',
                  marginBottom: 32
                }}>
                  <Title level={4} style={{ color: '#1f2937', marginBottom: 8, display: 'flex', alignItems: 'center' }}>
                    <EnvironmentOutlined style={{ marginRight: 8, color: '#6366f1' }} />
                    Location Information
                  </Title>
                  <Text style={{ color: '#6b7280', marginBottom: 20, display: 'block' }}>
                    This information helps our agents find local competitors in your area.
                  </Text>
                  
                  <Form.Item
                    name="street_address"
                    label={<Text strong style={{ color: '#374151' }}>Street Address</Text>}
                  >
                    <Input 
                      placeholder="123 Main St"
                      size="large"
                      style={{ borderRadius: '8px', border: '2px solid #e5e7eb' }}
                    />
                  </Form.Item>
                  
                  <Row gutter={16}>
                    <Col xs={24} sm={8}>
                      <Form.Item
                        name="city"
                        label={<Text strong style={{ color: '#374151' }}>City</Text>}
                      >
                        <Input 
                          placeholder="New York"
                          size="large"
                          style={{ borderRadius: '8px', border: '2px solid #e5e7eb' }}
                        />
                      </Form.Item>
                    </Col>
                    <Col xs={12} sm={8}>
                      <Form.Item
                        name="state"
                        label={<Text strong style={{ color: '#374151' }}>State</Text>}
                      >
                        <Input 
                          placeholder="NY"
                          size="large"
                          style={{ borderRadius: '8px', border: '2px solid #e5e7eb' }}
                        />
                      </Form.Item>
                    </Col>
                    <Col xs={12} sm={8}>
                      <Form.Item
                        name="postal_code"
                        label={<Text strong style={{ color: '#374151' }}>Postal Code</Text>}
                      >
                        <Input 
                          placeholder="10001"
                          size="large"
                          style={{ borderRadius: '8px', border: '2px solid #e5e7eb' }}
                        />
                      </Form.Item>
                    </Col>
                  </Row>
                  
                  <Form.Item
                    name="country"
                    label={<Text strong style={{ color: '#374151' }}>Country</Text>}
                    initialValue="USA"
                  >
                    <Select
                      size="large"
                      style={{ borderRadius: '8px' }}
                    >
                      <Option value="USA">United States</Option>
                      <Option value="Canada">Canada</Option>
                      <Option value="Mexico">Mexico</Option>
                      <Option value="Other">Other</Option>
                    </Select>
                  </Form.Item>
                </div>
                
                <Form.Item>
                  <Button 
                    type="primary" 
                    htmlType="submit"
                    loading={submitting}
                    size="large"
                    style={{
                      minWidth: 160,
                      height: '48px',
                      borderRadius: '8px',
                      fontSize: '16px',
                      fontWeight: 600,
                      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                      border: 'none',
                      boxShadow: '0 4px 14px 0 rgba(102, 126, 234, 0.4)'
                    }}
                  >
                    {mode === 'create' ? 'Create Profile' : 'Update Profile'}
                  </Button>
                </Form.Item>
              </Form>
            </Card>
          </Col>
  
          {/* Subscription Status Sidebar */}
          <Col xs={24} lg={8}>
            {subscription?.active ? (
              <Card
                title={
                  <div style={{ display: 'flex', alignItems: 'center' }}>
                    <CrownOutlined style={{ marginRight: 8, color: '#f59e0b' }} />
                    <span style={{ color: '#1f2937' }}>Subscription Status</span>
                  </div>
                }
                style={{ 
                  borderRadius: '12px',
                  boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
                  border: '1px solid #e5e7eb'
                }}
                bodyStyle={{ padding: '24px' }}
              >
                <div style={{ marginBottom: 20 }}>
                  <div style={{ 
                    padding: '16px', 
                    background: '#f0f9ff', 
                    borderRadius: '8px',
                    border: '1px solid #bae6fd',
                    marginBottom: 16
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', marginBottom: 8 }}>
                      <CheckCircleOutlined style={{ color: '#0ea5e9', marginRight: 8 }} />
                      <Text strong style={{ color: '#1f2937' }}>Current Plan</Text>
                    </div>
                    <Tag 
                      color="blue" 
                      style={{ 
                        fontSize: '14px', 
                        padding: '6px 12px',
                        borderRadius: '20px',
                        border: 'none',
                        fontWeight: 500
                      }}
                    >
                      {subscription.plan || 'Unknown'}
                    </Tag>
                  </div>
                  
                  <div style={{ 
                    padding: '16px', 
                    background: '#f0fdf4', 
                    borderRadius: '8px',
                    border: '1px solid #bbf7d0',
                    marginBottom: 16
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', marginBottom: 8 }}>
                      <CheckCircleOutlined style={{ color: '#22c55e', marginRight: 8 }} />
                      <Text strong style={{ color: '#1f2937' }}>Status</Text>
                    </div>
                    <Tag 
                      color="success" 
                      style={{ 
                        fontSize: '14px', 
                        padding: '6px 12px',
                        borderRadius: '20px',
                        border: 'none',
                        fontWeight: 500
                      }}
                    >
                      Active
                    </Tag>
                  </div>
                  
                  <div style={{ 
                    padding: '16px', 
                    background: '#fefce8', 
                    borderRadius: '8px',
                    border: '1px solid #fde047'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', marginBottom: 8 }}>
                      <CalendarOutlined style={{ color: '#eab308', marginRight: 8 }} />
                      <Text strong style={{ color: '#1f2937' }}>Renews On</Text>
                    </div>
                    <Text style={{ fontSize: '14px', color: '#374151' }}>{formattedDate}</Text>
                  </div>
                </div>
                
                <Button 
                  type="primary" 
                  onClick={handleCustomerPortal}
                  loading={portalLoading}
                  block
                  size="large"
                  icon={<CreditCardOutlined />}
                  style={{
                    height: '48px',
                    borderRadius: '8px',
                    fontSize: '15px',
                    fontWeight: 500,
                    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                    border: 'none'
                  }}
                >
                  Manage Subscription
                </Button>
                <Text type="secondary" style={{ 
                  display: 'block', 
                  marginTop: 12, 
                  textAlign: 'center',
                  fontSize: '12px'
                }}>
                  Secure billing portal powered by Stripe
                </Text>
              </Card>
            ) : (
              <Card
                style={{ 
                  borderRadius: '12px',
                  background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
                  border: 'none',
                  color: 'white'
                }}
                bodyStyle={{ padding: '32px', textAlign: 'center' }}
              >
                <Avatar 
                  size={64}
                  style={{ 
                    backgroundColor: 'rgba(255,255,255,0.2)', 
                    marginBottom: 20,
                    border: '3px solid rgba(255,255,255,0.3)'
                  }}
                  icon={<CrownOutlined style={{ fontSize: '24px', color: 'white' }} />}
                />
                <Title level={4} style={{ color: 'white', marginBottom: 12 }}>
                  Upgrade to Premium
                </Title>
                <Text style={{ 
                  color: 'rgba(255,255,255,0.9)', 
                  fontSize: '14px',
                  display: 'block',
                  marginBottom: 24
                }}>
                  Unlock advanced features and get the most out of your business profile
                </Text>
                <Button 
                  type="primary"
                  onClick={handleSubscribe}
                  size="large"
                  style={{
                    background: 'white',
                    color: '#f5576c',
                    border: 'none',
                    height: '44px',
                    fontWeight: 600,
                    borderRadius: '8px'
                  }}
                >
                  View Subscription Plans
                </Button>
              </Card>
            )}
  
            {/* Help Card */}
            <Card 
              style={{ 
                marginTop: 24,
                borderRadius: '12px',
                background: 'linear-gradient(135deg, #e0e7ff 0%, #c7d2fe 100%)',
                border: '1px solid #c7d2fe'
              }}
              bodyStyle={{ padding: '24px', textAlign: 'center' }}
            >
              <QuestionCircleOutlined style={{ fontSize: '32px', color: '#4f46e5', marginBottom: 12 }} />
              <Title level={5} style={{ color: '#3730a3', marginBottom: 8 }}>
                Need Help?
              </Title>
              <Text style={{ color: '#4338ca', fontSize: '13px', display: 'block', marginBottom: 16 }}>
                Our support team can help you set up your business profile for optimal results.
              </Text>
              <Button 
                style={{
                  background: '#4f46e5',
                  border: 'none',
                  color: 'white',
                  borderRadius: '6px',
                  fontWeight: 500
                }}
                size="small"
              >
                Get Support
              </Button>
            </Card>
          </Col>
        </Row>
      </div>
    );
};

export default BusinessProfile;
