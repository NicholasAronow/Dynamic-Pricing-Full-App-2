import React, { useState, useEffect } from 'react';
import { Form, Checkbox, Typography, Card } from 'antd';
import ReactMarkdown from 'react-markdown';

const { Title, Paragraph, Text } = Typography;

interface TermsConditionsStepProps {
  formData: any;
  updateFormData: (data: any) => void;
}

const TermsConditionsStep: React.FC<TermsConditionsStepProps> = ({ formData, updateFormData }) => {
  const [form] = Form.useForm();
  const [termsContent, setTermsContent] = useState<string>('');
  
  useEffect(() => {
    // Fetch the markdown content from the file
    fetch('/assets/markdown/terms-conditions.md')
      .then(response => response.text())
      .then(text => setTermsContent(text))
      .catch(error => console.error('Error loading terms and conditions:', error));
  }, []);
  
  const handleValuesChange = (_: any, allValues: any) => {
    updateFormData(allValues);
  };

  return (
    <div className="registration-step">
      <Title level={4}>Terms and Conditions</Title>
      <Paragraph>Please read and agree to our terms and conditions to continue.</Paragraph>
      
      <Card className="terms-card" style={{ maxHeight: '300px', overflow: 'auto', marginBottom: '20px' }}>
        {termsContent ? (
          <ReactMarkdown>{termsContent}</ReactMarkdown>
        ) : (
          <Paragraph>Loading terms and conditions...</Paragraph>
        )}
      </Card>
      
      <Form
        form={form}
        layout="vertical"
        initialValues={{
          agreedToTerms: formData.agreedToTerms || false
        }}
        onValuesChange={handleValuesChange}
      >
        <Form.Item
          name="agreedToTerms"
          valuePropName="checked"
          rules={[
            { 
              validator: (_, value) => 
                value ? Promise.resolve() : Promise.reject(new Error('You must agree to the terms and conditions')) 
            }
          ]}
        >
          <Checkbox>
            I have read and agree to the <Text strong>Terms of Service</Text> and <Text strong>Privacy Policy</Text>
          </Checkbox>
        </Form.Item>
      </Form>
    </div>
  );
};

export default TermsConditionsStep;
