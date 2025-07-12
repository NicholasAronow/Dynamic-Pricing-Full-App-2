import React, { useState, useEffect } from 'react';
import { 
  Card, Row, Col, Statistic, Table, Button, Switch, message, Tag, Spin, Alert, 
  Modal, Descriptions, Tabs, Progress, Drawer, Space, Typography, Divider, Tooltip 
} from 'antd';
import { 
  UserOutlined, ShopOutlined, DollarOutlined, TrophyOutlined, CheckCircleOutlined, 
  StopOutlined, EyeOutlined, DownloadOutlined, CalendarOutlined, 
  TeamOutlined, ShoppingCartOutlined, MenuOutlined, BarChartOutlined 
} from '@ant-design/icons';
import { useAuth } from 'context/AuthContext';
import apiService from 'services/api';

const { Title, Text } = Typography;
const { TabPane } = Tabs;

interface SystemStats {
  total_users: number;
  active_users: number;
  admin_users: number;
  total_businesses: number;
  total_orders: number;
  total_items: number;
  total_revenue: number;
  users_last_30_days: number;
  orders_last_30_days: number;
  revenue_last_30_days: number;
  orders_today: number;
  revenue_today: number;
  subscription_breakdown: Record<string, number>;
  pos_integrations: number;
  avg_order_value: number;
}

interface UserSummary {
  id: number;
  email: string;
  is_admin: boolean;
  is_active: boolean;
  created_at: string;
  last_login?: string;
  business_name?: string;
  total_orders: number;
  total_revenue: number;
}

interface BusinessSummary {
  id: number;
  business_name: string;
  owner_email: string;
  created_at: string;
  total_orders: number;
  total_revenue: number;
  active_items: number;
}

interface UserMenuItem {
  id: number;
  name: string;
  description?: string;
  category: string;
  current_price: number;
  cost?: number;
  created_at: string;
  total_orders: number;
  total_revenue: number;
}

interface UserOrder {
  id: number;
  order_date: string;
  total_amount: number;
  total_cost?: number;
  gross_margin?: number;
  items_count: number;
  pos_id?: string;
}

interface DetailedUserInfo {
  id: number;
  email: string;
  name?: string;
  is_active: boolean;
  is_admin: boolean;
  subscription_tier?: string;
  created_at: string;
  business_name?: string;
  business_industry?: string;
  total_orders: number;
  total_revenue: number;
  total_items: number;
  pos_connected: boolean;
  last_order_date?: string;
  avg_order_value: number;
  menu_items: UserMenuItem[];
  recent_orders: UserOrder[];
}

const AdminDashboard: React.FC = () => {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [users, setUsers] = useState<UserSummary[]>([]);
  const [businesses, setBusinesses] = useState<BusinessSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [selectedUser, setSelectedUser] = useState<DetailedUserInfo | null>(null);
  const [userDetailsVisible, setUserDetailsVisible] = useState(false);
  const [userDetailsLoading, setUserDetailsLoading] = useState(false);

  useEffect(() => {
    fetchAdminData();
  }, []);

  const fetchAdminData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch system stats
      const statsResponse = await apiService.get('/admin/stats');
      setStats(statsResponse.data);

      // Fetch users
      const usersResponse = await apiService.get('/admin/users?limit=50');
      setUsers(usersResponse.data);

      // Fetch businesses
      const businessesResponse = await apiService.get('/admin/businesses?limit=50');
      setBusinesses(businessesResponse.data);

    } catch (error: any) {
      console.error('Error fetching admin data:', error);
      if (error.response?.status === 403) {
        setError('Access denied. Admin privileges required.');
      } else {
        setError('Failed to load admin data. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  const toggleUserAdmin = async (userId: number, currentStatus: boolean) => {
    try {
      await apiService.post(`/admin/users/${userId}/toggle-admin`);
      message.success(`User admin status ${currentStatus ? 'removed' : 'granted'} successfully`);
      fetchAdminData(); // Refresh data
    } catch (error: any) {
      console.error('Error toggling admin status:', error);
      if (error.response?.data?.detail) {
        message.error(error.response.data.detail);
      } else {
        message.error('Failed to update admin status');
      }
    }
  };

  const toggleUserActive = async (userId: number, currentStatus: boolean) => {
    try {
      await apiService.post(`/admin/users/${userId}/toggle-active`);
      message.success(`User ${currentStatus ? 'deactivated' : 'activated'} successfully`);
      fetchAdminData(); // Refresh data
    } catch (error: any) {
      console.error('Error toggling user status:', error);
      message.error('Failed to update user status');
    }
  };

  const viewUserDetails = async (userId: number) => {
    try {
      setUserDetailsLoading(true);
      const response = await apiService.get(`/admin/users/${userId}/details`);
      setSelectedUser(response.data);
      setUserDetailsVisible(true);
    } catch (error: any) {
      console.error('Error fetching user details:', error);
      message.error('Failed to load user details');
    } finally {
      setUserDetailsLoading(false);
    }
  };

  const exportUserData = async (userId: number, dataType: string) => {
    try {
      // Show loading message
      const hideLoading = message.loading('Preparing export...', 0);
      
      const response = await apiService.get(`/admin/users/${userId}/export?data_type=${dataType}`, {
        responseType: 'blob'
      });
      
      hideLoading();
      
      // Extract filename from response headers if available
      const contentDisposition = response.headers['content-disposition'];
      let filename = `user_${userId}_${dataType}_${new Date().toISOString().split('T')[0]}.csv`;
      
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
        if (filenameMatch) {
          filename = filenameMatch[1];
        }
      }
      
      // Create and trigger download
      const url = window.URL.createObjectURL(new Blob([response.data], { type: 'text/csv' }));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      // Show success message with data type info
      const dataTypeLabel = dataType === 'menu_items' ? 'Menu Items' : 
                           dataType === 'orders' ? 'Orders' : 'All Data';
      message.success(`${dataTypeLabel} exported successfully as CSV`);
      
    } catch (error: any) {
      console.error('Error exporting data:', error);
      const errorMsg = error.response?.data?.detail || 'Failed to export data';
      message.error(`Export failed: ${errorMsg}`);
    }
  };

  const userColumns = [
    {
      title: 'Email',
      dataIndex: 'email',
      key: 'email',
    },
    {
      title: 'Business',
      dataIndex: 'business_name',
      key: 'business_name',
      render: (name: string) => name || 'No business profile',
    },
    {
      title: 'Status',
      key: 'status',
      render: (record: UserSummary) => (
        <div>
          {record.is_admin && <Tag color="gold">Admin</Tag>}
          <Tag color={record.is_active ? 'green' : 'red'}>
            {record.is_active ? 'Active' : 'Inactive'}
          </Tag>
        </div>
      ),
    },
    {
      title: 'Orders',
      dataIndex: 'total_orders',
      key: 'total_orders',
    },
    {
      title: 'Revenue',
      dataIndex: 'total_revenue',
      key: 'total_revenue',
      render: (revenue: number) => `$${revenue?.toFixed(2) || '0.00'}`,
    },
    {
      title: 'Created',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => new Date(date).toLocaleDateString(),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (record: UserSummary) => (
        <Space size="small">
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => viewUserDetails(record.id)}
            loading={userDetailsLoading}
            size="small"
          >
            Details
          </Button>
          <Switch
            checked={record.is_admin}
            onChange={() => toggleUserAdmin(record.id, record.is_admin)}
            checkedChildren="Admin"
            unCheckedChildren="User"
            size="small"
          />
          <Switch
            checked={record.is_active}
            onChange={() => toggleUserActive(record.id, record.is_active)}
            checkedChildren={<CheckCircleOutlined />}
            unCheckedChildren={<StopOutlined />}
            size="small"
          />
        </Space>
      ),
    },
  ];

  const businessColumns = [
    {
      title: 'Business Name',
      dataIndex: 'business_name',
      key: 'business_name',
    },
    {
      title: 'Owner',
      dataIndex: 'owner_email',
      key: 'owner_email',
    },
    {
      title: 'Orders',
      dataIndex: 'total_orders',
      key: 'total_orders',
    },
    {
      title: 'Revenue',
      dataIndex: 'total_revenue',
      key: 'total_revenue',
      render: (revenue: number) => `$${revenue?.toFixed(2) || '0.00'}`,
    },
    {
      title: 'Active Items',
      dataIndex: 'active_items',
      key: 'active_items',
    },
    {
      title: 'Created',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => new Date(date).toLocaleDateString(),
    },
  ];

  if (!user?.is_admin) {
    return (
      <Alert
        message="Access Denied"
        description="You don't have permission to access the admin dashboard."
        type="error"
        showIcon
      />
    );
  }

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '400px' }}>
        <Spin size="large" />
      </div>
    );
  }

  if (error) {
    return (
      <Alert
        message="Error"
        description={error}
        type="error"
        showIcon
        action={
          <Button size="small" onClick={fetchAdminData}>
            Retry
          </Button>
        }
      />
    );
  }

  return (
    <div style={{ padding: '24px' }}>
      <Title level={2}>Admin Dashboard</Title>
      
      {/* Enhanced System Statistics */}
      <Row gutter={16} style={{ marginBottom: '24px' }}>
        <Col span={4}>
          <Card>
            <Statistic
              title="Total Users"
              value={stats?.total_users || 0}
              prefix={<UserOutlined />}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="Active Users"
              value={stats?.active_users || 0}
              prefix={<TeamOutlined />}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="Admin Users"
              value={stats?.admin_users || 0}
              prefix={<UserOutlined style={{ color: '#faad14' }} />}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="Total Businesses"
              value={stats?.total_businesses || 0}
              prefix={<ShopOutlined />}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="Total Orders"
              value={stats?.total_orders || 0}
              prefix={<ShoppingCartOutlined />}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="Menu Items"
              value={stats?.total_items || 0}
              prefix={<MenuOutlined />}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={16} style={{ marginBottom: '24px' }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="Total Revenue"
              value={stats?.total_revenue || 0}
              prefix={<DollarOutlined />}
              precision={2}
              formatter={(value) => `$${value}`}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Avg Order Value"
              value={stats?.avg_order_value || 0}
              prefix={<BarChartOutlined />}
              precision={2}
              formatter={(value) => `$${value}`}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Orders Today"
              value={stats?.orders_today || 0}
              prefix={<CalendarOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Revenue Today"
              value={stats?.revenue_today || 0}
              prefix={<DollarOutlined style={{ color: '#52c41a' }} />}
              precision={2}
              formatter={(value) => `$${value}`}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={16} style={{ marginBottom: '24px' }}>
        <Col span={8}>
          <Card>
            <Statistic
              title="New Users (30 days)"
              value={stats?.users_last_30_days || 0}
              prefix={<UserOutlined />}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="Orders (30 days)"
              value={stats?.orders_last_30_days || 0}
              prefix={<ShoppingCartOutlined />}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="Revenue (30 days)"
              value={stats?.revenue_last_30_days || 0}
              prefix={<DollarOutlined />}
              precision={2}
              formatter={(value) => `$${value}`}
            />
          </Card>
        </Col>
      </Row>

      {/* Subscription Breakdown */}
      {stats?.subscription_breakdown && (
        <Row gutter={16} style={{ marginBottom: '24px' }}>
          <Col span={24}>
            <Card title="Subscription Breakdown">
              <Row gutter={16}>
                {Object.entries(stats.subscription_breakdown).map(([tier, count]) => (
                  <Col span={6} key={tier}>
                    <Statistic
                      title={tier.charAt(0).toUpperCase() + tier.slice(1)}
                      value={count}
                      prefix={<TrophyOutlined />}
                    />
                  </Col>
                ))}
              </Row>
            </Card>
          </Col>
        </Row>
      )}

      {/* Users Table */}
      <Card title="Users Management" style={{ marginBottom: '24px' }}>
        <Table
          dataSource={users}
          columns={userColumns}
          rowKey="id"
          pagination={{ pageSize: 10 }}
          scroll={{ x: true }}
        />
      </Card>

      {/* Businesses Table */}
      <Card title="Business Profiles">
        <Table
          dataSource={businesses}
          columns={businessColumns}
          rowKey="id"
          pagination={{ pageSize: 10 }}
          scroll={{ x: true }}
        />
      </Card>

      {/* User Details Modal */}
      <Drawer
        title={`User Details - ${selectedUser?.email}`}
        placement="right"
        size="large"
        onClose={() => setUserDetailsVisible(false)}
        open={userDetailsVisible}
        extra={
          <Space>
            <Tooltip title="Export menu items with pricing, costs, and order statistics">
              <Button 
                icon={<DownloadOutlined />} 
                onClick={() => selectedUser && exportUserData(selectedUser.id, 'menu_items')}
              >
                Menu Items CSV
              </Button>
            </Tooltip>
            <Tooltip title="Export order history with detailed transaction data">
              <Button 
                icon={<DownloadOutlined />} 
                onClick={() => selectedUser && exportUserData(selectedUser.id, 'orders')}
              >
                Orders CSV
              </Button>
            </Tooltip>
            <Tooltip title="Export comprehensive report with all user data and summary statistics">
              <Button 
                type="primary"
                icon={<DownloadOutlined />} 
                onClick={() => selectedUser && exportUserData(selectedUser.id, 'all')}
              >
                Complete Report CSV
              </Button>
            </Tooltip>
          </Space>
        }
      >
        {selectedUser && (
          <div>
            <Descriptions title="User Information" bordered column={2}>
              <Descriptions.Item label="Email">{selectedUser.email}</Descriptions.Item>
              <Descriptions.Item label="Name">{selectedUser.name || 'Not provided'}</Descriptions.Item>
              <Descriptions.Item label="Status">
                <Space>
                  {selectedUser.is_admin && <Tag color="gold">Admin</Tag>}
                  <Tag color={selectedUser.is_active ? 'green' : 'red'}>
                    {selectedUser.is_active ? 'Active' : 'Inactive'}
                  </Tag>
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="Subscription">
                {selectedUser.subscription_tier || 'Free'}
              </Descriptions.Item>
              <Descriptions.Item label="Business Name">
                {selectedUser.business_name || 'No business profile'}
              </Descriptions.Item>
              <Descriptions.Item label="Industry">
                {selectedUser.business_industry || 'Not specified'}
              </Descriptions.Item>
              <Descriptions.Item label="POS Connected">
                <Tag color={selectedUser.pos_connected ? 'green' : 'red'}>
                  {selectedUser.pos_connected ? 'Yes' : 'No'}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Member Since">
                {new Date(selectedUser.created_at).toLocaleDateString()}
              </Descriptions.Item>
            </Descriptions>

            <Divider />

            <Row gutter={16} style={{ marginBottom: '24px' }}>
              <Col span={6}>
                <Statistic
                  title="Total Orders"
                  value={selectedUser.total_orders}
                  prefix={<ShoppingCartOutlined />}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="Total Revenue"
                  value={selectedUser.total_revenue.toFixed(2)}
                  prefix={<DollarOutlined />}
                  precision={2}
                  formatter={(value) => `$${value}`}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="Menu Items"
                  value={selectedUser.total_items}
                  prefix={<MenuOutlined />}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="Avg Order Value"
                  value={selectedUser.avg_order_value.toFixed(2)}
                  prefix={<BarChartOutlined />}
                  precision={2}
                  formatter={(value) => `$${value}`}
                />
              </Col>
            </Row>

            <Tabs defaultActiveKey="menu">
              <TabPane tab="Menu Items" key="menu">
                <Table
                  dataSource={selectedUser.menu_items}
                  rowKey="id"
                  size="small"
                  columns={[
                    {
                      title: 'Name',
                      dataIndex: 'name',
                      key: 'name',
                    },
                    {
                      title: 'Category',
                      dataIndex: 'category',
                      key: 'category',
                    },
                    {
                      title: 'Price',
                      dataIndex: 'current_price',
                      key: 'current_price',
                      render: (price: number) => `$${price.toFixed(2)}`,
                    },
                    {
                      title: 'Cost',
                      dataIndex: 'cost',
                      key: 'cost',
                      render: (cost: number) => cost ? `$${cost.toFixed(2)}` : 'N/A',
                    },
                    {
                      title: 'Orders',
                      dataIndex: 'total_orders',
                      key: 'total_orders',
                    },
                    {
                      title: 'Revenue',
                      dataIndex: 'total_revenue',
                      key: 'total_revenue',
                      render: (revenue: number) => `$${revenue.toFixed(2)}`,
                    },
                  ]}
                  pagination={{ pageSize: 5 }}
                />
              </TabPane>
              <TabPane tab="Recent Orders" key="orders">
                <Table
                  dataSource={selectedUser.recent_orders}
                  rowKey="id"
                  size="small"
                  columns={[
                    {
                      title: 'Order ID',
                      dataIndex: 'id',
                      key: 'id',
                    },
                    {
                      title: 'Date',
                      dataIndex: 'order_date',
                      key: 'order_date',
                      render: (date: string) => new Date(date).toLocaleDateString(),
                    },
                    {
                      title: 'Amount',
                      dataIndex: 'total_amount',
                      key: 'total_amount',
                      render: (amount: number) => `$${amount.toFixed(2)}`,
                    },
                    {
                      title: 'Items',
                      dataIndex: 'items_count',
                      key: 'items_count',
                    },
                    {
                      title: 'Margin',
                      dataIndex: 'gross_margin',
                      key: 'gross_margin',
                      render: (margin: number) => margin ? `$${margin.toFixed(2)}` : 'N/A',
                    },
                    {
                      title: 'POS ID',
                      dataIndex: 'pos_id',
                      key: 'pos_id',
                      render: (posId: string) => posId || 'Manual',
                    },
                  ]}
                  pagination={{ pageSize: 5 }}
                />
              </TabPane>
            </Tabs>
          </div>
        )}
      </Drawer>
    </div>
  );
};

export default AdminDashboard;
