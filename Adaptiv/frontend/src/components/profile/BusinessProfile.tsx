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
  Col
} from 'antd';
import { BankOutlined } from '@ant-design/icons';
import { api } from '../../services/api';

const { Title } = Typography;
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
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // State to store profile data
  const [, setProfile] = useState<BusinessProfileData | null>(null);
  const [mode, setMode] = useState<'create' | 'edit'>('create');

  const currentYear = new Date().getFullYear();
  const yearsArray = Array.from({ length: 100 }, (_, i) => currentYear - i);

  useEffect(() => {
    fetchProfile();
    // eslint-disable-next-line react-hooks/exhaustive-deps
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

  return (
    <div>
      <Title level={2}>Business Profile</Title>
      <Title level={5} type="secondary" style={{ marginTop: 0 }}>
        {mode === 'create' ? 'Create your business profile' : 'Update your business profile'}
      </Title>
      
      <Card style={{ maxWidth: 800, margin: '24px auto' }}>
        {error && (
          <Alert
            message="Error"
            description={error}
            type="error"
            showIcon
            style={{ marginBottom: 24 }}
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
          <Form.Item
            name="business_name"
            label="Business Name"
            rules={[{ required: true, message: 'Please enter your business name' }]}
          >
            <Input 
              prefix={<BankOutlined />} 
              placeholder="Enter your business name" 
            />
          </Form.Item>
          
          <Form.Item
            name="industry"
            label="Industry"
            rules={[{ required: true, message: 'Please select your industry' }]}
          >
            <Select placeholder="Select your industry">
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
          
          <Form.Item
            name="company_size"
            label="Company Size"
            rules={[{ required: true, message: 'Please select company size' }]}
          >
            <Select placeholder="Select company size">
              <Option value="1-10">1-10 employees</Option>
              <Option value="11-50">11-50 employees</Option>
              <Option value="51-200">51-200 employees</Option>
              <Option value="201-500">201-500 employees</Option>
              <Option value="501-1000">501-1000 employees</Option>
              <Option value="1001+">1001+ employees</Option>
            </Select>
          </Form.Item>
          
          <Form.Item
            name="founded_year"
            label="Year Founded"
          >
            <Select placeholder="Select year founded">
              {yearsArray.map(year => (
                <Option key={year} value={year}>{year}</Option>
              ))}
            </Select>
          </Form.Item>
          
          <Form.Item
            name="description"
            label="Company Description"
          >
            <TextArea 
              rows={4} 
              placeholder="Brief description of your company" 
            />
          </Form.Item>

          <Title level={4} style={{ marginTop: 24 }}>Location Information</Title>
          <p style={{ marginBottom: 16 }}>This information helps our agents find local competitors in your area.</p>
          
          <Form.Item
            name="street_address"
            label="Street Address"
          >
            <Input placeholder="123 Main St" />
          </Form.Item>
          
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                name="city"
                label="City"
              >
                <Input placeholder="New York" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="state"
                label="State"
              >
                <Input placeholder="NY" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="postal_code"
                label="Postal Code"
              >
                <Input placeholder="10001" />
              </Form.Item>
            </Col>
          </Row>
          
          <Form.Item
            name="country"
            label="Country"
            initialValue="USA"
          >
            <Select>
              <Option value="USA">United States</Option>
              <Option value="Canada">Canada</Option>
              <Option value="Mexico">Mexico</Option>
              <Option value="Other">Other</Option>
            </Select>
          </Form.Item>
          
          <Form.Item>
            <Button 
              type="primary" 
              htmlType="submit"
              loading={submitting}
              style={{ minWidth: 120 }}
            >
              {mode === 'create' ? 'Create Profile' : 'Update Profile'}
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
};

export default BusinessProfile;
