import React, { useState, useEffect } from 'react';
import { Card, Button, Typography, Table, Spin, message, Empty, Tabs, Badge } from 'antd';
import { ReloadOutlined, SyncOutlined, CheckCircleOutlined, InfoCircleOutlined } from '@ant-design/icons';
import { useLocation } from 'react-router-dom';
import { integrationService } from '../../services/integrationService';

const { Title, Text, Paragraph } = Typography;
const { TabPane } = Tabs;

interface SquareOrder {
  id: string;
  created_at: string;
  total_money?: {
    amount: number;
    currency: string;
  };
  state: string;
  line_items?: any[];
}

/**
 * Component for testing and viewing Square orders
 * This is a dedicated page for administrators to test the Square integration
 */
const SquareOrderTester: React.FC = () => {
  const [orders, setOrders] = useState<SquareOrder[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [syncing, setSyncing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [syncStats, setSyncStats] = useState<any>(null);
  const location = useLocation();

  // Check for success parameter in URL on component mount
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    if (params.get('success') === 'true') {
      message.success('Square account connected successfully!');
      // Fetch orders automatically when redirected with success
      fetchOrders();
    }
  }, [location]);

  // Fetch orders from Square
  const fetchOrders = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await integrationService.getSquareOrders();
      console.log('Square Orders Response:', response);

      if (response && response.orders) {
        setOrders(response.orders);
        if (response.orders.length === 0) {
          message.info('No orders found in your Square account.');
        }
      } else {
        setOrders([]);
        message.info('No orders returned from Square.');
      }
    } catch (err: any) {
      console.error('Error fetching Square orders:', err);
      setError(err.response?.data?.detail || 'Failed to fetch orders from Square.');
    } finally {
      setLoading(false);
    }
  };

  // Sync Square data to local database
  const syncData = async () => {
    setSyncing(true);
    try {
      const response = await integrationService.syncSquareData();
      console.log('Sync response:', response);
      
      if (response.success) {
        message.success('Square data synced successfully!');
        setSyncStats(response);
      } else {
        message.error(response.error || 'Failed to sync Square data.');
      }
      
      // Refresh orders after sync
      fetchOrders();
    } catch (err: any) {
      console.error('Error syncing Square data:', err);
      message.error(err.response?.data?.detail || 'Failed to sync Square data.');
    } finally {
      setSyncing(false);
    }
  };

  // Fetch orders on component mount
  useEffect(() => {
    fetchOrders();
  }, []);

  // Table columns for orders
  const columns = [
    {
      title: 'Order ID',
      dataIndex: 'id',
      key: 'id',
      render: (text: string) => <Text copyable>{text}</Text>,
    },
    {
      title: 'Date',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (text: string) => new Date(text).toLocaleString(),
    },
    {
      title: 'Amount',
      dataIndex: 'total_money',
      key: 'total_money',
      render: (money: any) => 
        money ? `${(money.amount / 100).toFixed(2)} ${money.currency}` : 'N/A',
    },
    {
      title: 'Status',
      dataIndex: 'state',
      key: 'state',
      render: (state: string) => (
        <Badge 
          status={state === 'COMPLETED' ? 'success' : 'processing'} 
          text={state}
        />
      ),
    },
    {
      title: 'Items',
      dataIndex: 'line_items',
      key: 'line_items',
      render: (items: any[]) => items ? items.length : 0,
    }
  ];

  return (
    <Card title={
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title level={4} style={{ margin: 0 }}>Square Integration Tester</Title>
        <div>
          <Button 
            type="primary" 
            icon={<ReloadOutlined />} 
            onClick={fetchOrders}
            loading={loading}
            style={{ marginRight: 8 }}
          >
            Refresh Orders
          </Button>
          <Button 
            icon={<SyncOutlined />}
            onClick={syncData}
            loading={syncing}
          >
            Sync Square Data
          </Button>
        </div>
      </div>
    }>
      {error && (
        <div style={{ marginBottom: 16, color: 'red' }}>
          <Text type="danger">{error}</Text>
        </div>
      )}

      {syncStats && (
        <div style={{ marginBottom: 16, padding: 16, background: '#f0f7ff', borderRadius: 4, border: '1px solid #d0e3ff' }}>
          <Title level={5}><CheckCircleOutlined style={{ color: '#52c41a' }} /> Sync Completed</Title>
          <Paragraph>
            <ul>
              <li><Text strong>Items created:</Text> {syncStats.items_created}</li>
              <li><Text strong>Items updated:</Text> {syncStats.items_updated}</li>
              <li><Text strong>Orders imported:</Text> {syncStats.orders_created}</li>
            </ul>
          </Paragraph>
        </div>
      )}

      <Tabs defaultActiveKey="orders">
        <TabPane tab="Orders" key="orders">
          {loading ? (
            <div style={{ textAlign: 'center', padding: 24 }}>
              <Spin size="large" />
              <div style={{ marginTop: 16 }}>Loading orders from Square...</div>
            </div>
          ) : orders.length > 0 ? (
            <Table 
              dataSource={orders} 
              columns={columns} 
              rowKey="id"
              pagination={{ pageSize: 10 }}
              expandable={{
                expandedRowRender: record => (
                  <div>
                    <Title level={5}>Line Items</Title>
                    {record.line_items && record.line_items.length > 0 ? (
                      <ul>
                        {record.line_items.map((item: any, index: number) => (
                          <li key={index}>
                            {item.name || item.catalog_object_id} - 
                            Quantity: {item.quantity} - 
                            {item.base_price_money && 
                              `Price: ${(item.base_price_money.amount / 100).toFixed(2)} ${item.base_price_money.currency}`
                            }
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <Text>No line items found</Text>
                    )}
                  </div>
                ),
              }}
            />
          ) : (
            <Empty 
              description="No orders found in your Square account" 
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            />
          )}
        </TabPane>
        <TabPane tab="How to Test" key="howto">
          <div style={{ padding: 16 }}>
            <Title level={4}>Testing your Square Integration</Title>
            
            <Title level={5}>1. Check Orders</Title>
            <Text>Use the "Refresh Orders" button to fetch the latest orders from your connected Square account.</Text>
            
            <Title level={5} style={{ marginTop: 16 }}>2. Sync Data</Title>
            <Text>The "Sync Square Data" button will synchronize your Square catalog and orders with your Adaptiv database.</Text>
            
            <Title level={5} style={{ marginTop: 16 }}>3. Add Test Orders</Title>
            <Text>
              To add test orders to your Square sandbox account, you can:
              <ul>
                <li>Use the Square Sandbox Dashboard to manually create orders</li>
                <li>Use the Square Developer API to programmatically create orders</li>
                <li>Use the Square Point of Sale app in sandbox mode</li>
              </ul>
            </Text>

            <Title level={5} style={{ marginTop: 16 }}>4. View Your Data</Title>
            <Text>
              After syncing, your Square data will be available in your Adaptiv dashboard:
              <ul>
                <li>Menu items will appear in your products list</li>
                <li>Orders will be included in sales data and analytics</li>
                <li>Price changes will be tracked in price history</li>
              </ul>
            </Text>
            
            <div style={{ marginTop: 24, padding: 16, background: '#fffbe6', borderRadius: 4, border: '1px solid #ffe58f' }}>
              <Title level={5}><InfoCircleOutlined style={{ color: '#faad14' }} /> Important Notes</Title>
              <Text>
                <ul>
                  <li>Square sandbox accounts don't have real transaction data by default</li>
                  <li>You may need to create test data to fully test the integration</li>
                  <li>Only completed orders will be imported</li>
                  <li>Price recommendations will work with imported Square data</li>
                </ul>
              </Text>
            </div>
          </div>
        </TabPane>
      </Tabs>
    </Card>
  );
};

export default SquareOrderTester;
