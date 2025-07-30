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
  BarChartOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  LinkOutlined
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
    <div style={{ 
      padding: '0px 0px',
      background: '#fafbfc',
      minHeight: '100vh'
    }}>
      <div style={{ 
        maxWidth: '100vw', 
        margin: '0 auto' 
      }}>
        {/* Navigation */}
        <Button 
          icon={<ArrowLeftOutlined />} 
          onClick={() => navigate('/competitor-analysis')}
          style={{ 
            marginBottom: '32px',
            background: '#fff',
            border: '1px solid #e5e5e7',
            height: '40px',
            padding: '0 20px',
            borderRadius: '8px',
            fontSize: '15px',
            fontWeight: '500',
            color: '#0a0a0a',
            transition: 'all 0.3s ease',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.borderColor = '#007AFF';
            e.currentTarget.style.color = '#007AFF';
            e.currentTarget.style.transform = 'translateX(-2px)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.borderColor = '#e5e5e7';
            e.currentTarget.style.color = '#0a0a0a';
            e.currentTarget.style.transform = 'translateX(0)';
          }}
        >
          Back to Competitor Analysis
        </Button>

        <Card style={{
          border: 'none',
          borderRadius: '12px',
          boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
          background: '#fff',
          overflow: 'hidden'
        }}>
          {/* Header Section */}
          <div style={{ 
            padding: '32px',
            borderBottom: '1px solid #f0f0f2'
          }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '20px' }}>
              <div style={{
                width: '56px',
                height: '56px',
                background: 'linear-gradient(135deg, #007AFF 0%, #0051D5 100%)',
                borderRadius: '12px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0
              }}>
                <ShopOutlined style={{ 
                  fontSize: '28px', 
                  color: '#fff'
                }} />
              </div>
              <div style={{ flex: 1 }}>
                <Title level={2} style={{ 
                  margin: 0,
                  fontSize: '28px',
                  fontWeight: '600',
                  color: '#0a0a0a',
                  letterSpacing: '-0.02em'
                }}>
                  {competitor.name}
                </Title>
                <div style={{ 
                  marginTop: '8px',
                  display: 'flex',
                  flexWrap: 'wrap',
                  gap: '12px',
                  alignItems: 'center'
                }}>
                  {competitor.website && (
                    <a 
                      href={competitor.website} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      style={{
                        color: '#007AFF',
                        textDecoration: 'none',
                        fontSize: '15px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px',
                        transition: 'opacity 0.3s ease'
                      }}
                      onMouseEnter={(e) => e.currentTarget.style.opacity = '0.7'}
                      onMouseLeave={(e) => e.currentTarget.style.opacity = '1'}
                    >
                      <LinkOutlined /> {competitor.website}
                    </a>
                  )}
                  {competitor.address && (
                    <Text style={{ color: '#8e8e93', fontSize: '15px' }}>
                      📍 {competitor.address}
                    </Text>
                  )}
                  {competitor.category && (
                    <Text style={{ color: '#8e8e93', fontSize: '15px' }}>
                      🏷️ {competitor.category}
                    </Text>
                  )}
                  {competitor.is_selected ? (
                    <Tag 
                      color="#34C759" 
                      style={{
                        background: '#34C75920',
                        border: 'none',
                        borderRadius: '6px',
                        padding: '4px 12px',
                        fontSize: '13px',
                        fontWeight: '500'
                      }}
                    >
                      <CheckCircleOutlined /> Tracking Active
                    </Tag>
                  ) : (
                    <Tag 
                      style={{
                        background: '#8e8e9320',
                        color: '#8e8e93',
                        border: 'none',
                        borderRadius: '6px',
                        padding: '4px 12px',
                        fontSize: '13px',
                        fontWeight: '500'
                      }}
                    >
                      Not Tracking
                    </Tag>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Tabs Section */}
          <Tabs 
            activeKey={activeTab} 
            onChange={setActiveTab}
            style={{
              padding: '0 32px',
              marginBottom: 0,
              fontSize: '15px',
              fontWeight: '500',
              color: '#8e8e93',
              marginRight: '32px',
              background: '#fff',
            }}
          >
            <TabPane tab="Overview" key="overview">
              {/* Stats Cards */}
              <Row gutter={24} style={{ marginBottom: '32px' }}>
                <Col span={6}>
                  <div style={{
                    background: '#fafbfc',
                    borderRadius: '12px',
                    padding: '24px',
                    height: '100%',
                    transition: 'all 0.3s ease',
                    cursor: 'pointer'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = '#f5f5f7';
                    e.currentTarget.style.transform = 'translateY(-2px)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = '#fafbfc';
                    e.currentTarget.style.transform = 'translateY(0)';
                  }}>
                    <Statistic
                      title={<span style={{ 
                        color: '#8e8e93', 
                        fontSize: '13px',
                        fontWeight: '500',
                        textTransform: 'uppercase',
                        letterSpacing: '0.05em'
                      }}>Total Items</span>}
                      value={competitorItems.length}
                      prefix={<ShopOutlined style={{ fontSize: '20px', color: '#007AFF' }} />}
                      valueStyle={{
                        fontSize: '32px',
                        fontWeight: '600',
                        color: '#0a0a0a'
                      }}
                    />
                  </div>
                </Col>
                <Col span={6}>
                  <div style={{
                    background: '#fafbfc',
                    borderRadius: '12px',
                    padding: '24px',
                    height: '100%',
                    transition: 'all 0.3s ease',
                    cursor: 'pointer'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = '#f5f5f7';
                    e.currentTarget.style.transform = 'translateY(-2px)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = '#fafbfc';
                    e.currentTarget.style.transform = 'translateY(0)';
                  }}>
                    <Statistic
                      title={<span style={{ 
                        color: '#8e8e93', 
                        fontSize: '13px',
                        fontWeight: '500',
                        textTransform: 'uppercase',
                        letterSpacing: '0.05em'
                      }}>Matched Items</span>}
                      value={itemsWithMatches.length}
                      suffix={<span style={{ fontSize: '16px', color: '#8e8e93' }}>/ {competitorItems.length}</span>}
                      valueStyle={{
                        fontSize: '32px',
                        fontWeight: '600',
                        color: '#34C759'
                      }}
                    />
                  </div>
                </Col>
                <Col span={6}>
                  <div style={{
                    background: '#fafbfc',
                    borderRadius: '12px',
                    padding: '24px',
                    height: '100%',
                    transition: 'all 0.3s ease',
                    cursor: 'pointer'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = '#f5f5f7';
                    e.currentTarget.style.transform = 'translateY(-2px)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = '#fafbfc';
                    e.currentTarget.style.transform = 'translateY(0)';
                  }}>
                    <Statistic
                      title={<span style={{ 
                        color: '#8e8e93', 
                        fontSize: '13px',
                        fontWeight: '500',
                        textTransform: 'uppercase',
                        letterSpacing: '0.05em'
                      }}>Average Price</span>}
                      value={competitorStats?.price_stats?.avg_price || 0}
                      precision={2}
                      prefix="$"
                      loading={statsLoading}
                      valueStyle={{
                        fontSize: '32px',
                        fontWeight: '600',
                        color: '#0a0a0a'
                      }}
                    />
                  </div>
                </Col>
                <Col span={6}>
                  <div style={{
                    background: '#fafbfc',
                    borderRadius: '12px',
                    padding: '24px',
                    height: '100%',
                    transition: 'all 0.3s ease',
                    cursor: 'pointer'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = '#f5f5f7';
                    e.currentTarget.style.transform = 'translateY(-2px)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = '#fafbfc';
                    e.currentTarget.style.transform = 'translateY(0)';
                  }}>
                    <Statistic
                      title={<span style={{ 
                        color: '#8e8e93', 
                        fontSize: '13px',
                        fontWeight: '500',
                        textTransform: 'uppercase',
                        letterSpacing: '0.05em'
                      }}>Price Range</span>}
                      value={competitorStats ? 
                        `$${competitorStats.price_stats?.min_price?.toFixed(2)} - $${competitorStats.price_stats?.max_price?.toFixed(2)}` : 
                        'N/A'
                      }
                      loading={statsLoading}
                      valueStyle={{
                        fontSize: '20px',
                        fontWeight: '600',
                        color: '#0a0a0a'
                      }}
                    />
                  </div>
                </Col>
              </Row>

              {/* Category Breakdown */}
              {competitorStats && (
                <div style={{
                  background: '#fff',
                  border: '1px solid #e5e5e7',
                  borderRadius: '12px',
                  padding: '24px',
                  marginTop: '32px'
                }}>
                  <h3 style={{
                    fontSize: '18px',
                    fontWeight: '600',
                    color: '#0a0a0a',
                    marginBottom: '24px',
                    letterSpacing: '-0.02em'
                  }}>
                    Category Breakdown
                  </h3>
                  <Row gutter={16}>
                    {competitorStats.category_breakdown?.map((category: any, index: number) => (
                      <Col span={8} key={index}>
                        <div style={{
                          background: '#fafbfc',
                          borderRadius: '8px',
                          padding: '20px',
                          marginBottom: '16px',
                          transition: 'all 0.3s ease'
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.background = '#f5f5f7';
                          e.currentTarget.style.transform = 'scale(1.02)';
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.background = '#fafbfc';
                          e.currentTarget.style.transform = 'scale(1)';
                        }}>
                          <div style={{
                            fontSize: '13px',
                            color: '#8e8e93',
                            fontWeight: '500',
                            textTransform: 'uppercase',
                            letterSpacing: '0.05em',
                            marginBottom: '8px'
                          }}>
                            {category.category}
                          </div>
                          <div style={{
                            fontSize: '24px',
                            fontWeight: '600',
                            color: '#0a0a0a',
                            marginBottom: '4px'
                          }}>
                            {category.item_count} <span style={{ fontSize: '14px', color: '#8e8e93' }}>items</span>
                          </div>
                          <Text style={{ color: '#8e8e93', fontSize: '14px' }}>
                            Avg: ${category.avg_price?.toFixed(2) || 'N/A'}
                          </Text>
                        </div>
                      </Col>
                    ))}
                  </Row>
                </div>
              )}
            </TabPane>

            <TabPane 
              tab={
                <span>
                  Items <span style={{
                    background: '#8e8e9320',
                    padding: '2px 8px',
                    borderRadius: '12px',
                    fontSize: '12px',
                    marginLeft: '8px'
                  }}>{filteredItems.length}</span>
                </span>
              } 
              key="items"
            >
              {/* Search and Filter Bar */}
              <div style={{ 
                marginBottom: '24px',
                display: 'flex',
                gap: '16px',
                flexWrap: 'wrap'
              }}>
                <Input.Search
                  placeholder="Search items..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  style={{ 
                    width: 300
                  }}
                  prefix={<SearchOutlined style={{ color: '#8e8e93' }} />}
                  className="modern-search-input"
                />
                <Select
                  placeholder="Filter by category"
                  value={categoryFilter}
                  onChange={setCategoryFilter}
                  allowClear
                  style={{ 
                    width: 200
                  }}
                  className="modern-select"
                  suffixIcon={<FilterOutlined style={{ color: '#8e8e93' }} />}
                >
                  {categories.map(category => (
                    <Option key={category} value={category}>{category}</Option>
                  ))}
                </Select>
              </div>
              
              {/* Items Table */}
              {filteredItems.length > 0 ? (
                <div style={{
                  background: '#fff',
                  borderRadius: '8px',
                  overflow: 'hidden',
                  border: '1px solid #e5e5e7'
                }}>
                  <Table
                    columns={columns}
                    dataSource={filteredItems}
                    rowKey="id"
                    pagination={{
                      pageSize: 10,
                      showSizeChanger: true,
                      showQuickJumper: true,
                      showTotal: (total, range) => (
                        <span style={{ color: '#8e8e93', fontSize: '14px' }}>
                          {range[0]}-{range[1]} of {total} items
                        </span>
                      ),
                    }}
                    scroll={{ x: 800 }}
                    loading={itemsLoading}
                    className="modern-table"
                  />
                </div>
              ) : (
                <Empty 
                  description={
                    <span style={{ color: '#8e8e93', fontSize: '15px' }}>
                      No items found
                    </span>
                  }
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                  style={{ padding: '60px 0' }}
                />
              )}
            </TabPane>

            <TabPane tab="Statistics" key="statistics">
              <Spin spinning={statsLoading}>
                {competitorStats ? (
                  <Row gutter={24}>
                    <Col span={12}>
                      <div style={{
                        background: '#fff',
                        border: '1px solid #e5e5e7',
                        borderRadius: '12px',
                        padding: '24px',
                        height: '100%'
                      }}>
                        <div style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          marginBottom: '24px'
                        }}>
                          <h3 style={{
                            fontSize: '18px',
                            fontWeight: '600',
                            color: '#0a0a0a',
                            margin: 0,
                            letterSpacing: '-0.02em'
                          }}>
                            Price Analysis
                          </h3>
                          <BarChartOutlined style={{ fontSize: '20px', color: '#007AFF' }} />
                        </div>
                        <Row gutter={16}>
                          <Col span={8}>
                            <div style={{ marginBottom: '24px' }}>
                              <div style={{
                                fontSize: '13px',
                                color: '#8e8e93',
                                fontWeight: '500',
                                textTransform: 'uppercase',
                                letterSpacing: '0.05em',
                                marginBottom: '8px'
                              }}>
                                Average Price
                              </div>
                              <div style={{
                                fontSize: '28px',
                                fontWeight: '600',
                                color: '#0a0a0a'
                              }}>
                                ${competitorStats.price_stats?.avg_price?.toFixed(2)}
                              </div>
                            </div>
                          </Col>
                          <Col span={8}>
                            <div style={{ marginBottom: '24px' }}>
                              <div style={{
                                fontSize: '13px',
                                color: '#8e8e93',
                                fontWeight: '500',
                                textTransform: 'uppercase',
                                letterSpacing: '0.05em',
                                marginBottom: '8px'
                              }}>
                                Min Price
                              </div>
                              <div style={{
                                fontSize: '28px',
                                fontWeight: '600',
                                color: '#34C759'
                              }}>
                                ${competitorStats.price_stats?.min_price?.toFixed(2)}
                              </div>
                            </div>
                          </Col>
                          <Col span={8}>
                            <div style={{ marginBottom: '24px' }}>
                              <div style={{
                                fontSize: '13px',
                                color: '#8e8e93',
                                fontWeight: '500',
                                textTransform: 'uppercase',
                                letterSpacing: '0.05em',
                                marginBottom: '8px'
                              }}>
                                Max Price
                              </div>
                              <div style={{
                                fontSize: '28px',
                                fontWeight: '600',
                                color: '#FF3B30'
                              }}>
                                ${competitorStats.price_stats?.max_price?.toFixed(2)}
                              </div>
                            </div>
                          </Col>
                        </Row>
                      </div>
                    </Col>
                    <Col span={12}>
                      <div style={{
                        background: '#fff',
                        border: '1px solid #e5e5e7',
                        borderRadius: '12px',
                        padding: '24px',
                        height: '100%'
                      }}>
                        <div style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          marginBottom: '24px'
                        }}>
                          <h3 style={{
                            fontSize: '18px',
                            fontWeight: '600',
                            color: '#0a0a0a',
                            margin: 0,
                            letterSpacing: '-0.02em'
                          }}>
                            Inventory Analysis
                          </h3>
                          <ShopOutlined style={{ fontSize: '20px', color: '#5856D6' }} />
                        </div>
                        <Row gutter={16}>
                          <Col span={12}>
                            <div style={{ marginBottom: '24px' }}>
                              <div style={{
                                fontSize: '13px',
                                color: '#8e8e93',
                                fontWeight: '500',
                                textTransform: 'uppercase',
                                letterSpacing: '0.05em',
                                marginBottom: '8px'
                              }}>
                                Total Items
                              </div>
                              <div style={{
                                fontSize: '28px',
                                fontWeight: '600',
                                color: '#0a0a0a'
                              }}>
                                {competitorStats.total_items}
                              </div>
                            </div>
                          </Col>
                          <Col span={12}>
                            <div style={{ marginBottom: '24px' }}>
                              <div style={{
                                fontSize: '13px',
                                color: '#8e8e93',
                                fontWeight: '500',
                                textTransform: 'uppercase',
                                letterSpacing: '0.05em',
                                marginBottom: '8px'
                              }}>
                                Categories
                              </div>
                              <div style={{
                                fontSize: '28px',
                                fontWeight: '600',
                                color: '#0a0a0a'
                              }}>
                                {competitorStats.category_breakdown?.length || 0}
                              </div>
                            </div>
                          </Col>
                        </Row>
                        <Divider style={{ margin: '20px 0', borderColor: '#e5e5e7' }} />
                        <Text style={{ 
                          color: '#8e8e93', 
                          fontSize: '13px',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '4px'
                        }}>
                          <ClockCircleOutlined />
                          Last updated: {competitor.updated_at ? 
                            new Date(competitor.updated_at).toLocaleDateString('en-US', {
                              year: 'numeric',
                              month: 'short',
                              day: 'numeric'
                            }) : 
                            'Unknown'
                          }
                        </Text>
                      </div>
                    </Col>
                  </Row>
                ) : (
                  <Empty 
                    description={
                      <span style={{ color: '#8e8e93', fontSize: '15px' }}>
                        No statistics available
                      </span>
                    }
                    image={Empty.PRESENTED_IMAGE_SIMPLE}
                    style={{ padding: '60px 0' }}
                  />
                )}
              </Spin>
            </TabPane>
          </Tabs>
        </Card>
      </div>
    </div>
  );
};

export default CompetitorDetail;
