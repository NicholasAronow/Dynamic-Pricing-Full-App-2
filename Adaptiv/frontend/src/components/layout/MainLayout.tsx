import React from 'react';
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
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

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
    <Layout style={{ background: '#fff' }}>
      <Sider width={250} style={{ background: '#fff', borderRight: '1px solid #e8e8e8' }}>
        <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
          <div className="logo" style={{ color: '#9370DB' }}>
            Adaptiv
          </div>
          <Menu theme="light" mode="inline" selectedKeys={[location.pathname]} style={{ flex: '1 0 auto' }}>
          <Menu.Item key="/" icon={<DashboardOutlined />}>
            <Link to="/">Dashboard</Link>
          </Menu.Item>
          <Menu.Item key="/price-recommendations" icon={<AreaChartOutlined />}>
            <Link to="/price-recommendations">Price Recommendations</Link>
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
      <Layout className="site-layout" style={{ background: '#fff' }}>
        <Header className="site-layout-background" style={{ padding: 0, borderBottom: '1px solid #e8e8e8', height: '64px', display: 'flex', alignItems: 'center', background: '#fff' }}>
          <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', paddingRight: 24, width: '100%' }}>
            <Dropdown overlay={userMenu} placement="bottomRight">
              <Button type="text" style={{ marginRight: 8 }}>
                <Avatar icon={<UserOutlined />} /> 
                <span style={{ marginLeft: 8 }}>{user?.email || 'User'}</span>
              </Button>
            </Dropdown>
          </div>
        </Header>
        <Content
          className="site-layout-background"
          style={{
            margin: '0',
            padding: 24,
            minHeight: 280,
            borderLeft: 'none',
            boxShadow: 'none',
            background: '#fafafa'
          }}
        >
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
};

export default MainLayout;
