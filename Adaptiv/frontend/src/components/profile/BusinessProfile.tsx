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
  Alert
} from 'antd';
import { BankOutlined } from '@ant-design/icons';
import axios from 'axios';

const { Title } = Typography;
const { Option } = Select;
const { TextArea } = Input;

interface BusinessProfileData {
  business_name: string;
  industry: string;
  company_size: string;
  founded_year?: number;
  description?: string;
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
      const response = await axios.get('/api/profile/business');
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
        await axios.post('/api/profile/business', values);
        notification.success({
          message: 'Success',
          description: 'Business profile created successfully!',
        });
      } else {
        await axios.put('/api/profile/business', values);
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
              <Option value="Technology">Technology</Option>
              <Option value="E-commerce">E-commerce</Option>
              <Option value="Manufacturing">Manufacturing</Option>
              <Option value="Healthcare">Healthcare</Option>
              <Option value="Finance">Finance</Option>
              <Option value="Education">Education</Option>
              <Option value="Retail">Retail</Option>
              <Option value="Hospitality">Hospitality</Option>
              <Option value="Transportation">Transportation</Option>
              <Option value="Other">Other</Option>
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
