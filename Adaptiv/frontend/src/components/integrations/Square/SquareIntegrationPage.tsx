import React, { useState, useEffect } from 'react';
import { Card, Button, Typography, List, Divider, message, Spin, Alert, Empty, Space, Tag, Tooltip } from 'antd';
import { CheckCircleOutlined, CloseCircleOutlined, SyncOutlined, ShopOutlined, ShoppingOutlined, LinkOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { integrationService } from '../../../services/integrationService';
import api from '../../../services/api';

const { Title, Text, Paragraph } = Typography;

interface SquareIntegration {
  id: number;
  merchant_id: string;
  merchant_name: string;
  access_token: string; // Will be masked
  refresh_token: string; // Will be masked
  token_expires_at: string;
  locations: any[];
  webhook_id?: string;
  created_at: string;
  updated_at: string;
  last_sync_at?: string;
}

/**
 * Component to manage Square integration settings
 */
const SquareIntegrationPage: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState<boolean>(true);
  const [integration, setIntegration] = useState<SquareIntegration | null>(null);
  const [syncInProgress, setSyncInProgress] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Get integration status on component mount
  useEffect(() => {
    fetchIntegrationStatus();
  }, []);

  // Fetch integration status from the API
  const fetchIntegrationStatus = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get('/api/integrations/square/status');
      if (response.data && response.data.integration) {
        console.log('Integration status:', response.data.integration);
        setIntegration(response.data.integration);
      } else {
        setIntegration(null);
      }
    } catch (err: any) {
      console.error('Error fetching Square integration status:', err);
      setError(err.response?.data?.detail || 'Failed to fetch Square integration status.');
      setIntegration(null);
    } finally {
      setLoading(false);
    }
  };

  // Connect Square account (start OAuth flow)
  const handleConnectSquare = async () => {
    try {
      console.log('Initiating Square OAuth flow');
      const authUrl = await integrationService.getSquareAuthUrl();
      
      if (authUrl) {
        // Redirect to Square's authorization page
        window.location.href = authUrl;
      } else {
        message.error('Failed to get Square authorization URL.');
      }
    } catch (err) {
      console.error('Error starting Square OAuth flow:', err);
      message.error('Failed to connect to Square. Please try again.');
    }
  };

  // Sync data from Square
  const syncSquareData = async () => {
    setSyncInProgress(true);
    try {
      const response = await integrationService.syncSquareData();
      console.log('Sync response:', response);
      
      if (response.success) {
        message.success('Square data synced successfully!');
        // Refresh integration status
        fetchIntegrationStatus();
      } else {
        message.error(response.error || 'Failed to sync Square data.');
      }
    } catch (err: any) {
      console.error('Error syncing Square data:', err);
      message.error(err.response?.data?.detail || 'Failed to sync Square data.');
    } finally {
      setSyncInProgress(false);
    }
  };

  // Disconnect Square account
  const disconnectSquare = async () => {
    if (!window.confirm('Are you sure you want to disconnect your Square account? This will remove all your integration settings.')) {
      return;
    }
    
    try {
      await api.delete('/api/integrations/square');
      message.success('Square account disconnected successfully.');
      setIntegration(null);
    } catch (err: any) {
      console.error('Error disconnecting Square account:', err);
      message.error(err.response?.data?.detail || 'Failed to disconnect Square account.');
    }
  };

  // Format date string for display
  const formatDate = (dateString: string) => {
    if (!dateString) return 'N/A';
    try {
      return new Date(dateString).toLocaleString();
    } catch (e) {
      return dateString;
    }
  };

  // Render the integration details if connected
  const renderIntegrationDetails = () => {
    if (!integration) return null;

    // Extract needed information
    const { merchant_name, merchant_id, created_at, updated_at, last_sync_at, token_expires_at, locations, webhook_id } = integration;
    
    return (
      <div>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Alert
            message="Square Account Connected"
            description={`Your Square account "${merchant_name}" is connected and ready to use.`}
            type="success"
            showIcon
            icon={<CheckCircleOutlined />}
          />
          
          <List
            bordered
            header={<Title level={5}>Connection Details</Title>}
            dataSource={[
              { label: 'Merchant Name', value: merchant_name },
              { label: 'Merchant ID', value: merchant_id },
              { label: 'Connected On', value: formatDate(created_at) },
              { label: 'Last Updated', value: formatDate(updated_at) },
              { label: 'Last Sync', value: last_sync_at ? formatDate(last_sync_at) : 'Never synced' },
              { label: 'Token Expires', value: formatDate(token_expires_at) },
              { 
                label: 'Webhook Status', 
                value: webhook_id ? 
                  <Tag color="green"><CheckCircleOutlined /> Registered</Tag> : 
                  <Tag color="red"><CloseCircleOutlined /> Not Registered</Tag>
              },
              { 
                label: 'Locations', 
                value: locations && locations.length ? (
                  <List
                    size="small"
                    bordered={false}
                    dataSource={locations}
                    renderItem={(location: any) => (
                      <List.Item>
                        <Text>{location.name}</Text>
                        <Tag color="blue">{location.id}</Tag>
                      </List.Item>
                    )}
                  />
                ) : 'No locations found'
              }
            ]}
            renderItem={item => (
              <List.Item>
                <Text strong>{item.label}:</Text> {item.value}
              </List.Item>
            )}
          />
          
          <Space>
            <Button 
              type="primary" 
              icon={<SyncOutlined />} 
              onClick={syncSquareData}
              loading={syncInProgress}
            >
              Sync Square Data
            </Button>
            <Button 
              type="default" 
              icon={<ShopOutlined />} 
              onClick={() => window.open('https://squareup.com/dashboard', '_blank')}
            >
              Open Square Dashboard
            </Button>
            <Button 
              type="default" 
              icon={<LinkOutlined />} 
              onClick={() => navigate('/square-test')}
            >
              Test Square Integration
            </Button>
            <Button 
              danger 
              onClick={disconnectSquare}
            >
              Disconnect
            </Button>
          </Space>
        </Space>
      </div>
    );
  };

  // Render the not connected state
  const renderNotConnected = () => {
    return (
      <div style={{ textAlign: 'center', padding: '30px 0' }}>
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="No Square account connected"
        />
        <Paragraph style={{ marginTop: 16 }}>
          Connect your Square account to import your sales data and menu items.
          Get personalized insights and price recommendations based on your actual sales.
        </Paragraph>
        <Button 
          type="primary" 
          size="large"
          icon={<ShoppingOutlined />}
          onClick={handleConnectSquare}
          style={{ marginTop: 16 }}
        >
          Connect Square Account
        </Button>
      </div>
    );
  };

  return (
    <div>
      <Title level={2}>Square Integration</Title>
      <Paragraph>
        Connect your Square account to seamlessly sync your menu items and sales data with Adaptiv's dynamic pricing engine.
      </Paragraph>
      
      <Card>
        {loading ? (
          <div style={{ textAlign: 'center', padding: '50px 0' }}>
            <Spin size="large" />
            <div style={{ marginTop: 16 }}>Loading integration status...</div>
          </div>
        ) : error ? (
          <Alert
            message="Error Loading Integration"
            description={error}
            type="error"
            showIcon
          />
        ) : integration ? (
          renderIntegrationDetails()
        ) : (
          renderNotConnected()
        )}
      </Card>

      <Divider />
      
      <Title level={3}>About Square Integration</Title>
      <Paragraph>
        The Square integration allows you to:
      </Paragraph>
      <ul>
        <li><Text strong>Import your menu items</Text> - All your Square catalog items are automatically imported</li>
        <li><Text strong>Sync sales data</Text> - Your historical sales data is imported to generate accurate pricing recommendations</li>
        <li><Text strong>Get real-time updates</Text> - New orders are automatically synced via webhooks</li>
        <li><Text strong>Implement price changes</Text> - Apply price recommendations directly to your Square menu</li>
      </ul>
      
      <Paragraph>
        <Text type="secondary">
          Note: This integration uses Square's OAuth2 authentication to securely connect to your account without requiring your Square login credentials.
        </Text>
      </Paragraph>
    </div>
  );
};

export default SquareIntegrationPage;
