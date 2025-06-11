import React from 'react';
import { Form, Input, Select, Typography, Row, Col } from 'antd';
import { BankOutlined } from '@ant-design/icons';

const { Title, Paragraph } = Typography;
const { Option } = Select;
const { TextArea } = Input;

interface BusinessProfileStepProps {
  formData: any;
  updateFormData: (data: any) => void;
}

const BusinessProfileStep: React.FC<BusinessProfileStepProps> = ({ formData, updateFormData }) => {
  const [form] = Form.useForm();
  
  const currentYear = new Date().getFullYear();
  const yearsArray = Array.from({ length: 100 }, (_, i) => currentYear - i);
  
  const handleValuesChange = (_: any, allValues: any) => {
    updateFormData(allValues);
  };

  return (
    <div className="registration-step">
      <Title level={4}>Tell Us About Your Business</Title>
      <Paragraph>This information helps us personalize your experience and find local competitors.</Paragraph>
      
      <Form
        form={form}
        layout="vertical"
        initialValues={{
          business_name: formData.business_name || '',
          industry: formData.industry || '',
          company_size: formData.company_size || '',
          founded_year: formData.founded_year,
          description: formData.description || '',
          street_address: formData.street_address || '',
          city: formData.city || '',
          state: formData.state || '',
          postal_code: formData.postal_code || '',
          country: formData.country || 'USA',
        }}
        onValuesChange={handleValuesChange}
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
            rows={3} 
            placeholder="Brief description of your company" 
          />
        </Form.Item>

        <Title level={5} style={{ marginTop: 16 }}>Location Information</Title>
        <Paragraph>This information helps our agents find local competitors in your area.</Paragraph>
        
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
        >
          <Select>
            <Option value="USA">United States</Option>
            <Option value="Canada">Canada</Option>
            <Option value="Mexico">Mexico</Option>
            <Option value="Other">Other</Option>
          </Select>
        </Form.Item>
      </Form>
    </div>
  );
};

export default BusinessProfileStep;
