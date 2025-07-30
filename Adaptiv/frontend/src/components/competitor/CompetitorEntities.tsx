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

  // Handle migrate legacy data
  const handleMigrateLegacyData = async () => {
    try {
      setMigrationLoading(true);
      const result = await competitorEntityService.migrateLegacyData();
      message.success(
        `Migration completed: ${result.details.migrated_competitors} competitors migrated, ${result.details.existing_competitors} already existed`
      );
      loadCompetitors();
      loadSummary();
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Failed to migrate legacy data';
      message.error(errorMessage);
    } finally {
      setMigrationLoading(false);
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
              Tracking
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
      title: 'Address',
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
    <div style={{ padding: '24px' }}>
      <div style={{ marginBottom: '24px' }}>
        <Title level={2}>Competitor Management</Title>
        <Paragraph>
          Manage your competitor entities and track their pricing data.
        </Paragraph>
      </div>

      {/* Summary Statistics */}
      <Row gutter={16} style={{ marginBottom: '24px' }}>
        <Col span={8}>
          <Card>
            <Statistic
              title="Total Competitors"
              value={summary.total_competitors}
              prefix={<BarChartOutlined />}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="Tracking"
              value={summary.selected_competitors}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="Total Items"
              value={summary.total_items}
              prefix={<EyeOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* Action Bar */}
      <Card style={{ marginBottom: '24px' }}>
        <Space>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={handleCreateCompetitor}
            loading={scrapingLoading}
          >
            Scrape Competitor
          </Button>
          
          <Button
            icon={<PlusOutlined />}
            onClick={handleManualCreateCompetitor}
          >
            Manual Entry
          </Button>
          
          <Button
            icon={<SyncOutlined />}
            onClick={loadCompetitors}
            loading={loading}
          >
            Refresh
          </Button>
          
          <Button
            icon={<SyncOutlined />}
            onClick={handleMigrateLegacyData}
            loading={migrationLoading}
          >
            Migrate Legacy Data
          </Button>
        </Space>
      </Card>

      {/* Competitors Table */}
      <Card>
        <Table
          columns={columns}
          dataSource={competitors}
          rowKey="id"
          loading={loading}
          locale={{
            emptyText: (
              <Empty
                description="No competitors found"
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              />
            ),
          }}
        />
      </Card>

      {/* Create/Edit Modal */}
      <Modal
        title={editingCompetitor ? 'Edit Competitor' : 'Add New Competitor'}
        open={modalVisible}
        onCancel={() => {
          setModalVisible(false);
          setEditingCompetitor(null);
          form.resetFields();
        }}
        footer={null}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSaveCompetitor}
        >
          <Form.Item
            name="name"
            label="Competitor Name"
            rules={[
              { required: true, message: 'Please enter competitor name' },
              { min: 2, message: 'Name must be at least 2 characters' }
            ]}
          >
            <Input placeholder="Enter competitor name" />
          </Form.Item>

          <Form.Item
            name="website"
            label="Website"
            rules={[
              { type: 'url', message: 'Please enter a valid URL' }
            ]}
          >
            <Input placeholder="https://competitor-website.com" />
          </Form.Item>

          <Form.Item
            name="address"
            label="Address"
          >
            <Input placeholder="Enter competitor address" />
          </Form.Item>

          <Form.Item
            name="category"
            label="Category"
          >
            <Input placeholder="e.g., restaurant, cafe, fast food" />
          </Form.Item>

          <Form.Item
            name="menu_url"
            label="Menu URL"
            rules={[
              { type: 'url', message: 'Please enter a valid URL' }
            ]}
          >
            <Input placeholder="https://competitor-menu-url.com" />
          </Form.Item>

          <Form.Item
            name="is_selected"
            label="Track this competitor"
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>

          <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
            <Space>
              <Button
                onClick={() => {
                  setModalVisible(false);
                  setEditingCompetitor(null);
                  form.resetFields();
                }}
              >
                Cancel
              </Button>
              <Button type="primary" htmlType="submit">
                {editingCompetitor ? 'Update' : 'Create'}
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* Statistics Modal */}
      <Modal
        title="Competitor Statistics"
        open={statsModalVisible}
        onCancel={() => {
          setStatsModalVisible(false);
          setSelectedCompetitorStats(null);
        }}
        footer={[
          <Button key="close" onClick={() => setStatsModalVisible(false)}>
            Close
          </Button>
        ]}
        width={800}
      >
        {statsLoading ? (
          <div style={{ textAlign: 'center', padding: '40px' }}>
            <Spin size="large" />
          </div>
        ) : selectedCompetitorStats ? (
          <div>
            <Title level={4}>{selectedCompetitorStats.competitor_name}</Title>
            
            <Row gutter={16} style={{ marginBottom: '24px' }}>
              <Col span={8}>
                <Statistic
                  title="Total Items"
                  value={selectedCompetitorStats.total_items}
                />
              </Col>
              <Col span={8}>
                <Statistic
                  title="Average Price"
                  value={selectedCompetitorStats.price_stats.avg_price}
                  precision={2}
                  prefix="$"
                />
              </Col>
              <Col span={8}>
                <Statistic
                  title="Price Range"
                  value={`$${selectedCompetitorStats.price_stats.min_price.toFixed(2)} - $${selectedCompetitorStats.price_stats.max_price.toFixed(2)}`}
                />
              </Col>
            </Row>

            <Title level={5}>Category Breakdown</Title>
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
            />
          </div>
        ) : null}
      </Modal>

      {/* Competitor Scraping Modal */}
      <Modal
        title="Scrape Competitor Menu"
        open={scrapingModalVisible}
        onCancel={() => {
          setScrapingModalVisible(false);
          scrapeForm.resetFields();
        }}
        footer={null}
        width={600}
      >
        <Alert
          message="AI-Powered Menu Scraping"
          description="Enter a restaurant name and location. Our AI will automatically find their website, scrape their menu, and add it to your competitor database."
          type="info"
          showIcon
          style={{ marginBottom: '24px' }}
        />
        
        <Form
          form={scrapeForm}
          layout="vertical"
          onFinish={handleScrapeCompetitor}
        >
          <Form.Item
            name="restaurant_name"
            label="Restaurant Name"
            rules={[
              { required: true, message: 'Please enter restaurant name' },
              { min: 2, message: 'Name must be at least 2 characters' }
            ]}
          >
            <Input 
              placeholder="e.g., McDonald's, Starbucks, Local Bistro"
              disabled={scrapingLoading}
            />
          </Form.Item>

          <Form.Item
            name="location"
            label="Location (Optional)"
            extra="Helps find the correct restaurant if there are multiple locations"
          >
            <Input 
              placeholder="e.g., New York, NY or 123 Main St, Boston"
              disabled={scrapingLoading}
            />
          </Form.Item>

          <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
            <Space>
              <Button
                onClick={() => {
                  setScrapingModalVisible(false);
                  scrapeForm.resetFields();
                }}
                disabled={scrapingLoading}
              >
                Cancel
              </Button>
              <Button 
                type="primary" 
                htmlType="submit"
                loading={scrapingLoading}
                icon={<SyncOutlined />}
              >
                {scrapingLoading ? 'Scraping...' : 'Start Scraping'}
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default CompetitorEntities;
