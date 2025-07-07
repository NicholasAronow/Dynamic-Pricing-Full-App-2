import React from 'react';
import { Typography, Card, Space, Divider } from 'antd';
import {
  MailOutlined,
  PhoneOutlined
} from '@ant-design/icons';

const { Title, Paragraph, Text } = Typography;

const Support: React.FC = () => {
  return (
    <div style={{ maxWidth: '800px', margin: '0 auto', padding: '40px 24px' }}>
      <Title level={2}>Support</Title>
      <Paragraph style={{ fontSize: '16px', marginBottom: '32px' }}>
        Need help with Adaptiv? Our team is here to assist you with any questions or issues.
      </Paragraph>
      
      <Card
        bordered={false}
        style={{ 
          boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)', 
          borderRadius: '8px',
          padding: '12px'
        }}
      >
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <div>
            <Title level={4} style={{ marginBottom: '24px', marginTop: '12px' }}>
              Contact Information
            </Title>
            
            <Space direction="vertical" size="large">
              <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                <div style={{ 
                  width: '48px', 
                  height: '48px', 
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', 
                  borderRadius: '50%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}>
                  <MailOutlined style={{ fontSize: '20px', color: 'white' }} />
                </div>
                <div>
                  <Text strong style={{ fontSize: '16px', display: 'block', marginBottom: '4px' }}>
                    Email Support
                  </Text>
                  <Text style={{ fontSize: '15px', color: '#7546C9' }}>
                    nickaronow@adaptiv.com
                  </Text>
                </div>
              </div>
              
              <Divider style={{ margin: '20px 0' }} />
              
              <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                <div style={{ 
                  width: '48px', 
                  height: '48px', 
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', 
                  borderRadius: '50%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}>
                  <PhoneOutlined style={{ fontSize: '20px', color: 'white' }} />
                </div>
                <div>
                  <Text strong style={{ fontSize: '16px', display: 'block', marginBottom: '4px' }}>
                    Phone Support
                  </Text>
                  <Text style={{ fontSize: '15px', color: '#7546C9' }}>
                    (516) 404-1316
                  </Text>
                  <Text style={{ fontSize: '14px', display: 'block', color: '#6b7280', marginTop: '4px' }}>
                    Available 24/7
                  </Text>
                </div>
              </div>
            </Space>
          </div>
        </Space>
      </Card>
    </div>
  );
};

export default Support;
