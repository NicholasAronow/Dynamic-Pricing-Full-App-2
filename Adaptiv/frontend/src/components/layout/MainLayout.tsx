import React from 'react';
import { Layout, Menu, Avatar, Dropdown, Button, Typography } from 'antd';
import adaptivLogo from '../../assets/adaptiv_logo.png';
import { 
  MenuUnfoldOutlined, 
  MenuFoldOutlined,
  HomeOutlined,
  UserOutlined,
  LogoutOutlined,
  BookOutlined,
  ShopOutlined,
  GlobalOutlined,
  RocketOutlined,
  SettingOutlined,
  CalculatorOutlined,
  PieChartOutlined,
  CrownOutlined,
  BankOutlined,
  FileTextOutlined,
  CoffeeOutlined,
  ReadOutlined,
  QuestionCircleOutlined,
  MenuOutlined,
  DollarOutlined
} from '@ant-design/icons';
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useSubscription } from '../../contexts/SubscriptionContext';

const { Header, Sider, Content } = Layout;

const { Text } = Typography;

const MainLayout: React.FC = () => {
  const { user, logout } = useAuth();
  const { currentPlan, isSubscribed } = useSubscription();
  const location = useLocation();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const userMenu = (
    <Menu>
      <Menu.Item key="profile" icon={<UserOutlined style={{ fontSize: '16px', color: '#7546C9' }} />}>
        <Link to="/profile">Profile</Link>
      </Menu.Item>
      <Menu.Item key="support" icon={<QuestionCircleOutlined style={{ fontSize: '16px', color: '#7546C9' }} />}>
        <Link to="/support">Support</Link>
      </Menu.Item>
      <Menu.Divider />
      <Menu.Item key="logout" icon={<LogoutOutlined style={{ fontSize: '16px', color: '#7546C9' }} />} onClick={handleLogout}>
        Logout
      </Menu.Item>
    </Menu>
  );

  return (
    <Layout style={{ background: '#fff' }}>
      <Sider 
        width={260} 
        style={{ 
          background: '#fff', 
          borderRight: '1px solid #f1f3f4',
          boxShadow: '0 0 0 1px rgba(0,0,0,0.02)',
          overflow: 'hidden',
          position: 'fixed',
          height: '100vh',
          left: 0,
          top: 0,
          bottom: 0
        }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
          {/* Logo Section */}
          <div style={{ 
            padding: '24px 20px', 
            borderBottom: '0px solid #f1f3f4',
            background: 'white'
          }}>
            <div style={{ 
              display: 'flex', 
              alignItems: 'center',
              gap: '12px'
            }}>
              <div style={{
                width: '32px',
                height: '32px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <img 
                  src={adaptivLogo} 
                  alt="Adaptiv Logo" 
                  style={{ 
                    width: '100%', 
                    height: '100%', 
                    objectFit: 'contain' 
                  }} 
                />
              </div>
              <span style={{ 
                fontFamily: '"Inter", -apple-system, sans-serif', 
                fontSize: '20px', 
                fontWeight: 600, 
                color: '#1f2937',
                letterSpacing: '-0.3px'
              }}>
                Adaptiv
              </span>
            </div>
          </div>

          {/* Navigation Menu */}
          <div style={{ flex: '1 0 auto', padding: '16px 0', overflow: 'hidden' }}>
            <Menu 
              theme="light" 
              mode="inline" 
              selectedKeys={[location.pathname]}
              style={{ 
                background: 'transparent',
                border: 'none',
                fontSize: '14px'
              }}
              items={[
                {
                  key: '/',
                  icon: (
                    <div style={{
                      width: '20px',
                      height: '20px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center'
                    }}>
                      <HomeOutlined style={{ 
                        fontSize: '16px', 
                        color: location.pathname === '/' ? '#667eea' : '#6b7280'
                      }} />
                    </div>
                  ),
                  label: (
                    <Link 
                      to="/" 
                      style={{ 
                        color: location.pathname === '/' ? '#1f2937' : '#6b7280',
                        fontWeight: location.pathname === '/' ? 500 : 400,
                        textDecoration: 'none'
                      }}
                    >
                      Dashboard
                    </Link>
                  ),
                  style: {
                    height: '44px',
                    margin: '2px 9px',
                    borderRadius: '0px',
                    padding: '0 12px',
                    background: location.pathname === '/' ? '#f0f4ff' : 'transparent',
                    border: 'none'
                  }
                },
                {
                  key: '/price-recommendations',
                  icon: (
                    <div style={{
                      width: '20px',
                      height: '20px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center'
                    }}>
                      <MenuOutlined style={{ 
                        fontSize: '16px', 
                        color: location.pathname === '/price-recommendations' ? '#667eea' : '#6b7280'
                      }} />
                    </div>
                  ),
                  label: (
                    <Link 
                      to="/price-recommendations" 
                      style={{ 
                        color: location.pathname === '/price-recommendations' ? '#1f2937' : '#6b7280',
                        fontWeight: location.pathname === '/price-recommendations' ? 500 : 400,
                        textDecoration: 'none'
                      }}
                    >
                      Menu & Pricing
                    </Link>
                  ),
                  style: {
                    height: '44px',
                    margin: '2px 9px',
                    borderRadius: '0px',
                    padding: '0 12px',
                    background: location.pathname === '/price-recommendations' ? '#f0f4ff' : 'transparent',
                    border: 'none'
                  }
                },
                {
                  key: '/costs',
                  icon: (
                    <div style={{
                      width: '20px',
                      height: '20px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center'
                    }}>
                      <DollarOutlined style={{ 
                        fontSize: '16px', 
                        color: location.pathname === '/costs' ? '#667eea' : '#6b7280'
                      }} />
                    </div>
                  ),
                  label: (
                    <Link 
                      to="/costs" 
                      style={{ 
                        color: location.pathname === '/costs' ? '#1f2937' : '#6b7280',
                        fontWeight: location.pathname === '/costs' ? 500 : 400,
                        textDecoration: 'none'
                      }}
                    >
                      Cost Management
                    </Link>
                  ),
                  style: {
                    height: '44px',
                    margin: '2px 9px',
                    borderRadius: '0px',
                    padding: '0 12px',
                    background: location.pathname === '/costs' ? '#f0f4ff' : 'transparent',
                    border: 'none'
                  }
                },
                {
                  key: '/competitors',
                  icon: (
                    <div style={{
                      width: '20px',
                      height: '20px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center'
                    }}>
                      <GlobalOutlined style={{ 
                        fontSize: '16px', 
                        color: location.pathname === '/competitors' ? '#667eea' : '#6b7280'
                      }} />
                    </div>
                  ),
                  label: (
                    <Link 
                      to="/competitors" 
                      style={{ 
                        color: location.pathname === '/competitors' ? '#1f2937' : '#6b7280',
                        fontWeight: location.pathname === '/competitors' ? 500 : 400,
                        textDecoration: 'none'
                      }}
                    >
                      Competitors
                    </Link>
                  ),
                  style: {
                    height: '44px',
                    margin: '2px 9px',
                    borderRadius: '0px',
                    padding: '0 12px',
                    background: location.pathname === '/competitors' ? '#f0f4ff' : 'transparent',
                    border: 'none'
                  }
                },
                {
                  key: '/agents',
                  icon: (
                    <div style={{
                      width: '20px',
                      height: '20px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center'
                    }}>
                      <RocketOutlined style={{ 
                        fontSize: '16px', 
                        color: location.pathname === '/agents' ? '#667eea' : '#6b7280'
                      }} />
                    </div>
                  ),
                  label: (
                    <Link 
                      to="/agents" 
                      style={{ 
                        color: location.pathname === '/agents' ? '#1f2937' : '#6b7280',
                        fontWeight: location.pathname === '/agents' ? 500 : 400,
                        textDecoration: 'none'
                      }}
                    >
                      Price Optimization
                    </Link>
                  ),
                  style: {
                    height: '44px',
                    margin: '2px 9px',
                    borderRadius: '0px',
                    padding: '0 12px',
                    background: location.pathname === '/agents' ? '#f0f4ff' : 'transparent',
                    border: 'none'
                  }
                },
                {
                  key: '/profile',
                  icon: (
                    <div style={{
                      width: '20px',
                      height: '20px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center'
                    }}>
                      <BankOutlined style={{ 
                        fontSize: '16px', 
                        color: location.pathname === '/profile' ? '#667eea' : '#6b7280'
                      }} />
                    </div>
                  ),
                  label: (
                    <Link 
                      to="/profile" 
                      style={{ 
                        color: location.pathname === '/profile' ? '#1f2937' : '#6b7280',
                        fontWeight: location.pathname === '/profile' ? 500 : 400,
                        textDecoration: 'none'
                      }}
                    >
                      Business Profile
                    </Link>
                  ),
                  style: {
                    height: '44px',
                    margin: '2px 9px',
                    borderRadius: '0px',
                    padding: '0 12px',
                    background: location.pathname === '/profile' ? '#f0f4ff' : 'transparent',
                    border: 'none'
                  }
                },
                {
                  key: '/subscription-plans',
                  icon: (
                    <div style={{
                      width: '20px',
                      height: '20px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center'
                    }}>
                      <CrownOutlined style={{ 
                        fontSize: '16px', 
                        color: location.pathname === '/subscription-plans' ? '#667eea' : '#6b7280'
                      }} />
                    </div>
                  ),
                  label: (
                    <Link 
                      to="/subscription-plans" 
                      style={{ 
                        color: location.pathname === '/subscription-plans' ? '#1f2937' : '#6b7280',
                        fontWeight: location.pathname === '/subscription-plans' ? 500 : 400,
                        textDecoration: 'none'
                      }}
                    >
                      Subscription
                    </Link>
                  ),
                  style: {
                    height: '44px',
                    margin: '2px 9px',
                    borderRadius: '0px',
                    padding: '0 12px',
                    background: location.pathname === '/subscription-plans' ? '#f0f4ff' : 'transparent',
                    border: 'none'
                  }
                }
              ]}
            />
          </div>

          {/* Footer Section */}
          <div style={{ 
            padding: '16px 20px',
            borderTop: '1px solid #f1f3f4',
            background: 'white'
          }}>
            <div style={{
              padding: '12px',
              background: '#f8fafc',
              borderRadius: '8px',
              border: '1px solid #e5e7eb'
            }}>
              <Text style={{ 
                fontSize: '12px', 
                color: '#6b7280',
                display: 'block',
                textAlign: 'center'
              }}>
                Need help?{' '}
                <a 
                  href="/support" 
                  style={{ 
                    color: '#667eea', 
                    textDecoration: 'none',
                    fontWeight: 500
                  }}
                >
                  Contact Support
                </a>
              </Text>
            </div>
          </div>
        </div>
      </Sider>
      <Layout className="site-layout" style={{ background: '#fff', marginLeft: '260px' }}>
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
