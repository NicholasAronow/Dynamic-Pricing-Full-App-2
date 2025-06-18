import React, { useState } from 'react';
import { Steps, Button, message, Card, Typography } from 'antd';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../services/api';
import './MultiStepRegistration.css';

// Step components
import BasicRegistrationStep from './steps/BasicRegistrationStep';
import BusinessProfileStep from './steps/BusinessProfileStep';
import TermsConditionsStep from './steps/TermsConditionsStep';

const { Title } = Typography;

interface RegistrationData {
  // Basic registration
  email: string;
  password: string;
  // Business profile
  business_name: string;
  industry: string;
  company_size: string;
  founded_year?: number;
  description?: string;
  street_address?: string;
  city?: string;
  state?: string;
  postal_code?: string;
  country?: string;
  // Terms and conditions
  agreedToTerms: boolean;
}

const MultiStepRegistration: React.FC = () => {
  const [current, setCurrent] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { register } = useAuth();
  const navigate = useNavigate();

  // Store all form data across steps
  const [formData, setFormData] = useState<RegistrationData>({
    email: '',
    password: '',
    business_name: '',
    industry: '',
    company_size: '',
    agreedToTerms: false
  });

  const steps = [
    {
      title: 'Account',
      content: <BasicRegistrationStep 
        formData={formData} 
        updateFormData={(data: any) => setFormData({...formData, ...data})}
      />,
    },
    {
      title: 'Business Profile',
      content: <BusinessProfileStep 
        formData={formData}
        updateFormData={(data: any) => setFormData({...formData, ...data})}
      />,
    },
    {
      title: 'Terms & Conditions',
      content: <TermsConditionsStep
        formData={formData}
        updateFormData={(data: any) => setFormData({...formData, ...data})}
      />,
    },
  ];

  // Create business profile in backend
  const createBusinessProfile = async () => {
    try {
      const profileData = {
        business_name: formData.business_name,
        industry: formData.industry,
        company_size: formData.company_size,
        founded_year: formData.founded_year,
        description: formData.description,
        street_address: formData.street_address,
        city: formData.city,
        state: formData.state,
        postal_code: formData.postal_code,
        country: formData.country,
      };

      const response = await api.post('profile/business', profileData);
      return response.data;
    } catch (err) {
      console.error('Failed to create business profile:', err);
      throw err;
    }
  };

  // No competitor tracking setup needed

  const handleNext = () => {
    setCurrent(current + 1);
  };

  const handlePrev = () => {
    setCurrent(current - 1);
  };

  const handleFinish = async () => {
    try {
      setLoading(true);
      setError(null);

      // 1. Register the user
      await register(formData.email, formData.password);
      
      // 2. Create business profile
      await createBusinessProfile();

      // Registration complete
      message.success('Registration completed successfully!');
      
      // Navigate to Dashboard
      navigate('/dashboard');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to complete registration. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <Card className="auth-form multi-step-form">
        <Title level={2} className="auth-title">Register for Adaptiv</Title>
        
        <Steps current={current} className="registration-steps">
          {steps.map(item => (
            <Steps.Step key={item.title} title={item.title} />
          ))}
        </Steps>
        
        <div className="steps-content">
          {error && (
            <div className="error-message">
              {error}
            </div>
          )}
          {steps[current].content}
        </div>
        
        <div className="steps-action">
          {current > 0 && (
            <Button style={{ margin: '0 8px' }} onClick={handlePrev}>
              Previous
            </Button>
          )}
          
          {current < steps.length - 1 && (
            <Button 
              type="primary" 
              onClick={handleNext}
              disabled={current === 2 && !formData.agreedToTerms}
            >
              Next
            </Button>
          )}
          
          {current === steps.length - 1 && (
            <Button 
              type="primary" 
              onClick={handleFinish}
              loading={loading}
              disabled={!formData.agreedToTerms}
            >
              Complete Registration
            </Button>
          )}
        </div>
      </Card>
    </div>
  );
};

export default MultiStepRegistration;
