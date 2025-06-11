import React, { useState } from 'react';
import { Form, Radio, Typography, Card, Space, Button, message, Spin } from 'antd';
import { ShoppingOutlined, RightOutlined, ClockCircleOutlined, LinkOutlined } from '@ant-design/icons';
import { integrationService } from '../../../services/integrationService';

const { Title, Paragraph, Text } = Typography;

interface PosIntegrationStepProps {
  formData: any;
  updateFormData: (data: any) => void;
}

const PosIntegrationStep: React.FC<PosIntegrationStepProps> = ({ formData, updateFormData }) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  
  const handleValuesChange = (_: any, allValues: any) => {
    updateFormData(allValues);
  };
  
  const connectToSquare = async () => {
    try {
      setLoading(true);
      console.log('Requesting Square auth URL...');
      const authUrl = await integrationService.getSquareAuthUrl();
      console.log('Received Square auth URL:', authUrl);
      
      if (authUrl) {
        // Open in a new tab instead of redirecting
        window.open(authUrl, '_blank');
        message.success('Square integration page opened in a new tab. Please complete the authorization there.');
      } else {
        message.error('Failed to get Square authorization URL. Please try again later.');
      }
    } catch (error) {
      console.error('Square integration error:', error);
      message.error('Failed to start Square integration. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="registration-step">
      <Title level={4}>Connect Your POS System</Title>
      <Paragraph>
        Connect your Point of Sale system to automatically import your menu items, 
        sales data, and inventory for pricing optimization.
      </Paragraph>
      
      <Form
        form={form}
        layout="vertical"
        initialValues={{
          connectPosNow: formData.connectPosNow
        }}
        onValuesChange={handleValuesChange}
      >
        <Form.Item name="connectPosNow">
          <Radio.Group>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Card 
                hoverable 
                className={`selection-card ${formData.connectPosNow ? 'selected' : ''}`}
                onClick={() => form.setFieldsValue({ connectPosNow: true })}
              >
                <Space>
                  <ShoppingOutlined style={{ fontSize: '24px', color: '#1890ff' }} />
                  <div>
                    <Text strong>Connect now</Text>
                    <Paragraph style={{ marginBottom: 0 }}>
                      Connect to your POS system immediately after registration
                    </Paragraph>
                  </div>
                  <RightOutlined style={{ marginLeft: 'auto' }} />
                </Space>
              </Card>
              
              <Card 
                hoverable 
                className={`selection-card ${formData.connectPosNow === false ? 'selected' : ''}`}
                onClick={() => form.setFieldsValue({ connectPosNow: false })}
              >
                <Space>
                  <ClockCircleOutlined style={{ fontSize: '24px', color: '#52c41a' }} />
                  <div>
                    <Text strong>Connect later</Text>
                    <Paragraph style={{ marginBottom: 0 }}>
                      Skip for now and connect your POS system anytime from your dashboard
                    </Paragraph>
                  </div>
                  <RightOutlined style={{ marginLeft: 'auto' }} />
                </Space>
              </Card>
            </Space>
          </Radio.Group>
        </Form.Item>

        {formData.connectPosNow && (
          <Card bordered={false} style={{ backgroundColor: '#f5f5f5', marginTop: 20 }}>
            <Title level={5}>Connect Your POS System</Title>
            
            <Card 
              hoverable 
              style={{ marginBottom: 15, borderColor: '#1890ff' }}
              onClick={!loading ? connectToSquare : undefined}
            >
              <Space align="center">
                <div style={{ 
                  backgroundColor: '#1890ff', 
                  borderRadius: '50%', 
                  width: 40, 
                  height: 40, 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'center' 
                }}>
                  <LinkOutlined style={{ fontSize: '20px', color: '#fff' }} />
                </div>
                <div>
                  <Text strong style={{ fontSize: 16 }}>Square</Text>
                  <Paragraph style={{ marginBottom: 0 }}>
                    Connect your Square account to import menus, sales, and inventory
                  </Paragraph>
                </div>
                {loading ? (
                  <Spin style={{ marginLeft: 'auto' }} />
                ) : (
                  <Button 
                    type="primary" 
                    style={{ marginLeft: 'auto' }}
                    onClick={connectToSquare}
                  >
                    Connect
                  </Button>
                )}
              </Space>
            </Card>
            
            <Space style={{ marginTop: 10 }} wrap>
              <Button type="default" disabled>Toast (Coming Soon)</Button>
              <Button type="default" disabled>Clover (Coming Soon)</Button>
              <Button type="default" disabled>Lightspeed (Coming Soon)</Button>
            </Space>
            
            <Paragraph style={{ marginTop: 12 }}>
              Don't see your POS? <a href="#">Contact us</a> to request integration support for your provider.
            </Paragraph>
          </Card>
        )}
      </Form>
    </div>
  );
};

export default PosIntegrationStep;
