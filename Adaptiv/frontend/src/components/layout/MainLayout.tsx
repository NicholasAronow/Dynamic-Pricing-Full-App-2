import React, { useState } from 'react';
import { Layout, Menu, Avatar, Dropdown, Button } from 'antd';
import { 
  MenuUnfoldOutlined, 
  MenuFoldOutlined,
  DashboardOutlined,
  UserOutlined,
  LogoutOutlined,
  AreaChartOutlined,
  ShoppingOutlined,
  TeamOutlined
} from '@ant-design/icons';
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

const { Header, Sider, Content } = Layout;

const MainLayout: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  const toggle = () => {
    setCollapsed(!collapsed);
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const userMenu = (
    <Menu>
      <Menu.Item key="profile" icon={<UserOutlined />}>
        <Link to="/profile">Profile</Link>
      </Menu.Item>
      <Menu.Divider />
      <Menu.Item key="logout" icon={<LogoutOutlined />} onClick={handleLogout}>
        Logout
      </Menu.Item>
    </Menu>
  );

  return (
    <Layout>
      <Sider trigger={null} collapsible collapsed={collapsed} breakpoint="lg" 
        collapsedWidth="80" width={250}>
        <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
          <div className="logo">
            {!collapsed ? 'Adaptiv' : 'A'}
          </div>
          <Menu theme="dark" mode="inline" selectedKeys={[location.pathname]} style={{ flex: '1 0 auto' }}>
          <Menu.Item key="/" icon={<DashboardOutlined />}>
            <Link to="/">Dashboard</Link>
          </Menu.Item>
          <Menu.Item key="/price-recommendations" icon={<AreaChartOutlined />}>
            <Link to="/price-recommendations">Price Recommendations</Link>
          </Menu.Item>
          <Menu.Item key="/sales-overview" icon={<ShoppingOutlined />}>
            <Link to="/sales-overview">Sales Overview</Link>
          </Menu.Item>
          <Menu.Item key="/competitor-analysis" icon={<TeamOutlined />}>
            <Link to="/competitor-analysis">Competitor Analysis</Link>
          </Menu.Item>
          <Menu.Item key="/profile" icon={<UserOutlined />}>
            <Link to="/profile">Business Profile</Link>
          </Menu.Item>
        </Menu>
        </div>
      </Sider>
      <Layout className="site-layout">
        <Header className="site-layout-background" style={{ padding: 0 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingRight: 24 }}>
            {React.createElement(collapsed ? MenuUnfoldOutlined : MenuFoldOutlined, {
              className: 'trigger',
              onClick: toggle,
              style: { fontSize: '18px', padding: '0 24px', cursor: 'pointer' }
            })}
            <Dropdown overlay={userMenu} placement="bottomRight">
              <Button type="text" style={{ marginRight: 8 }}>
                <Avatar icon={<UserOutlined />} /> 
                {!collapsed && <span style={{ marginLeft: 8 }}>{user?.email || 'User'}</span>}
              </Button>
            </Dropdown>
          </div>
        </Header>
        <Content
          className="site-layout-background"
          style={{
            margin: '24px 16px',
            padding: 24,
            minHeight: 280,
          }}
        >
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
};

export default MainLayout;
