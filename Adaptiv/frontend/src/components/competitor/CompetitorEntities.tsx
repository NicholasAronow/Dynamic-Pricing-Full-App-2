import React, { useState, useEffect } from 'react';
import {
  Typography,
  Card,
  Button,
  Table,
  Tag,
  message,
  Spin,
  Empty,
  Modal,
  Form,
  Input,
  Switch,
  Space,
  Tooltip,
  Popconfirm,
  Statistic,
  Row,
  Col,
  Alert,
  Tabs
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  BarChartOutlined,
  LinkOutlined,
  SyncOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import competitorEntityService, {
  CompetitorEntity,
  CompetitorEntityCreate,
  CompetitorEntityUpdate,
  CompetitorStats,
  CompetitorScrapeRequest,
  CompetitorScrapeResponse
} from '../../services/competitorEntityService';
import moment from 'moment';
import { useAuth } from 'context/AuthContext';

const { Title, Text, Paragraph } = Typography;
const { TabPane } = Tabs;

const CompetitorEntities: React.FC = () => {
  const navigate = useNavigate();
  const [form] = Form.useForm();

  // State management
  const [competitors, setCompetitors] = useState<CompetitorEntity[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [modalVisible, setModalVisible] = useState<boolean>(false);
  const [editingCompetitor, setEditingCompetitor] = useState<CompetitorEntity | null>(null);
  const [statsModalVisible, setStatsModalVisible] = useState<boolean>(false);
  const [selectedCompetitorStats, setSelectedCompetitorStats] = useState<CompetitorStats | null>(null);
  const [statsLoading, setStatsLoading] = useState<boolean>(false);
  const [migrationLoading, setMigrationLoading] = useState<boolean>(false);
  const [scrapingLoading, setScrapingLoading] = useState<boolean>(false);
  const [scrapingModalVisible, setScrapingModalVisible] = useState<boolean>(false);
  const [scrapeForm] = Form.useForm();
  const { user } = useAuth(); // Add this line

  // Summary statistics
  const [summary, setSummary] = useState({
    total_competitors: 0,
    selected_competitors: 0,
    total_items: 0
  });

  // Load competitor entities
  const loadCompetitors = async () => {
    try {
      setLoading(true);
      const data = await competitorEntityService.getCompetitorEntities({
        include_items: false
      });
      
      // Ensure data is an array
      if (Array.isArray(data)) {
        setCompetitors(data);
        
        // Update summary
        const selectedCount = data.filter(c => c.is_selected).length;
        setSummary(prev => ({
          ...prev,
          total_competitors: data.length,
          selected_competitors: selectedCount
        }));
      } else {
        console.error('Unexpected response format:', data);
        setCompetitors([]);
      }
    } catch (error: any) {
      console.error('Error loading competitors:', error);
      // Check if it's a 404 or other specific error
      if (error.response?.status === 404) { 
        message.error('Competitors endpoint not found');
      } else {
        message.error('Failed to load competitors');
      }
      setCompetitors([]);
    } finally {
      setLoading(false);
    }
  };

  // Load summary statistics
  const loadSummary = async () => {
    try {
      const summaryData = await competitorEntityService.getCompetitorSummary();
      setSummary(summaryData);
    } catch (error) {
      console.error('Error loading summary:', error);
      // Set default values on error
      setSummary({
        total_competitors: 0,
        selected_competitors: 0,
        total_items: 0
      });
    }
  };

  useEffect(() => {
    loadCompetitors();
    loadSummary();
  }, []);

  // Handle create/update competitor
  const handleSaveCompetitor = async (values: CompetitorEntityCreate | CompetitorEntityUpdate) => {
    try {
      if (editingCompetitor) {
        await competitorEntityService.updateCompetitorEntity(editingCompetitor.id, values as CompetitorEntityUpdate);
        message.success('Competitor updated successfully');
      } else {
        await competitorEntityService.createCompetitorEntity(values as CompetitorEntityCreate);
        message.success('Competitor created successfully');
      }
      
      setModalVisible(false);
      setEditingCompetitor(null);
      form.resetFields();
      loadCompetitors();
      loadSummary();
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Failed to save competitor';
      message.error(errorMessage);
    }
  };

  // Handle delete competitor
  const handleDeleteCompetitor = async (competitorId: number) => {
    try {
      await competitorEntityService.deleteCompetitorEntity(competitorId);
      message.success('Competitor deleted successfully');
      loadCompetitors();
      loadSummary();
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Failed to delete competitor';
      message.error(errorMessage);
    }
  };

  // Handle toggle selection
  const handleToggleSelection = async (competitor: CompetitorEntity) => {
    try {
      await competitorEntityService.toggleCompetitorSelection(
        competitor.id,
        !competitor.is_selected
      );
      
      const action = !competitor.is_selected ? 'selected' : 'unselected';
      message.success(`Competitor ${action} for tracking`);
      loadCompetitors();
      loadSummary();
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Failed to update competitor selection';
      message.error(errorMessage);
    }
  };

  // Handle view stats
  const handleViewStats = async (competitor: CompetitorEntity) => {
    try {
      setStatsLoading(true);
      setStatsModalVisible(true);
      const stats = await competitorEntityService.getCompetitorStats(competitor.id);
      setSelectedCompetitorStats(stats);
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Failed to load competitor statistics';
      message.error(errorMessage);
      setStatsModalVisible(false);
    } finally {
      setStatsLoading(false);
    }
  };

  // Handle competitor scraping
  const handleScrapeCompetitor = async (values: CompetitorScrapeRequest) => {
    try {
      setScrapingLoading(true);
      
      // Add user_id to the request if needed
      const requestData = {
        ...values,
        user_id: user?.id // Add this if your backend expects it
      };
      
      const response = await competitorEntityService.scrapeCompetitor(requestData);
      
      console.log('Scrape response received:', response);
      
      if (response.success) {
        message.success(
          `Successfully scraped ${values.restaurant_name}! Found ${response.items_added} menu items.`
        );
        setScrapingModalVisible(false);
        scrapeForm.resetFields();
        
        // Force a complete refresh
        setCompetitors([]);
        
        // Wait a bit then reload
        setTimeout(async () => {
          await loadCompetitors();
          await loadSummary();
        }, 500);
      } else {
        message.error(response.error || 'Failed to scrape competitor data');
      }
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Failed to scrape competitor';
      message.error(errorMessage);
    } finally {
      setScrapingLoading(false);
    }
  };

  // Open modal for scraping new competitor
  const handleCreateCompetitor = () => {
    scrapeForm.resetFields();
    setScrapingModalVisible(true);
  };

  // Open modal for manually creating competitor (legacy)
  const handleManualCreateCompetitor = () => {
    setEditingCompetitor(null);
    form.resetFields();
    setModalVisible(true);
  };

  // Open modal for editing competitor
  const handleEditCompetitor = (competitor: CompetitorEntity) => {
    setEditingCompetitor(competitor);
    form.setFieldsValue({
      name: competitor.name,
      address: competitor.address,
      category: competitor.category,
      website: competitor.website,
      menu_url: competitor.menu_url,
      is_selected: competitor.is_selected
    });
    setModalVisible(true);
  };

  // Table columns
  const columns = [
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: CompetitorEntity) => (
        <Space>
          <Text strong>{text}</Text>
          {record.is_selected && (
            <Tag color="green" icon={<CheckCircleOutlined />}>
            </Tag>
          )}
        </Space>
      ),
    },
    {
      title: 'Website',
      dataIndex: 'website',
      key: 'website',
      render: (website: string) => website ? (
        <a href={website} target="_blank" rel="noopener noreferrer">
          <LinkOutlined /> {website}
        </a>
      ) : (
        <Text type="secondary">Not provided</Text>
      ),
    },
    {
      title: 'Location',
      dataIndex: 'address',
      key: 'address',
      render: (address: string) => address || (
        <Text type="secondary">No address</Text>
      ),
    },
    {
      title: 'Category',
      dataIndex: 'category',
      key: 'category',
      render: (category: string) => category || (
        <Text type="secondary">No category</Text>
      ),
    },
    {
      title: 'Created',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => moment(date).format('MMM DD, YYYY'),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_: any, record: CompetitorEntity) => (
        <Space>
          <Tooltip title="View Statistics">
            <Button
              type="text"
              icon={<BarChartOutlined />}
              onClick={() => handleViewStats(record)}
            />
          </Tooltip>
          
          <Tooltip title="View Items">
            <Button
              type="text"
              icon={<EyeOutlined />}
              onClick={() => navigate(`/competitor/${record.id}`)}
            />
          </Tooltip>
          
          <Tooltip title={record.is_selected ? "Stop Tracking" : "Start Tracking"}>
            <Button
              type="text"
              icon={record.is_selected ? <CloseCircleOutlined /> : <CheckCircleOutlined />}
              onClick={() => handleToggleSelection(record)}
            />
          </Tooltip>
          
          <Tooltip title="Edit">
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => handleEditCompetitor(record)}
            />
          </Tooltip>
          
          <Popconfirm
            title="Are you sure you want to delete this competitor?"
            description="This will also delete all associated competitor items."
            onConfirm={() => handleDeleteCompetitor(record.id)}
            okText="Yes"
            cancelText="No"
          >
            <Tooltip title="Delete">
              <Button
                type="text"
                danger
                icon={<DeleteOutlined />}
              />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ 
      padding: '0px 0px',
      background: '#fafbfc',
      minHeight: '100vh'
    }}>
      <div style={{ 
        maxWidth: '100vw', 
        margin: '0 auto' 
      }}>
        {/* Header Section */}
        <div style={{ 
          marginBottom: '48px',
          animation: 'fadeIn 0.5s ease-out'
        }}>
          <Title level={2} style={{
            fontSize: '32px',
            fontWeight: '600',
            color: '#0a0a0a',
            marginBottom: '8px',
            letterSpacing: '-0.02em'
          }}>
            Competitor Management
          </Title>
          <Paragraph style={{
            fontSize: '16px',
            color: '#666',
            margin: 0,
            fontWeight: '400'
          }}>
            Manage your competitor entities and track their pricing data.
          </Paragraph>
        </div>

        {/* Summary Statistics */}
        <Row gutter={24} style={{ marginBottom: '32px' }}>
          <Col span={8}>
            <Card style={{
              border: 'none',
              borderRadius: '12px',
              boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
              transition: 'all 0.3s ease',
              cursor: 'pointer',
              background: '#fff',
              height: '100%'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = 'translateY(-2px)';
              e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.08)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'translateY(0)';
              e.currentTarget.style.boxShadow = '0 1px 3px rgba(0,0,0,0.04)';
            }}>
              <Statistic
                title={<span style={{ 
                  color: '#8e8e93', 
                  fontSize: '13px',
                  fontWeight: '500',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em'
                }}>Total Competitors</span>}
                value={summary.total_competitors}
                prefix={<BarChartOutlined style={{ 
                  fontSize: '20px',
                  color: '#007AFF'
                }} />}
                valueStyle={{
                  fontSize: '36px',
                  fontWeight: '600',
                  color: '#0a0a0a',
                  letterSpacing: '-0.02em'
                }}
              />
            </Card>
          </Col>
          <Col span={8}>
            <Card style={{
              border: 'none',
              borderRadius: '12px',
              boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
              transition: 'all 0.3s ease',
              cursor: 'pointer',
              background: '#fff',
              height: '100%'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = 'translateY(-2px)';
              e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.08)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'translateY(0)';
              e.currentTarget.style.boxShadow = '0 1px 3px rgba(0,0,0,0.04)';
            }}>
              <Statistic
                title={<span style={{ 
                  color: '#8e8e93', 
                  fontSize: '13px',
                  fontWeight: '500',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em'
                }}>Tracking</span>}
                value={summary.selected_competitors}
                prefix={<CheckCircleOutlined style={{ 
                  fontSize: '20px',
                  color: '#34C759'
                }} />}
                valueStyle={{ 
                  fontSize: '36px',
                  fontWeight: '600',
                  color: '#34C759',
                  letterSpacing: '-0.02em'
                }}
              />
            </Card>
          </Col>
          <Col span={8}>
            <Card style={{
              border: 'none',
              borderRadius: '12px',
              boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
              transition: 'all 0.3s ease',
              cursor: 'pointer',
              background: '#fff',
              height: '100%'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = 'translateY(-2px)';
              e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.08)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'translateY(0)';
              e.currentTarget.style.boxShadow = '0 1px 3px rgba(0,0,0,0.04)';
            }}>
              <Statistic
                title={<span style={{ 
                  color: '#8e8e93', 
                  fontSize: '13px',
                  fontWeight: '500',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em'
                }}>Total Items</span>}
                value={summary.total_items}
                prefix={<EyeOutlined style={{ 
                  fontSize: '20px',
                  color: '#5856D6'
                }} />}
                valueStyle={{
                  fontSize: '36px',
                  fontWeight: '600',
                  color: '#0a0a0a',
                  letterSpacing: '-0.02em'
                }}
              />
            </Card>
          </Col>
        </Row>

        {/* Action Bar */}
        <Card style={{ 
          marginBottom: '32px',
          border: 'none',
          borderRadius: '12px',
          boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
          background: '#fff',
          padding: '20px 24px'
        }}>
          <Space size={16}>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={handleCreateCompetitor}
              loading={scrapingLoading}
              style={{
                background: '#007AFF',
                border: 'none',
                height: '40px',
                padding: '0 24px',
                borderRadius: '8px',
                fontSize: '15px',
                fontWeight: '500',
                boxShadow: '0 2px 8px rgba(0,122,255,0.2)',
                transition: 'all 0.3s ease'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = '#0051D5';
                e.currentTarget.style.transform = 'translateY(-1px)';
                e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,122,255,0.3)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = '#007AFF';
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,122,255,0.2)';
              }}
            >
              Scrape Competitor
            </Button>
            
            <Button
              icon={<PlusOutlined />}
              onClick={handleManualCreateCompetitor}
              style={{
                background: '#fff',
                border: '1px solid #e5e5e7',
                height: '40px',
                padding: '0 24px',
                borderRadius: '8px',
                fontSize: '15px',
                fontWeight: '500',
                color: '#0a0a0a',
                transition: 'all 0.3s ease'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = '#007AFF';
                e.currentTarget.style.color = '#007AFF';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = '#e5e5e7';
                e.currentTarget.style.color = '#0a0a0a';
              }}
            >
              Manual Entry
            </Button>
            
            <Button
              icon={<SyncOutlined />}
              onClick={loadCompetitors}
              loading={loading}
              style={{
                background: '#fff',
                border: '1px solid #e5e5e7',
                height: '40px',
                padding: '0 20px',
                borderRadius: '8px',
                fontSize: '15px',
                fontWeight: '500',
                color: '#0a0a0a',
                transition: 'all 0.3s ease'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = '#007AFF';
                e.currentTarget.style.color = '#007AFF';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = '#e5e5e7';
                e.currentTarget.style.color = '#0a0a0a';
              }}
            >
              Refresh
            </Button>
          </Space>
        </Card>

        {/* Competitors Table */}
        <Card style={{
          border: 'none',
          borderRadius: '12px',
          boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
          background: '#fff',
          overflow: 'hidden'
        }}>
          <Table
            columns={columns}
            dataSource={competitors}
            rowKey="id"
            loading={loading}
            style={{
              fontSize: '12px',
              background: '#fff',
              borderBottom: '1px solid #e5e5e7',
              color: '#8e8e93',
              fontWeight: '300',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              padding: '16px',
            }}
            locale={{
              emptyText: (
                <Empty
                  description={
                    <span style={{ color: '#8e8e93', fontSize: '15px' }}>
                      No competitors found
                    </span>
                  }
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                  style={{ padding: '60px 0' }}
                />
              ),
            }}
          />
        </Card>

        {/* Create/Edit Modal */}
        <Modal
          title={
            <span style={{
              fontSize: '20px',
              fontWeight: '600',
              color: '#0a0a0a'
            }}>
              {editingCompetitor ? 'Edit Competitor' : 'Add New Competitor'}
            </span>
          }
          open={modalVisible}
          onCancel={() => {
            setModalVisible(false);
            setEditingCompetitor(null);
            form.resetFields();
          }}
          footer={null}
          style={{
            top: 80
          }}
          bodyStyle={{
            padding: '32px'
          }}
        >
          <Form
            form={form}
            layout="vertical"
            onFinish={handleSaveCompetitor}
            style={{
              fontSize: '14px',
              fontWeight: '200',
              color: '#0a0a0a'
            }}
          >
            <Form.Item
              name="name"
              label="Competitor Name"
              rules={[
                { required: true, message: 'Please enter competitor name' },
                { min: 2, message: 'Name must be at least 2 characters' }
              ]}
              style={{ marginBottom: '24px' }}
            >
              <Input 
                placeholder="Enter competitor name" 
                style={{
                  height: '40px',
                  borderRadius: '8px',
                  fontSize: '15px',
                  border: '1px solid #e5e5e7',
                  transition: 'all 0.3s ease'
                }}
              />
            </Form.Item>

            <Form.Item
              name="website"
              label="Website"
              rules={[
                { type: 'url', message: 'Please enter a valid URL' }
              ]}
              style={{ marginBottom: '24px' }}
            >
              <Input 
                placeholder="https://competitor-website.com" 
                style={{
                  height: '40px',
                  borderRadius: '8px',
                  fontSize: '15px',
                  border: '1px solid #e5e5e7',
                  transition: 'all 0.3s ease'
                }}
              />
            </Form.Item>

            <Form.Item
              name="address"
              label="Location"
              style={{ marginBottom: '24px' }}
            >
              <Input 
                placeholder="Enter competitor address" 
                style={{
                  height: '40px',
                  borderRadius: '8px',
                  fontSize: '15px',
                  border: '1px solid #e5e5e7',
                  transition: 'all 0.3s ease'
                }}
              />
            </Form.Item>

            <Form.Item
              name="category"
              label="Category"
              style={{ marginBottom: '24px' }}
            >
              <Input 
                placeholder="e.g., restaurant, cafe, fast food" 
                style={{
                  height: '40px',
                  borderRadius: '8px',
                  fontSize: '15px',
                  border: '1px solid #e5e5e7',
                  transition: 'all 0.3s ease'
                }}
              />
            </Form.Item>

            <Form.Item
              name="menu_url"
              label="Menu URL"
              rules={[
                { type: 'url', message: 'Please enter a valid URL' }
              ]}
              style={{ marginBottom: '24px' }}
            >
              <Input 
                placeholder="https://competitor-menu-url.com" 
                style={{
                  height: '40px',
                  borderRadius: '8px',
                  fontSize: '15px',
                  border: '1px solid #e5e5e7',
                  transition: 'all 0.3s ease'
                }}
              />
            </Form.Item>

            <Form.Item
              name="is_selected"
              label="Track this competitor"
              valuePropName="checked"
              style={{ marginBottom: '32px' }}
            >
              <Switch 
                style={{
                  background: '#e5e5e7'
                }}
              />
            </Form.Item>

            <Form.Item style={{ marginBottom: 0 }}>
              <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
                <Button
                  onClick={() => {
                    setModalVisible(false);
                    setEditingCompetitor(null);
                    form.resetFields();
                  }}
                  style={{
                    height: '40px',
                    padding: '0 24px',
                    borderRadius: '8px',
                    fontSize: '15px',
                    fontWeight: '500',
                    border: '1px solid #e5e5e7',
                    background: '#fff',
                    color: '#0a0a0a'
                  }}
                >
                  Cancel
                </Button>
                <Button 
                  type="primary" 
                  htmlType="submit"
                  style={{
                    height: '40px',
                    padding: '0 24px',
                    borderRadius: '8px',
                    fontSize: '15px',
                    fontWeight: '500',
                    background: '#007AFF',
                    border: 'none',
                    boxShadow: '0 2px 8px rgba(0,122,255,0.2)'
                  }}
                >
                  {editingCompetitor ? 'Update' : 'Create'}
                </Button>
              </Space>
            </Form.Item>
          </Form>
        </Modal>

        {/* Statistics Modal */}
        <Modal
          title={
            <span style={{
              fontSize: '20px',
              fontWeight: '600',
              color: '#0a0a0a'
            }}>
              Competitor Statistics
            </span>
          }
          open={statsModalVisible}
          onCancel={() => {
            setStatsModalVisible(false);
            setSelectedCompetitorStats(null);
          }}
          footer={[
            <Button 
              key="close" 
              onClick={() => setStatsModalVisible(false)}
              style={{
                height: '40px',
                padding: '0 24px',
                borderRadius: '8px',
                fontSize: '15px',
                fontWeight: '500',
                border: '1px solid #e5e5e7',
                background: '#fff',
                color: '#0a0a0a'
              }}
            >
              Close
            </Button>
          ]}
          width={800}
          style={{ top: 80 }}
          bodyStyle={{ padding: '32px' }}
        >
          {statsLoading ? (
            <div style={{ textAlign: 'center', padding: '60px' }}>
              <Spin size="large" />
            </div>
          ) : selectedCompetitorStats ? (
            <div>
              <Title level={4} style={{
                fontSize: '24px',
                fontWeight: '600',
                color: '#0a0a0a',
                marginBottom: '32px'
              }}>
                {selectedCompetitorStats.competitor_name}
              </Title>
              
              <Row gutter={24} style={{ marginBottom: '40px' }}>
                <Col span={8}>
                  <div style={{
                    background: '#fafbfc',
                    padding: '24px',
                    borderRadius: '12px',
                    textAlign: 'center'
                  }}>
                    <Statistic
                      title={<span style={{ 
                        color: '#8e8e93', 
                        fontSize: '13px',
                        fontWeight: '500',
                        textTransform: 'uppercase',
                        letterSpacing: '0.05em'
                      }}>Total Items</span>}
                      value={selectedCompetitorStats.total_items}
                      valueStyle={{
                        fontSize: '32px',
                        fontWeight: '600',
                        color: '#0a0a0a'
                      }}
                    />
                  </div>
                </Col>
                <Col span={8}>
                  <div style={{
                    background: '#fafbfc',
                    padding: '24px',
                    borderRadius: '12px',
                    textAlign: 'center'
                  }}>
                    <Statistic
                      title={<span style={{ 
                        color: '#8e8e93', 
                        fontSize: '13px',
                        fontWeight: '500',
                        textTransform: 'uppercase',
                        letterSpacing: '0.05em'
                      }}>Average Price</span>}
                      value={selectedCompetitorStats.price_stats.avg_price}
                      precision={2}
                      prefix="$"
                      valueStyle={{
                        fontSize: '32px',
                        fontWeight: '600',
                        color: '#0a0a0a'
                      }}
                    />
                  </div>
                </Col>
                <Col span={8}>
                  <div style={{
                    background: '#fafbfc',
                    padding: '24px',
                    borderRadius: '12px',
                    textAlign: 'center'
                  }}>
                    <Statistic
                      title={<span style={{ 
                        color: '#8e8e93', 
                        fontSize: '13px',
                        fontWeight: '500',
                        textTransform: 'uppercase',
                        letterSpacing: '0.05em'
                      }}>Price Range</span>}
                      value={`$${selectedCompetitorStats.price_stats.min_price.toFixed(2)} - $${selectedCompetitorStats.price_stats.max_price.toFixed(2)}`}
                      valueStyle={{
                        fontSize: '20px',
                        fontWeight: '600',
                        color: '#0a0a0a'
                      }}
                    />
                  </div>
                </Col>
              </Row>

              <Title level={5} style={{
                fontSize: '16px',
                fontWeight: '600',
                color: '#0a0a0a',
                marginBottom: '16px',
                textTransform: 'uppercase',
                letterSpacing: '0.05em'
              }}>
                Category Breakdown
              </Title>
              <Table
                dataSource={selectedCompetitorStats.category_breakdown}
                columns={[
                  {
                    title: 'Category',
                    dataIndex: 'category',
                    key: 'category',
                  },
                  {
                    title: 'Items',
                    dataIndex: 'item_count',
                    key: 'item_count',
                  },
                  {
                    title: 'Avg Price',
                    dataIndex: 'avg_price',
                    key: 'avg_price',
                    render: (price: number) => `$${price.toFixed(2)}`,
                  },
                ]}
                pagination={false}
                size="small"
                style={{
                    background: '#fafbfc',
                    borderBottom: '1px solid #e5e5e7',
                    color: '#8e8e93',
                    fontWeight: '600',
                    fontSize: '12px',
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em'
                }}
              />
            </div>
          ) : null}
        </Modal>

        {/* Competitor Scraping Modal */}
        <Modal
          title={
            <span style={{
              fontSize: '20px',
              fontWeight: '600',
              color: '#0a0a0a'
            }}>
              Scrape Competitor Menu
            </span>
          }
          open={scrapingModalVisible}
          onCancel={() => {
            setScrapingModalVisible(false);
            scrapeForm.resetFields();
          }}
          footer={null}
          width={600}
          style={{ top: 80 }}
          bodyStyle={{ padding: '32px' }}
        >
          <Alert
            message={
              <span style={{ fontWeight: '600', fontSize: '15px' }}>
                AI-Powered Menu Scraping
              </span>
            }
            description={
              <span style={{ fontSize: '14px', lineHeight: '1.6' }}>
                Enter a restaurant name and location. Our AI will automatically find their website, scrape their menu, and add it to your competitor database.
              </span>
            }
            type="info"
            showIcon
            style={{ 
              marginBottom: '32px',
              borderRadius: '8px',
              border: '1px solid #b3d7ff',
              background: '#f0f8ff'
            }}
          />
          
          <Form
            form={scrapeForm}
            layout="vertical"
            onFinish={handleScrapeCompetitor}
            style={{
              fontSize: '14px',
              fontWeight: '500',
              color: '#0a0a0a'
            }}
          >
            <Form.Item
              name="restaurant_name"
              label="Restaurant Name"
              rules={[
                { required: true, message: 'Please enter restaurant name' },
                { min: 2, message: 'Name must be at least 2 characters' }
              ]}
              style={{ marginBottom: '24px' }}
            >
              <Input 
                placeholder="e.g., McDonald's, Starbucks, Local Bistro"
                disabled={scrapingLoading}
                style={{
                  height: '40px',
                  borderRadius: '8px',
                  fontSize: '15px',
                  border: '1px solid #e5e5e7',
                  transition: 'all 0.3s ease'
                }}
              />
            </Form.Item>

            <Form.Item
              name="location"
              label="Location (Optional)"
              extra={
                <span style={{ fontSize: '13px', color: '#8e8e93' }}>
                  Helps find the correct restaurant if there are multiple locations
                </span>
              }
              style={{ marginBottom: '32px' }}
            >
              <Input 
                placeholder="e.g., New York, NY or 123 Main St, Boston"
                disabled={scrapingLoading}
                style={{
                  height: '40px',
                  borderRadius: '8px',
                  fontSize: '15px',
                  border: '1px solid #e5e5e7',
                  transition: 'all 0.3s ease'
                }}
              />
            </Form.Item>

            <Form.Item style={{ marginBottom: 0 }}>
              <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
                <Button
                  onClick={() => {
                    setScrapingModalVisible(false);
                    scrapeForm.resetFields();
                  }}
                  disabled={scrapingLoading}
                  style={{
                    height: '40px',
                    padding: '0 24px',
                    borderRadius: '8px',
                    fontSize: '15px',
                    fontWeight: '500',
                    border: '1px solid #e5e5e7',
                    background: '#fff',
                    color: '#0a0a0a'
                  }}
                >
                  Cancel
                </Button>
                <Button 
                  type="primary" 
                  htmlType="submit"
                  loading={scrapingLoading}
                  icon={<SyncOutlined />}
                  style={{
                    height: '40px',
                    padding: '0 24px',
                    borderRadius: '8px',
                    fontSize: '15px',
                    fontWeight: '500',
                    background: '#007AFF',
                    border: 'none',
                    boxShadow: '0 2px 8px rgba(0,122,255,0.2)'
                  }}
                >
                  {scrapingLoading ? 'Scraping...' : 'Start Scraping'}
                </Button>
              </Space>
            </Form.Item>
          </Form>
        </Modal>
      </div>
    </div>
  );
};

export default CompetitorEntities;
