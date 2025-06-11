import React from 'react';
import { Form, Checkbox, Typography, Card } from 'antd';

const { Title, Paragraph, Text } = Typography;

interface TermsConditionsStepProps {
  formData: any;
  updateFormData: (data: any) => void;
}

const TermsConditionsStep: React.FC<TermsConditionsStepProps> = ({ formData, updateFormData }) => {
  const [form] = Form.useForm();
  
  const handleValuesChange = (_: any, allValues: any) => {
    updateFormData(allValues);
  };

  return (
    <div className="registration-step">
      <Title level={4}>Terms and Conditions</Title>
      <Paragraph>Please read and agree to our terms and conditions to continue.</Paragraph>
      
      <Card className="terms-card" style={{ maxHeight: '300px', overflow: 'auto', marginBottom: '20px' }}>
        <Title level={5}>Terms of Service Agreement</Title>
        <Paragraph>
          Last updated: June 2025
        </Paragraph>
        
        <Paragraph>
          <strong>1. AGREEMENT TO TERMS</strong>
        </Paragraph>
        <Paragraph>
          These Terms of Use constitute a legally binding agreement made between you and Adaptiv, concerning your access to and use of the Adaptiv platform and services.
        </Paragraph>
        
        <Paragraph>
          <strong>2. INTELLECTUAL PROPERTY RIGHTS</strong>
        </Paragraph>
        <Paragraph>
          Unless otherwise indicated, the Adaptiv platform is our proprietary property and all source code, databases, functionality, software, website designs, audio, video, text, photographs, and graphics on the platform and the trademarks, service marks, and logos contained therein are owned or controlled by us or licensed to us, and are protected by copyright and trademark laws.
        </Paragraph>
        
        <Paragraph>
          <strong>3. USER REPRESENTATIONS</strong>
        </Paragraph>
        <Paragraph>
          By using the Adaptiv platform, you represent and warrant that: (1) you have the legal capacity to agree to these Terms of Use; (2) you are not a minor in the jurisdiction in which you reside; (3) you will not access the Adaptiv platform through automated or non-human means; (4) you will not use the Adaptiv platform for any illegal or unauthorized purpose; and (5) your use of the Adaptiv platform will not violate any applicable law or regulation.
        </Paragraph>
        
        <Paragraph>
          <strong>4. PROHIBITED ACTIVITIES</strong>
        </Paragraph>
        <Paragraph>
          You may not access or use the Adaptiv platform for any purpose other than that for which we make the platform available. The Adaptiv platform may not be used in connection with any commercial endeavors except those that are specifically endorsed or approved by us.
        </Paragraph>
        
        <Paragraph>
          <strong>5. PRIVACY POLICY</strong>
        </Paragraph>
        <Paragraph>
          We care about data privacy and security. Please review our Privacy Policy at adaptiv.ai/privacy. By using the Adaptiv platform, you agree to be bound by our Privacy Policy, which is incorporated into these Terms of Use.
        </Paragraph>
        
        <Paragraph>
          <strong>6. TERM AND TERMINATION</strong>
        </Paragraph>
        <Paragraph>
          These Terms of Use shall remain in full force and effect while you use the Adaptiv platform. We may terminate your use or participation in the platform or delete your account and any content or information that you posted at any time, without warning, in our sole discretion.
        </Paragraph>
        
        <Paragraph>
          <strong>7. GOVERNING LAW</strong>
        </Paragraph>
        <Paragraph>
          These Terms of Use and your use of the Adaptiv platform are governed by and construed in accordance with the laws of the State of California applicable to agreements made and to be entirely performed within the State of California, without regard to its conflict of law principles.
        </Paragraph>
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
