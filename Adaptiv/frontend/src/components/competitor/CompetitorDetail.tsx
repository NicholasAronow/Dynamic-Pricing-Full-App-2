import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Card,
  Spin,
  Alert,
  Button,
  Typography,
  Row,
  Col,
  Statistic,
  Table,
  Tag,
  Tabs,
  Input,
  Select,
  Space,
  Empty,
  Divider
} from 'antd';
import {
  ArrowLeftOutlined,
  ShopOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
  SearchOutlined,
  FilterOutlined,
  DollarOutlined,
  BarChartOutlined
} from '@ant-design/icons';
import competitorEntityService, {
  CompetitorEntity,
  CompetitorItem,
  CompetitorStats
} from '../../services/competitorEntityService';
import itemService, { Item } from '../../services/itemService';

const { Title, Text } = Typography;
const { TabPane } = Tabs;
const { Option } = Select;
const { Search } = Input;

interface ItemWithComparison extends CompetitorItem {
  ourItem?: Item;
  priceDifference?: number | null;
  status: 'higher' | 'lower' | 'same' | 'no-match';
}

const CompetitorDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [competitor, setCompetitor] = useState<CompetitorEntity | null>(null);
  const [competitorItems, setCompetitorItems] = useState<CompetitorItem[]>([]);
  const [competitorStats, setCompetitorStats] = useState<CompetitorStats | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [itemsLoading, setItemsLoading] = useState<boolean>(false);
  const [statsLoading, setStatsLoading] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<string>('overview');
  const [categoryFilter, setCategoryFilter] = useState<string | undefined>(undefined);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [ourItems, setOurItems] = useState<Item[]>([]);
  const [error, setError] = useState<string | null>(null);

  // Fetch competitor data on component mount
  useEffect(() => {
    const fetchCompetitorData = async () => {
      if (!id) {
        setError('No competitor ID provided');
        setLoading(false);
        return;
      }
  
      try {
        setLoading(true);
        
        // Fetch competitor entity WITHOUT items
        const competitor = await competitorEntityService.getCompetitorEntity(
          parseInt(id), 
          false  // Don't include items to avoid circular reference
        );
        
        if (competitor) {
          setCompetitor(competitor);
          
          // Fetch items separately using the dedicated endpoint
          try {
            setItemsLoading(true);
            const items = await competitorEntityService.getCompetitorItems(parseInt(id), { limit: 1000 });
            setCompetitorItems(items || []);
          } catch (itemsError) {
            console.error('Error fetching competitor items:', itemsError);
            setCompetitorItems([]);
          } finally {
            setItemsLoading(false);
          }
        } else {
          setError('Competitor not found');
        }
  
        // Fetch our items for price comparison
        const ourItems = await itemService.getItems();
        if (ourItems) {
          setOurItems(ourItems);
        }
  
      } catch (error) {
        console.error('Error fetching competitor data:', error);
        setError('Failed to load competitor data');
      } finally {
        setLoading(false);
      }
    };
  
    fetchCompetitorData();
  }, [id]);

  // Fetch competitor statistics
  useEffect(() => {
    const fetchStats = async () => {
      if (!id || !competitor) return;

      try {
        setStatsLoading(true);
        const stats = await competitorEntityService.getCompetitorStats(parseInt(id));
        
        if (stats) {
          setCompetitorStats(stats);
        }
      } catch (error) {
        console.error('Error fetching competitor stats:', error);
      } finally {
        setStatsLoading(false);
      }
    };

    fetchStats();
  }, [id, competitor]);

  // Calculate price differences for competitor items
  const getItemsWithPriceComparison = (): ItemWithComparison[] => {
    return competitorItems.map(competitorItem => {
      // Find matching item in our inventory using fuzzy matching
      const ourItem = ourItems.find(item => {
        const ourName = item.name.toLowerCase().trim();
        const competitorName = competitorItem.item_name.toLowerCase().trim();
        
        // Exact match
        if (ourName === competitorName) return true;
        
        // Partial match (either contains the other)
        if (ourName.includes(competitorName) || competitorName.includes(ourName)) return true;
        
        // Word-based matching for multi-word items
        const ourWords = ourName.split(' ');
        const competitorWords = competitorName.split(' ');
        const commonWords = ourWords.filter(word => 
          word.length > 2 && competitorWords.some((cWord: string) => cWord.includes(word))
        );
        
        return commonWords.length >= Math.min(ourWords.length, competitorWords.length) / 2;
      });

      let priceDifference = null;
      let status: 'higher' | 'lower' | 'same' | 'no-match' = 'no-match';

      if (ourItem && ourItem.current_price && competitorItem.price) {
        const diff = ((ourItem.current_price - competitorItem.price) / competitorItem.price) * 100;
        priceDifference = diff;
        
        if (diff < -2) status = 'lower';
        else if (diff > 2) status = 'higher';
        else status = 'same';
      }

      return {
        ...competitorItem,
        ourItem,
        priceDifference,
        status
      };
    });
  };

  // Filter items based on search and category
  const getFilteredItems = () => {
    const itemsWithComparison = getItemsWithPriceComparison();
    
    return itemsWithComparison.filter(item => {
      const matchesSearch = !searchTerm || 
        item.item_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (item.ourItem && item.ourItem.name.toLowerCase().includes(searchTerm.toLowerCase()));
      
      const matchesCategory = !categoryFilter || item.category === categoryFilter;
      
      return matchesSearch && matchesCategory;
    });
  };

  // Get unique categories for filter dropdown
  const getCategories = () => {
    return [...new Set(competitorItems.map(item => item.category))].filter(Boolean);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'lower': return 'green';
      case 'higher': return 'red';
      case 'same': return 'blue';
      case 'no-match': return 'default';
      default: return 'default';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'lower': return <ArrowDownOutlined />;
      case 'higher': return <ArrowUpOutlined />;
      case 'same': return <DollarOutlined />;
      default: return null;
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'lower': return 'We\'re cheaper';
      case 'higher': return 'We\'re pricier';
      case 'same': return 'Similar price';
      case 'no-match': return 'No match';
      default: return 'Unknown';
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '400px' }}>
        <Spin size="large" />
      </div>
    );
  }

  if (error || !competitor) {
    return (
      <div style={{ padding: '20px' }}>
        <Button 
          icon={<ArrowLeftOutlined />} 
          onClick={() => navigate('/competitor-analysis')}
          style={{ marginBottom: '20px' }}
        >
          Back to Competitor Analysis
        </Button>
        <Alert
          message="Error"
          description={error || 'Competitor data not found'}
          type="error"
          showIcon
        />
      </div>
    );
  }

  const filteredItems = getFilteredItems();
  const categories = getCategories();
  const itemsWithMatches = filteredItems.filter(item => item.status !== 'no-match');

  const columns = [
    {
      title: 'Item Name',
      dataIndex: 'item_name',
      key: 'item_name',
      render: (text: string, record: ItemWithComparison) => (
        <div>
          <div style={{ fontWeight: 'bold' }}>{record.item_name}</div>
          {record.ourItem && record.ourItem.name !== record.item_name && (
            <div style={{ fontSize: '12px', color: '#666' }}>
              Our item: {record.ourItem.name}
            </div>
          )}
        </div>
      ),
    },
    {
      title: 'Category',
      dataIndex: 'category',
      key: 'category',
      filters: categories.map(category => ({ text: category, value: category })),
      onFilter: (value: any, record: ItemWithComparison) => record.category === value,
    },
    {
      title: 'Their Price',
      dataIndex: 'price',
      key: 'price',
      render: (price: number) => `$${price?.toFixed(2) || 'N/A'}`,
      sorter: (a: ItemWithComparison, b: ItemWithComparison) => (a.price || 0) - (b.price || 0),
    },
    {
      title: 'Our Price',
      key: 'ourPrice',
      render: (record: ItemWithComparison) => 
        record.ourItem?.current_price ? `$${record.ourItem.current_price.toFixed(2)}` : 'N/A',
      sorter: (a: ItemWithComparison, b: ItemWithComparison) => 
        (a.ourItem?.current_price || 0) - (b.ourItem?.current_price || 0),
    },
    {
      title: 'Price Comparison',
      key: 'comparison',
      render: (record: ItemWithComparison) => {
        if (record.status === 'no-match') {
          return <Tag color="default">No match found</Tag>;
        }
        
        const diffText = record.priceDifference 
          ? `${record.priceDifference > 0 ? '+' : ''}${record.priceDifference.toFixed(1)}%`
          : '';
        
        return (
          <Tag 
            color={getStatusColor(record.status)} 
            icon={getStatusIcon(record.status)}
          >
            {getStatusText(record.status)} {diffText && `(${diffText})`}
          </Tag>
        );
      },
      sorter: (a: ItemWithComparison, b: ItemWithComparison) => 
        (a.priceDifference || 0) - (b.priceDifference || 0),
    },
  ];

  return (
    <div style={{ padding: '20px' }}>
      <Button 
        icon={<ArrowLeftOutlined />} 
        onClick={() => navigate('/competitor-analysis')}
        style={{ marginBottom: '20px' }}
      >
        Back to Competitor Analysis
      </Button>

      <Card>
        <div style={{ display: 'flex', alignItems: 'center', marginBottom: '20px' }}>
          <ShopOutlined style={{ fontSize: '24px', marginRight: '12px', color: '#1890ff' }} />
          <div>
            <Title level={2} style={{ margin: 0 }}>
              {competitor.name}
            </Title>
            <Text type="secondary">
              {competitor.website && `${competitor.website} • `}
              {competitor.address && `${competitor.address} • `}
              {competitor.category && `${competitor.category} • `}
              {competitor.is_selected ? (
                <Tag color="green">Selected for tracking</Tag>
              ) : (
                <Tag color="default">Not selected</Tag>
              )}
            </Text>
          </div>
        </div>

        <Tabs activeKey={activeTab} onChange={setActiveTab}>
          <TabPane tab="Overview" key="overview">
            <Row gutter={[16, 16]}>
              <Col span={6}>
                <Card>
                  <Statistic
                    title="Total Items"
                    value={competitorItems.length}
                    prefix={<ShopOutlined />}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card>
                  <Statistic
                    title="Matched Items"
                    value={itemsWithMatches.length}
                    suffix={`/ ${competitorItems.length}`}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card>
                  <Statistic
                    title="Avg Price"
                    value={competitorStats?.price_stats?.avg_price || 0}
                    precision={2}
                    prefix="$"
                    loading={statsLoading}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card>
                  <Statistic
                    title="Price Range"
                    value={competitorStats ? 
                      `$${competitorStats.price_stats?.min_price?.toFixed(2)} - $${competitorStats.price_stats?.max_price?.toFixed(2)}` : 
                      'N/A'
                    }
                    loading={statsLoading}
                  />
                </Card>
              </Col>
            </Row>

            {competitorStats && (
              <Card title="Category Breakdown" style={{ marginTop: '20px' }}>
                <Row gutter={[16, 16]}>
                  {competitorStats.category_breakdown?.map((category: any, index: number) => (
                    <Col span={8} key={index}>
                      <Card size="small">
                        <Statistic
                          title={category.category}
                          value={category.item_count}
                          suffix="items"
                        />
                        <Text type="secondary">
                          Avg: ${category.avg_price?.toFixed(2) || 'N/A'}
                        </Text>
                      </Card>
                    </Col>
                  ))}
                </Row>
              </Card>
            )}
          </TabPane>

          <TabPane tab={`Items (${filteredItems.length})`} key="items">
            <div style={{ marginBottom: '16px' }}>
              <Space>
                <Search
                  placeholder="Search items..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  style={{ width: 250 }}
                  prefix={<SearchOutlined />}
                />
                <Select
                  placeholder="Filter by category"
                  value={categoryFilter}
                  onChange={setCategoryFilter}
                  allowClear
                  style={{ width: 180 }}
                  suffixIcon={<FilterOutlined />}
                >
                  {categories.map(category => (
                    <Option key={category} value={category}>{category}</Option>
                  ))}
                </Select>
              </Space>
            </div>
            
            {filteredItems.length > 0 ? (
              <Table
                columns={columns}
                dataSource={filteredItems}
                rowKey="id"
                pagination={{
                  pageSize: 10,
                  showSizeChanger: true,
                  showQuickJumper: true,
                  showTotal: (total, range) => `${range[0]}-${range[1]} of ${total} items`,
                }}
                scroll={{ x: 800 }}
                loading={itemsLoading}
              />
            ) : (
              <Empty 
                description="No items found"
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              />
            )}
          </TabPane>

          <TabPane tab="Statistics" key="statistics">
            <Spin spinning={statsLoading}>
              {competitorStats ? (
                <Row gutter={[16, 16]}>
                  <Col span={12}>
                    <Card title="Price Analysis" extra={<BarChartOutlined />}>
                      <Row gutter={16}>
                        <Col span={8}>
                          <Statistic
                            title="Average Price"
                            value={competitorStats.price_stats?.avg_price}
                            precision={2}
                            prefix="$"
                          />
                        </Col>
                        <Col span={8}>
                          <Statistic
                            title="Min Price"
                            value={competitorStats.price_stats?.min_price}
                            precision={2}
                            prefix="$"
                          />
                        </Col>
                        <Col span={8}>
                          <Statistic
                            title="Max Price"
                            value={competitorStats.price_stats?.max_price}
                            precision={2}
                            prefix="$"
                          />
                        </Col>
                      </Row>
                    </Card>
                  </Col>
                  <Col span={12}>
                    <Card title="Inventory Analysis" extra={<ShopOutlined />}>
                      <Row gutter={16}>
                        <Col span={12}>
                          <Statistic
                            title="Total Items"
                            value={competitorStats.total_items}
                          />
                        </Col>
                        <Col span={12}>
                          <Statistic
                            title="Categories"
                            value={competitorStats.category_breakdown?.length || 0}
                          />
                        </Col>
                      </Row>
                      <Divider />
                      <Text type="secondary">
                        Last updated: {competitor.updated_at ? 
                          new Date(competitor.updated_at).toLocaleDateString() : 
                          'Unknown'
                        }
                      </Text>
                    </Card>
                  </Col>
                </Row>
              ) : (
                <Empty 
                  description="No statistics available"
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                />
              )}
            </Spin>
          </TabPane>
        </Tabs>
      </Card>
    </div>
  );
};

export default CompetitorDetail;
