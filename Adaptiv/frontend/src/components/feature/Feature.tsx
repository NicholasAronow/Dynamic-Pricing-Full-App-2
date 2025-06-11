import React, { useState, useEffect } from 'react';
import { Typography, Card, Form, Input, Button, Table, message, Spin, Alert, Divider, Space, Tag, Tabs, Modal, List, Descriptions, Steps, Radio, Checkbox, InputNumber, Select, Empty } from 'antd';
import { SearchOutlined, LoadingOutlined, MenuOutlined, LinkOutlined, FileSearchOutlined, AppstoreOutlined, EditOutlined, ShopOutlined, BarChartOutlined } from '@ant-design/icons';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';

const { Title, Text } = Typography;

// TypeScript interface for competitor data
interface Competitor {
  name: string;
  address: string;
  category: string;
  distance_km?: number;
  report_id?: number;
  created_at?: string;
  menu_url?: string | null;
  competitor_data?: {
    name: string;
    address: string;
    category: string;
    distance_km?: number;
    menu_url?: string | null;
    [key: string]: any;
  };
}

// TypeScript interface for menu batch data
interface MenuBatch {
  batch_id: string;
  sync_timestamp: string;
  item_count: number;
}

// TypeScript interface for menu item data
interface MenuItem {
  item_name: string;
  category: string;
  description?: string | null;
  price: number | null;
  price_currency: string;
  availability?: string;
  source_confidence?: string;
  source_url?: string;
  batch_id?: string;
  sync_timestamp?: string;
}

// TypeScript interface for menu URL data
interface MenuUrl {
  url: string;
  source_type: string;
  confidence: string;
  selected?: boolean;
}

const { TabPane } = Tabs;
const { Step } = Steps;

const Feature: React.FC = () => {
  const [form] = Form.useForm();
  const [manualForm] = Form.useForm();
  const [editForm] = Form.useForm();
  const { isAuthenticated } = useAuth();
  const [competitors, setCompetitors] = useState<Competitor[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchCompleted, setSearchCompleted] = useState(false);
  const [showAddForm, setShowAddForm] = useState(false);
  const [activeTab, setActiveTab] = useState<string>('1');
  const [menuItems, setMenuItems] = useState<MenuItem[]>([]);
  const [menuLoading, setMenuLoading] = useState(false);
  const [menuVisible, setMenuVisible] = useState(false);
  const [selectedCompetitor, setSelectedCompetitor] = useState<Competitor | null>(null);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [editingCompetitor, setEditingCompetitor] = useState<Competitor | null>(null);
  const [editLoading, setEditLoading] = useState(false);
  
  // New state variables for competitor comparison tab
  const [selectedCompetitorId, setSelectedCompetitorId] = useState<number | null>(null);
  const [competitorMenuItems, setCompetitorMenuItems] = useState<MenuItem[]>([]);
  const [competitorMenuLoading, setCompetitorMenuLoading] = useState<boolean>(false);
  const [menuBatches, setMenuBatches] = useState<MenuBatch[]>([]);
  const [selectedBatchId, setSelectedBatchId] = useState<string | null>(null);
  const [batchesLoading, setBatchesLoading] = useState<boolean>(false);
  
  // Step-by-step menu discovery states
  const [menuDiscoveryVisible, setMenuDiscoveryVisible] = useState(false);
  const [menuDiscoveryStep, setMenuDiscoveryStep] = useState(0);
  const [menuUrls, setMenuUrls] = useState<MenuUrl[]>([]);
  const [urlsLoading, setUrlsLoading] = useState(false);
  const [extractedMenuItems, setExtractedMenuItems] = useState<MenuItem[]>([]);
  const [currentExtractUrl, setCurrentExtractUrl] = useState<string>('');
  const [extracting, setExtracting] = useState(false);
  const [consolidating, setConsolidating] = useState(false);

  // Load competitors when component mounts
  // Function to fetch available menu batches for a competitor
  const loadMenuBatches = async (reportId: number) => {
    try {
      setBatchesLoading(true);
      setMenuBatches([]);
      
      const token = localStorage.getItem('token');
      if (!token) return;
      
      const response = await axios.get(`/api/gemini-competitors/get-menu-batches/${reportId}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (response.data.success && response.data.batches && response.data.batches.length > 0) {
        // Sort batches by timestamp (newest first)
        const sortedBatches = [...response.data.batches].sort(
          (a, b) => new Date(b.sync_timestamp).getTime() - new Date(a.sync_timestamp).getTime()
        );
        setMenuBatches(sortedBatches);
        // Automatically select the most recent batch
        setSelectedBatchId(sortedBatches[0].batch_id);
        
        // Load menu items with the most recent batch
        if (reportId && sortedBatches[0].batch_id) {
          loadCompetitorMenuWithBatch(reportId, sortedBatches[0].batch_id);
        }
      } else {
        setMenuBatches([]);
        setSelectedBatchId(null);
      }
    } catch (error) {
      console.error("Error loading menu batches:", error);
      message.error("Failed to load menu sync history");
    } finally {
      setBatchesLoading(false);
    }
  };
  
  // Function to load a competitor's menu items with specific batch selection
  const loadCompetitorMenuWithBatch = async (reportId: number, batchId?: string | null) => {
    try {
      setCompetitorMenuLoading(true);
      setCompetitorMenuItems([]);
      
      const token = localStorage.getItem('token');
      if (!token) return;
      
      // Set up query parameters for the API call
      const params: any = {};
      if (batchId) {
        params.batch_id = batchId;
      }
      
      const response = await axios.get(`/api/gemini-competitors/get-stored-menu/${reportId}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        },
        params: params
      });
      
      if (response.data.success) {
        setCompetitorMenuItems(response.data.menu_items);
        
        // Update selected batch from response if not explicitly provided
        if (!batchId && response.data.batch) {
          setSelectedBatchId(response.data.batch.batch_id);
        }

        if (response.data.batch && response.data.batch.sync_timestamp) {
          const date = new Date(response.data.batch.sync_timestamp);
          message.info(`Showing menu from ${date.toLocaleDateString()} ${date.toLocaleTimeString()}`);
        }
      } else {
        message.warning("No menu data available for this competitor");
      }
    } catch (error) {
      console.error("Error loading competitor menu:", error);
      message.error("Failed to load menu data");
    } finally {
      setCompetitorMenuLoading(false);
    }
  };
  
  // Function to fetch competitors from the database
  const fetchCompetitors = async () => {
    try {
      // Get token from localStorage
      const token = localStorage.getItem('token');
      if (!token) {
        return; // Skip if not authenticated
      }

      setLoading(true);
      const response = await axios.get('/api/gemini-competitors/competitors', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.data.success && response.data.competitors) {
        setCompetitors(response.data.competitors);
        if (response.data.competitors.length > 0) {
          setSearchCompleted(true);
        }
      }
    } catch (err) {
      console.error('Error fetching competitors:', err);
      // Don't show error message when just loading initially
    } finally {
      setLoading(false);
    }
  };
  
  useEffect(() => {
    fetchCompetitors();
  }, []);
  
  // Function to load competitor menu when selected in the comparison tab
  const loadCompetitorMenu = async (competitorId: number) => {
    if (!competitorId) {
      setCompetitorMenuItems([]);
      return;
    }
    
    try {
      setCompetitorMenuLoading(true);
      
      const token = localStorage.getItem('token');
      if (!token) {
        message.error('Authentication required');
        return;
      }
      
      // Use the new get-stored-menu endpoint to retrieve data without triggering extraction
      const response = await axios.get(
        `/api/gemini-competitors/get-stored-menu/${competitorId}`,
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      );
      
      if (response.data.success && response.data.menu_items && response.data.menu_items.length > 0) {
        setCompetitorMenuItems(response.data.menu_items);
        message.success('Competitor menu data loaded');
      } else {
        // If no stored menu data is available, ask the user if they want to run extraction
        setCompetitorMenuItems([]);
        Modal.confirm({
          title: 'No menu data available',
          content: 'This competitor doesn\'t have any menu data stored yet. Would you like to extract menu data now?',
          okText: 'Extract Menu Data',
          cancelText: 'Cancel',
          onOk: async () => {
            try {
              message.info('Starting menu extraction process...');
              const extractResponse = await axios.post(
                `/api/gemini-competitors/fetch-menu/${competitorId}`,
                {},
                {
                  headers: {
                    'Authorization': `Bearer ${token}`
                  }
                }
              );
              
              if (extractResponse.data.success && extractResponse.data.menu_items) {
                setCompetitorMenuItems(extractResponse.data.menu_items);
                message.success('Menu data extracted and saved successfully');
              } else {
                message.warning('Menu extraction completed but no items were found');
              }
            } catch (extractErr: any) {
              console.error('Error in menu extraction:', extractErr);
              message.error(extractErr.response?.data?.detail || 'Failed to extract menu data');
            }
          },
        });
      }
    } catch (err: any) {
      console.error('Error loading competitor menu:', err);
      message.error(err.response?.data?.detail || 'Failed to load competitor menu');
      setCompetitorMenuItems([]);
    } finally {
      setCompetitorMenuLoading(false);
    }
  };

  // Function to start step-by-step menu discovery
  const startMenuDiscovery = (competitor: Competitor) => {
    if (!competitor.report_id) {
      message.error('Cannot fetch menu: Missing competitor ID');
      return;
    }
    
    setSelectedCompetitor(competitor);
    setMenuDiscoveryStep(0);
    setMenuUrls([]);
    setExtractedMenuItems([]);
    setMenuDiscoveryVisible(true);
  };
  
  // Step 1: Find menu URLs
  const findMenuUrls = async () => {
    if (!selectedCompetitor?.report_id) {
      message.error('No competitor selected');
      return;
    }
    
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        message.error('Authentication required');
        return;
      }
      
      setUrlsLoading(true);
      
      const response = await axios.post(
        `/api/gemini-competitors/find-menu-urls/${selectedCompetitor.report_id}`,
        {},
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      );
      
      if (response.data.success && response.data.urls) {
        // Add selected property to each URL
        const urlsWithSelection = response.data.urls.map((url: MenuUrl) => ({
          ...url,
          selected: true
        }));
        
        setMenuUrls(urlsWithSelection);
        message.success(`Found ${urlsWithSelection.length} menu sources for ${selectedCompetitor.name}`);
        setMenuDiscoveryStep(1);
      } else {
        message.warning('No menu URLs found for this competitor');
      }
    } catch (err: any) {
      console.error('Error finding menu URLs:', err);
      message.error(err.response?.data?.detail || 'Failed to find menu URLs');
    } finally {
      setUrlsLoading(false);
    }
  };
  
  // Step 2: Extract menu from a URL
  const extractMenuFromUrl = async (url: string) => {
    if (!selectedCompetitor) {
      message.error('No competitor selected');
      return;
    }
    
    try {
      setCurrentExtractUrl(url);
      setExtracting(true);
      
      const token = localStorage.getItem('token');
      if (!token) {
        message.error('Authentication required');
        return;
      }
      
      const response = await axios.post(
        `/api/gemini-competitors/extract-menu-from-url`,
        {
          url: url,
          competitor_name: selectedCompetitor.name,
          competitor_category: selectedCompetitor.category || ''
        },
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      );
      
      if (response.data.success && response.data.menu_items) {
        // Add the new menu items to our existing collection
        const newItems = response.data.menu_items;
        setExtractedMenuItems([...extractedMenuItems, ...newItems]);
        message.success(`Extracted ${newItems.length} menu items from ${url}`);
        
        if (extractedMenuItems.length + newItems.length > 0) {
          setMenuDiscoveryStep(2);
        }
      } else {
        message.warning(`No menu items found at ${url}`);
      }
    } catch (err: any) {
      console.error('Error extracting menu from URL:', err);
      message.error(err.response?.data?.detail || 'Failed to extract menu from URL');
    } finally {
      setCurrentExtractUrl('');
      setExtracting(false);
    }
  };
  
  // Step 3: Consolidate menu data and save
  const consolidateMenuData = async () => {
    if (!selectedCompetitor?.report_id) {
      message.error('No competitor selected');
      return;
    }
    
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        message.error('Authentication required');
        return;
      }
      
      setConsolidating(true);
      
      const response = await axios.post(
        `/api/gemini-competitors/consolidate-menu/${selectedCompetitor.report_id}`,
        extractedMenuItems,
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      );
      
      if (response.data.success && response.data.menu_items) {
        message.success(`Menu consolidated and saved for ${selectedCompetitor.name}`);
        setMenuItems(response.data.menu_items);
        setMenuDiscoveryVisible(false);
        setMenuVisible(true);
      } else {
        message.warning('Problem consolidating menu data');
      }
    } catch (err: any) {
      console.error('Error consolidating menu:', err);
      message.error(err.response?.data?.detail || 'Failed to consolidate menu');
    } finally {
      setConsolidating(false);
    }
  };
  
  // Handle URL selection change
  const handleUrlSelectionChange = (url: string, checked: boolean) => {
    setMenuUrls(menuUrls.map(item => {
      if (item.url === url) {
        return { ...item, selected: checked };
      }
      return item;
    }));
  };
  
  // Traditional full menu fetch process (one API call)
  const handleFetchMenu = async (competitor: Competitor) => {
    setSelectedCompetitor(competitor);
    setMenuLoading(true);
    
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        message.error('Authentication required');
        return;
      }
      
      const response = await axios.post(
        `/api/gemini-competitors/fetch-menu/${competitor.report_id}`,
        {},
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      );
      
      if (response.data.success && response.data.menu_items) {
        setMenuItems(response.data.menu_items);
        setMenuVisible(true);
        
        // After fetching new menu data, refresh the batches list and competitor menu
        if (competitor.report_id) {
          loadMenuBatches(competitor.report_id);
        }
      } else if (response.data.error) {
        message.warning(response.data.error);
      } else {
        message.warning('No menu found for this business');
      }
    } catch (err: any) {
      console.error('Error fetching menu:', err);
      message.error(err.response?.data?.detail || 'Failed to fetch menu');
    } finally {
      setMenuLoading(false);
    }
  };
  
  // Function to delete a competitor
  const handleDeleteCompetitor = async (reportId?: number) => {
    if (!reportId) {
      message.error('Cannot delete competitor: Missing ID');
      return;
    }

    try {
      const token = localStorage.getItem('token');
      if (!token) {
        message.error('Authentication required');
        return;
      }

      await axios.delete(`/api/gemini-competitors/competitors/${reportId}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      message.success('Competitor deleted successfully');

      // Refresh the competitor list
      fetchCompetitors();
    } catch (err) {
      console.error('Error deleting competitor:', err);
      message.error('Failed to delete competitor');
    }
  };

  // Function to edit a competitor
  const handleEditCompetitor = (competitor: Competitor) => {
    setEditingCompetitor(competitor);
    // Get menu_url from competitor.menu_url or from competitor_data if available
    const menu_url = competitor.menu_url || 
      (competitor.competitor_data && typeof competitor.competitor_data === 'object' ? 
        competitor.competitor_data.menu_url : null);
        
    editForm.setFieldsValue({
      name: competitor.name,
      address: competitor.address,
      category: competitor.category,
      distance_km: competitor.distance_km,
      menu_url: menu_url
    });
    setEditModalVisible(true);
  };

  // Function to update a competitor
  const updateCompetitor = async (values: any) => {
    if (!editingCompetitor?.report_id) {
      message.error('Cannot update competitor: Missing ID');
      return;
    }

    try {
      const token = localStorage.getItem('token');
      if (!token) {
        message.error('Authentication required');
        return;
      }

      setEditLoading(true);

      // Make a PUT request to update the competitor
      const response = await axios.put(
        `/api/gemini-competitors/competitors/${editingCompetitor.report_id}`,
        {
          name: values.name,
          address: values.address,
          category: values.category,
          distance_km: values.distance_km ? parseFloat(values.distance_km) : null,
          menu_url: values.menu_url || null
        },
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      );

      if (response.data.success && response.data.competitor) {
        message.success('Competitor updated successfully');
        setEditModalVisible(false);

        // Update the competitor in the list
        setCompetitors(competitors.map(comp => 
          comp.report_id === editingCompetitor.report_id ? response.data.competitor : comp
        ));
      }
    } catch (err: any) {
      console.error('Error updating competitor:', err);
      message.error(err.response?.data?.detail || 'Failed to update competitor');
    } finally {
      setEditLoading(false);
    }
  };

  // Function to add a competitor manually
  const addCompetitorManually = async (values: any) => {
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        message.error('Authentication required');
        return;
      }

      setLoading(true);

      const response = await axios.post(
        '/api/gemini-competitors/manually-add',
        {
          name: values.name,
          address: values.address,
          category: values.category,
          distance_km: values.distance_km ? parseFloat(values.distance_km) : null,
          menu_url: values.menu_url || null
        },
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      );

      if (response.data.success && response.data.competitor) {
        message.success('Competitor added successfully');
        manualForm.resetFields();

        // Add the new competitor to the list
        setCompetitors([response.data.competitor, ...competitors]);
      }
    } catch (err: any) {
      console.error('Error adding competitor manually:', err);
      message.error(err.response?.data?.detail || 'Failed to add competitor');
    }
  };

  const columns = [
    {
      title: 'Business Name',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: 'Address',
      dataIndex: 'address',
      key: 'address',
    },
    {
      title: 'Category',
      dataIndex: 'category',
      key: 'category',
      render: (text: string) => <Tag color="blue">{text}</Tag>,
    },
    {
      title: 'Distance',
      dataIndex: 'distance_km',
      key: 'distance',
      render: (distance: number) => (
        distance ? `${distance.toFixed(2)} km` : 'Unknown'
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (text: any, competitor: any) => (
        <Space>
          <Button 
            icon={<LinkOutlined />} 
            onClick={() => startMenuDiscovery(competitor)} 
            type="primary"
            ghost
          >
            Explore Menu
          </Button>
          <Button 
            icon={<MenuOutlined />} 
            onClick={() => handleFetchMenu(competitor)} 
            loading={menuLoading && selectedCompetitor?.report_id === competitor.report_id}
          >
            Fetch Menu
          </Button>
          <Button
            icon={<EditOutlined />}
            onClick={() => handleEditCompetitor(competitor)}
          >
            Edit
          </Button>
          <Button 
            danger 
            onClick={() => handleDeleteCompetitor(competitor.report_id)}
          >
            Delete
          </Button>
        </Space>
      ),
    },
  ];

  const onFinish = async (values: { business_type: string; location: string }) => {
    setLoading(true);
    setError(null);
    setCompetitors([]);
    setSearchCompleted(false);

    try {
      // Get token from localStorage
      const token = localStorage.getItem('token');
      if (!token) {
        throw new Error('Authentication token not found');
      }

      const response = await axios.post(
        '/api/gemini-competitors/search',
        {
          business_type: values.business_type,
          location: values.location
        },
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      );

      if (response.data.success && response.data.competitors) {
        setCompetitors(response.data.competitors);
        setSearchCompleted(true);
        // Update the local state with new data from search
        // No need to call fetchCompetitors() as we already have the latest data
      } else {
        setError('No competitors found');
      }
      message.success('Competitors found and saved to database');
    } catch (err: any) {
      console.error('Error searching for competitors:', err);
      setError(err.response?.data?.detail || 'Failed to search for competitors');
      message.error('Failed to search for competitors');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="feature-page">
      <Title level={2}>Competitor Discovery</Title>
      <Text type="secondary">
        Use Google Gemini AI to find nearby competitors based on your business type and location.
        Discovered competitors will be saved to your database.
      </Text>
      
      <Tabs defaultActiveKey="1" onChange={(key) => setActiveTab(key)} style={{ marginTop: 24 }}>
        <TabPane tab={<span><SearchOutlined /> Discover</span>} key="1">

      <Card style={{ marginTop: 24 }}>
        <Form
          form={form}
          layout="vertical"
          onFinish={onFinish}
        >
          <Form.Item
            name="business_type"
            label="Business Type"
            rules={[{ required: true, message: 'Please enter your business type' }]}
          >
            <Input placeholder="e.g. Coffee Shop, Restaurant, Bakery" />
          </Form.Item>

          <Form.Item
            name="location"
            label="Location"
            rules={[{ required: true, message: 'Please enter your business location' }]}
          >
            <Input placeholder="e.g. 123 Main St, San Francisco, CA" />
          </Form.Item>

          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              icon={<SearchOutlined />}
              loading={loading}
            >
              Find Competitors
            </Button>
          </Form.Item>
        </Form>

        {error && (
          <Alert
            message="Error"
            description={error}
            type="error"
            showIcon
            style={{ marginTop: 16 }}
          />
        )}
      </Card>

      <Divider orientation="left">Results</Divider>

      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: '40px 0' }}>
          <Space direction="vertical" align="center">
            <Spin size="large" />
            <Text>Searching for competitors using Google Gemini AI...</Text>
          </Space>
        </div>
      ) : searchCompleted ? (
        competitors.length > 0 ? (
          <Table
            dataSource={competitors}
            columns={columns}
            rowKey="report_id"
            pagination={false}
          />
        ) : (
          <Alert
            message="No competitors found"
            description="Try searching with different criteria or add competitors manually."
            type="info"
            showIcon
          />
        )
      ) : null}
      
      <Divider orientation="left">Manually Add Competitor</Divider>
      
      <Button 
        type="primary" 
        onClick={() => setShowAddForm(!showAddForm)}
        style={{ marginBottom: '1rem' }}
      >
        {showAddForm ? 'Cancel' : 'Add New Competitor'}
      </Button>
      
      {showAddForm && (
        <Card style={{ marginBottom: '2rem' }}>
          <Form
            form={manualForm}
            name="add_competitor"
            layout="vertical"
            onFinish={addCompetitorManually}
          >
            <Form.Item
              name="name"
              label="Business Name"
              rules={[{ required: true, message: 'Please enter business name' }]}
            >
              <Input placeholder="Enter business name" />
            </Form.Item>
            
            <Form.Item
              name="address"
              label="Address"
              rules={[{ required: true, message: 'Please enter address' }]}
            >
              <Input placeholder="Enter full address" />
            </Form.Item>
            
            <Form.Item
              name="category"
              label="Category"
              rules={[{ required: true, message: 'Please enter business category' }]}
            >
              <Input placeholder="e.g. Restaurant, Retail, Service" />
            </Form.Item>
            
            <Form.Item
              name="distance_km"
              label="Distance (km)"
            >
              <Input type="number" placeholder="Optional" step="0.1" />
            </Form.Item>
            
            <Form.Item
              name="menu_url"
              label="Menu URL"
              tooltip="Directly provide the URL to this competitor's menu. If provided, this will be used instead of automatic URL discovery."
            >
              <Input placeholder="https://restaurant-example.com/menu" />
            </Form.Item>
            
            <Form.Item>
              <Button type="primary" htmlType="submit" loading={loading}>
                Add Competitor
              </Button>
            </Form.Item>
          </Form>
        </Card>
      )}
      
      {loading ? null : searchCompleted ? null : (
        <Card>
          <Text>Enter your business type and location above to search for nearby competitors.</Text>
        </Card>
      )}
        </TabPane>
        
        <TabPane tab={<span><BarChartOutlined /> Competitor Comparison</span>} key="2">
          <Card>
            <div style={{ marginBottom: 16 }}>
              <Text strong>Select a competitor to view their menu and price data:</Text>
              <div style={{ display: 'flex', marginTop: 12 }}>
                <Select 
                  style={{ width: '60%', marginRight: '12px' }} 
                  placeholder="Select a competitor" 
                  onChange={(value) => {
                    const reportId = value as number;
                    setSelectedCompetitorId(reportId);
                    setSelectedBatchId(null);
                    setMenuBatches([]);
                    // We only need to load the batches - loadMenuBatches will automatically
                    // load the most recent batch's menu items
                    loadMenuBatches(reportId);
                  }}
                  loading={loading}
                  disabled={competitors.length === 0}
                  allowClear
                >
                  {competitors.map((competitor) => (
                    <Select.Option key={competitor.report_id} value={competitor.report_id}>
                      {competitor.name} - {competitor.category} {competitor.distance_km ? `(${competitor.distance_km} km away)` : ''}
                    </Select.Option>
                  ))}
                </Select>
                {menuBatches.length > 0 && (
                  <Select
                    style={{ width: '35%' }}
                    placeholder="Select menu sync"
                    loading={batchesLoading}
                    value={selectedBatchId || undefined}
                    onChange={(batchId: string) => {
                      setSelectedBatchId(batchId);
                      if (selectedCompetitorId) {
                        loadCompetitorMenuWithBatch(selectedCompetitorId, batchId);
                      }
                    }}
                  >
                    {[...menuBatches]
                      .sort((a, b) => new Date(b.sync_timestamp).getTime() - new Date(a.sync_timestamp).getTime())
                      .map((batch) => {
                        const date = new Date(batch.sync_timestamp);
                        const formattedDate = date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
                        return (
                          <Select.Option key={batch.batch_id} value={batch.batch_id}>
                            {formattedDate} ({batch.item_count} items)
                          </Select.Option>
                        );
                      })}
                  </Select>
                )}
              </div>
            </div>
            
            <Divider orientation="left">Menu Items</Divider>
            
            {competitorMenuLoading ? (
              <div style={{ display: 'flex', justifyContent: 'center', padding: '40px 0' }}>
                <Space direction="vertical" align="center">
                  <Spin size="large" />
                  <Text>Loading competitor menu data...</Text>
                </Space>
              </div>
            ) : competitorMenuItems.length > 0 ? (
              <Table 
                dataSource={competitorMenuItems}
                rowKey={(item) => `${item.item_name}-${item.price}`}
                pagination={{ pageSize: 10 }}
                columns={[
                  {
                    title: 'Item Name',
                    dataIndex: 'item_name',
                    key: 'item_name',
                    sorter: (a, b) => a.item_name.localeCompare(b.item_name)
                  },
                  {
                    title: 'Category',
                    dataIndex: 'category',
                    key: 'category',
                    render: (category) => <Tag color="blue">{category}</Tag>,
                    filters: Array.from(new Set(competitorMenuItems.map(item => item.category)))
                      .map(category => ({ text: category, value: category })),
                    onFilter: (value, record) => record.category === value
                  },
                  {
                    title: 'Description',
                    dataIndex: 'description',
                    key: 'description',
                    ellipsis: true
                  },
                  {
                    title: 'Price',
                    dataIndex: 'price',
                    key: 'price',
                    render: (price, record) => (
                      price !== null ? 
                      <Tag color="green">{price} {record.price_currency || '$'}</Tag> : 
                      <Tag color="orange">N/A</Tag>
                    ),
                    sorter: (a, b) => (a.price || 0) - (b.price || 0)
                  },
                  {
                    title: 'Confidence',
                    dataIndex: 'source_confidence',
                    key: 'source_confidence',
                    render: (confidence) => confidence ? (
                      <Tag color={confidence === 'high' ? 'green' : confidence === 'medium' ? 'orange' : 'red'}>
                        {confidence.toUpperCase()}
                      </Tag>
                    ) : '-'
                  },
                  {
                    title: 'Source',
                    dataIndex: 'source_url',
                    key: 'source_url',
                    render: (url) => url ? (
                      <a href={url} target="_blank" rel="noreferrer">
                        <LinkOutlined />
                      </a>
                    ) : '-'
                  }
                ]}
              />
            ) : (
              <Empty 
                description={
                  selectedCompetitorId ? 
                  "No menu data available for this competitor" : 
                  "Select a competitor to view their menu data"
                }
                image={Empty.PRESENTED_IMAGE_SIMPLE} 
              />
            )}
          </Card>
        </TabPane>
      </Tabs>

      {/* Step-by-Step Menu Discovery Modal */}
      <Modal
        title={selectedCompetitor ? `Menu Discovery for ${selectedCompetitor.name}` : 'Menu Discovery'}
        open={menuDiscoveryVisible}
        onCancel={() => setMenuDiscoveryVisible(false)}
        footer={null}
        width={800}
      >
        <div>
          <Steps current={menuDiscoveryStep}>
            <Step title="Find URLs" icon={<LinkOutlined />} description="Find menu sources" />
            <Step title="Extract Items" icon={<FileSearchOutlined />} description="Extract menu from URLs" />
            <Step title="Consolidate" icon={<AppstoreOutlined />} description="Save menu data" />
          </Steps>
          
          <div style={{ marginTop: '30px', minHeight: '300px' }}>
            {/* Step 0: Initial state */}
            {menuDiscoveryStep === 0 && (
              <div style={{ textAlign: 'center' }}>
                <Descriptions title="Competitor Info" bordered column={1}>
                  <Descriptions.Item label="Business Name">{selectedCompetitor?.name}</Descriptions.Item>
                  <Descriptions.Item label="Category">{selectedCompetitor?.category}</Descriptions.Item>
                </Descriptions>
                
                <div style={{ marginTop: '30px' }}>
                  <p>Let's find menu sources for this competitor. We'll search for official websites, online ordering platforms, and third-party menu pages.</p>
                  <Button 
                    type="primary" 
                    icon={<LinkOutlined />} 
                    onClick={findMenuUrls}
                    loading={urlsLoading}
                    size="large"
                  >
                    Find Menu URLs
                  </Button>
                </div>
              </div>
            )}
            
            {/* Step 1: Show and select URLs to process */}
            {menuDiscoveryStep === 1 && (
              <div>
                <Alert 
                  message="Select menu URLs to process" 
                  description="Choose which URLs you want to extract menu data from. URLs with higher confidence are more likely to contain accurate menu information." 
                  type="info" 
                  showIcon 
                  style={{ marginBottom: '16px' }}
                />
                
                <List
                  itemLayout="horizontal"
                  dataSource={menuUrls}
                  renderItem={(url) => (
                    <List.Item
                      key={url.url}
                      actions={[
                        <Button 
                          type="primary" 
                          size="small" 
                          onClick={() => extractMenuFromUrl(url.url)}
                          loading={extracting && currentExtractUrl === url.url}
                          disabled={!url.selected}
                        >
                          Extract Menu
                        </Button>
                      ]}
                    >
                      <List.Item.Meta
                        avatar={<Checkbox 
                          checked={url.selected} 
                          onChange={(e) => handleUrlSelectionChange(url.url, e.target.checked)} 
                        />}
                        title={
                          <a href={url.url} target="_blank" rel="noreferrer">
                            {url.url.length > 60 ? `${url.url.substring(0, 60)}...` : url.url}
                          </a>
                        }
                        description={
                          <span>
                            <Tag color="blue">{url.source_type}</Tag>
                            <Tag color={url.confidence === 'high' ? 'green' : url.confidence === 'medium' ? 'orange' : 'red'}>
                              {url.confidence.toUpperCase()} confidence
                            </Tag>
                          </span>
                        }
                      />
                    </List.Item>
                  )}
                />
                
                <div style={{ marginTop: '20px', display: 'flex', justifyContent: 'space-between' }}>
                  <Button onClick={() => setMenuDiscoveryStep(0)}>Back</Button>
                  <Button 
                    type="primary" 
                    disabled={extractedMenuItems.length === 0}
                    onClick={() => setMenuDiscoveryStep(2)}
                  >
                    Next: Review Extracted Items
                  </Button>
                </div>
              </div>
            )}
            
            {/* Step 2: Review extracted menu items and consolidate */}
            {menuDiscoveryStep === 2 && (
              <div>
                <Alert 
                  message="Review extracted menu items" 
                  description={`${extractedMenuItems.length} menu items have been extracted. You can now consolidate them to remove duplicates and standardize formatting.`}
                  type="success" 
                  showIcon 
                  style={{ marginBottom: '16px' }}
                />
                
                <List
                  itemLayout="horizontal"
                  dataSource={extractedMenuItems.slice(0, 5)}
                  renderItem={(item) => (
                    <List.Item
                      key={`${item.item_name}-${item.price}`}
                      extra={
                        item.price !== null ? (
                          <Tag color="green">
                            ${item.price}
                          </Tag>
                        ) : (
                          <Tag color="orange">Price N/A</Tag>
                        )
                      }
                    >
                      <List.Item.Meta
                        title={item.item_name}
                        description={
                          <>
                            <Tag color="blue">{item.category}</Tag>
                            {item.source_url && (
                              <Tag color="purple">From URL</Tag>
                            )}
                          </>
                        }
                      />
                    </List.Item>
                  )}
                />
                
                {extractedMenuItems.length > 5 && (
                  <div style={{ textAlign: 'center', margin: '10px 0' }}>
                    <Text type="secondary">Showing 5 of {extractedMenuItems.length} items...</Text>
                  </div>
                )}
                
                <div style={{ marginTop: '20px', display: 'flex', justifyContent: 'space-between' }}>
                  <Button onClick={() => setMenuDiscoveryStep(1)}>Back to URLs</Button>
                  <Button 
                    type="primary" 
                    onClick={consolidateMenuData}
                    loading={consolidating}
                  >
                    Consolidate and Save Menu
                  </Button>
                </div>
              </div>
            )}
          </div>
        </div>
      </Modal>
      
      {/* Edit Competitor Modal */}
      <Modal
        title={`Edit ${editingCompetitor?.name}`}
        open={editModalVisible}
        onCancel={() => setEditModalVisible(false)}
        footer={null}
      >
        <Form
          form={editForm}
          layout="vertical"
          onFinish={updateCompetitor}
        >
          <Form.Item
            name="name"
            label="Business Name"
            rules={[{ required: true, message: 'Please enter business name' }]}
          >
            <Input />
          </Form.Item>
          
          <Form.Item
            name="address"
            label="Address"
            rules={[{ required: true, message: 'Please enter address' }]}
          >
            <Input />
          </Form.Item>
          
          <Form.Item
            name="category"
            label="Category"
            rules={[{ required: true, message: 'Please enter business category' }]}
          >
            <Input />
          </Form.Item>
          
          <Form.Item
            name="distance_km"
            label="Distance (km)"
          >
            <InputNumber min={0} step={0.1} />
          </Form.Item>
          
          <Form.Item
            name="menu_url"
            label="Menu URL"
            tooltip="Directly provide the URL to this competitor's menu. If provided, this will be used instead of automatic URL discovery."
          >
            <Input placeholder="https://restaurant-example.com/menu" />
          </Form.Item>
          
          <Form.Item>
            <Space>
              <Button 
                type="primary" 
                htmlType="submit"
                loading={editLoading}
              >
                Update
              </Button>
              <Button onClick={() => setEditModalVisible(false)}>
                Cancel
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* Menu Modal */}
      <Modal
        title={selectedCompetitor ? `Menu for ${selectedCompetitor.name}` : 'Competitor Menu'}
        open={menuVisible}
        onCancel={() => setMenuVisible(false)}
        width={800}
        footer={[
          <Button key="close" onClick={() => setMenuVisible(false)}>
            Close
          </Button>
        ]}
      >
        {menuItems.length > 0 ? (
          <div>
            <Descriptions title="Competitor Info" bordered column={1}>
              <Descriptions.Item label="Business Name">{selectedCompetitor?.name}</Descriptions.Item>
              <Descriptions.Item label="Address">{selectedCompetitor?.address}</Descriptions.Item>
              <Descriptions.Item label="Category">
                <Tag color="blue">{selectedCompetitor?.category}</Tag>
              </Descriptions.Item>
            </Descriptions>
            
            <Divider orientation="left">Menu Items</Divider>
            
            <List
              itemLayout="vertical"
              dataSource={menuItems}
              renderItem={(item) => (
                <List.Item
                  key={item.item_name}
                  extra={
                    item.price !== null ? (
                      <Tag color="green" style={{ fontSize: '16px' }}>
                        {item.price} {item.price_currency || '$'}
                      </Tag>
                    ) : (
                      <Tag color="orange">Price unavailable</Tag>
                    )
                  }
                >
                  <List.Item.Meta
                    title={<span style={{ fontSize: '16px' }}>{item.item_name}</span>}
                    description={
                      <span>
                        <Tag color="blue">{item.category}</Tag>
                        {item.availability && (
                          <Tag color={item.availability === 'Available' ? 'green' : 'orange'}>
                            {item.availability}
                          </Tag>
                        )}
                        {item.source_confidence && (
                          <Tag color={item.source_confidence === 'high' ? 'green' : 
                                   item.source_confidence === 'medium' ? 'orange' : 'red'}>
                            {item.source_confidence.toUpperCase()} confidence
                          </Tag>
                        )}
                      </span>
                    }
                  />
                  {item.description && <p>{item.description}</p>}
                </List.Item>
              )}
            />
          </div>
        ) : (
          <div style={{ textAlign: 'center', padding: '20px' }}>
            <LoadingOutlined spin style={{ fontSize: 24 }} />
            <p>Fetching menu items...</p>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default Feature;
