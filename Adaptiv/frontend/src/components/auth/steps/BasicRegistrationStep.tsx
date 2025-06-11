import React from 'react';
import { Form, Input, Typography } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import { Link } from 'react-router-dom';

const { Title, Paragraph } = Typography;

interface BasicRegistrationStepProps {
  formData: any;
  updateFormData: (data: any) => void;
}

const BasicRegistrationStep: React.FC<BasicRegistrationStepProps> = ({ formData, updateFormData }) => {
  const [form] = Form.useForm();
  
  const handleValuesChange = (_: any, allValues: any) => {
    updateFormData(allValues);
  };

  return (
    <div className="registration-step">
      <Title level={4}>Create Your Account</Title>
      <Paragraph>Enter your email and create a password to begin.</Paragraph>
      
      <Form
        form={form}
        layout="vertical"
        initialValues={{
          email: formData.email,
          password: formData.password,
          confirm: formData.password
        }}
        onValuesChange={handleValuesChange}
      >
        <Form.Item
          name="email"
          rules={[
            { required: true, message: 'Please input your email!' },
            { type: 'email', message: 'Please enter a valid email!' }
          ]}
        >
          <Input 
            prefix={<UserOutlined />} 
            placeholder="Email" 
            size="large"
          />
        </Form.Item>
        
        <Form.Item
          name="password"
          rules={[
            { required: true, message: 'Please input your password!' },
            { min: 8, message: 'Password must be at least 8 characters!' }
          ]}
        >
          <Input.Password
            prefix={<LockOutlined />}
            placeholder="Password"
            size="large"
          />
        </Form.Item>
        
        <Form.Item
          name="confirm"
          dependencies={['password']}
          rules={[
            { required: true, message: 'Please confirm your password!' },
            ({ getFieldValue }) => ({
              validator(_, value) {
                if (!value || getFieldValue('password') === value) {
                  return Promise.resolve();
                }
                return Promise.reject(new Error('The two passwords do not match!'));
              },
            }),
          ]}
        >
          <Input.Password
            prefix={<LockOutlined />}
            placeholder="Confirm Password"
            size="large"
          />
        </Form.Item>
        
        <div className="auth-form-register">
          Already have an account? <Link to="/login">Login now!</Link>
        </div>
      </Form>
    </div>
  );
};

export default BasicRegistrationStep;
