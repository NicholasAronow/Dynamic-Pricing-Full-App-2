import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Typography, Card, Button, Row, Col, Space, Statistic, Table, Tag, Divider, Spin } from 'antd';
import { 
  ArrowLeftOutlined, 
  ArrowUpOutlined, 
  ArrowDownOutlined, 
  ShopOutlined, 
  DollarOutlined,
  LeftOutlined 
} from '@ant-design/icons';
import { 
  ResponsiveContainer, 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip as RechartsTooltip, 
  Legend 
} from 'recharts';

const { Title, Text } = Typography;

// Utility function to format numbers with commas
const formatNumberWithCommas = (num: any): string => {
  if (Array.isArray(num)) {
    return formatNumberWithCommas(num[0]);
  }
  if (typeof num === 'string') {
    return Number(num).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  }
  if (typeof num === 'number') {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  }
  return String(num);
};

// Sample data generator function for common items
const generateCommonItems = (competitorId: string) => {
  const items = [
    {
      key: '1',
      itemName: 'Signature Latte',
      ourPrice: 4.50,
      theirPrice: 4.95,
      category: 'Beverages'
    },
    {
      key: '2',
      itemName: 'Cappuccino',
      ourPrice: 4.25,
      theirPrice: 3.99,
      category: 'Beverages'
    },
    {
      key: '3',
      itemName: 'Croissant',
      ourPrice: 3.50,
      theirPrice: 3.99,
      category: 'Bakery'
    },
    {
      key: '4',
      itemName: 'Avocado Toast',
      ourPrice: 8.99,
      theirPrice: 9.49,
      category: 'Food'
    },
    {
      key: '5',
      itemName: 'Blueberry Muffin',
      ourPrice: 3.25,
      theirPrice: 2.99,
      category: 'Bakery'
    },
    {
      key: '6',
      itemName: 'Cold Brew',
      ourPrice: 4.75,
      theirPrice: 5.25,
      category: 'Beverages'
    },
    {
      key: '7',
      itemName: 'Breakfast Sandwich',
      ourPrice: 6.99,
      theirPrice: 7.49,
      category: 'Food'
    },
  ];

  // Calculate the price difference and status
  const itemsWithDifference = items.map(item => {
    // Calculate how our price compares to theirs
    // Negative percentage means our price is lower (good)
    // Positive percentage means our price is higher (bad)
    const priceDiff = ((item.ourPrice - item.theirPrice) / item.theirPrice) * 100;
    const status = priceDiff < 0 ? 'lower' : priceDiff > 0 ? 'higher' : 'same';
    const formattedDiff = `${priceDiff > 0 ? '+' : ''}${priceDiff.toFixed(1)}%`;
    
    return {
      ...item,
      difference: formattedDiff,
      diffValue: priceDiff, // Store the actual numeric value for sorting
      status: status
    };
  });

  // Filter items randomly based on competitorId to simulate different competitors having different items
  return itemsWithDifference.filter((_, index: number) => {
    const competitorIdNum = parseInt(competitorId || '1', 10);
    return (index % competitorIdNum !== 0);
  });
};

// Generate market position data with normalized 1-10 scale
const generateMarketPositionData = (competitorId: string) => {
  // This would come from API in a real implementation
  const competitorIdNum = parseInt(competitorId || '1', 10);
  
  // Original price points (for reference)
  const originalMarketLow = 3.99;
  const originalMarketHigh = 6.99;
  const originalOurPrice = 4.50;
  
  // Define the normalized scale
  const scaleMin = 1;
  const scaleMax = 10;
  
  // Set original competitor price based on ID
  let originalCompetitorPrice;
  if (competitorIdNum === 1) {
    originalCompetitorPrice = 4.29; // Lower than our price
  } else if (competitorIdNum === 2) {
    originalCompetitorPrice = 4.99; // Same as market average
  } else {
    originalCompetitorPrice = 5.49; // Higher than our price
  }
  
  // Normalize prices to 1-10 scale
  const normalize = (price: number) => {
    // Linear transformation from the original price range to 1-10 scale
    return (
      ((price - originalMarketLow) / (originalMarketHigh - originalMarketLow)) * 
      (scaleMax - scaleMin) + 
      scaleMin
    );
  };
  
  const normalizedMarketLow = scaleMin;
  const normalizedMarketHigh = scaleMax;
  const normalizedOurPrice = normalize(originalOurPrice);
  const normalizedCompetitorPrice = normalize(originalCompetitorPrice);
  const normalizedMarketAverage = normalize(4.99); // Original market average
  
  // Calculate percentage position for visualization
  const ourPricePosition = ((normalizedOurPrice - scaleMin) / (scaleMax - scaleMin)) * 100;
  const competitorPricePosition = ((normalizedCompetitorPrice - scaleMin) / (scaleMax - scaleMin)) * 100;
  
  return {
    // Original price data (for reference and display in table)
    originalMarketLow,
    originalMarketHigh,
    originalOurPrice,
    originalCompetitorPrice,
    originalMarketAverage: 4.99,
    
    // Normalized scale data (for visualization)
    marketLow: normalizedMarketLow,
    marketHigh: normalizedMarketHigh,
    ourPrice: normalizedOurPrice,
    competitorPrice: normalizedCompetitorPrice,
    marketAverage: normalizedMarketAverage,
    
    // Positioning for visualization
    ourPricePosition,
    competitorPricePosition
  };
};

const CompetitorDetail: React.FC = () => {
  const { competitorId } = useParams<{ competitorId: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState<boolean>(true);
  const [commonItems, setCommonItems] = useState<any[]>([]);
  const [marketPositionData, setMarketPositionData] = useState<any>(null);

  // This would normally come from an API
  const competitors = [
    {
      id: '1',
      name: 'PriceWise',
      similarityScore: 85,
      priceDifference: '+15%',
      status: 'higher',
      categories: ['Dynamic Pricing', 'Analytics', 'Integrations']
    },
    {
      id: '2',
      name: 'MarketMaster',
      similarityScore: 72,
      priceDifference: '-3%',
      status: 'lower',
      categories: ['Analytics', 'AI Recommendations']
    },
    {
      id: '3',
      name: 'PricePoint',
      similarityScore: 91,
      priceDifference: '+5%',
      status: 'higher',
      categories: ['Analytics', 'Integrations', 'Multi-platform']
    }
  ];
  
  const competitorData = competitors.find(comp => comp.id === competitorId) || {
    id: competitorId,
    name: 'Competitor ' + competitorId,
    similarityScore: 85,
    priceDifference: '+15%',
    status: 'higher',
    categories: ['Dynamic Pricing', 'Analytics', 'Integrations']
  };
  
  useEffect(() => {
    // Simulate API loading
    setLoading(true);
    
    setTimeout(() => {
      setCommonItems(generateCommonItems(competitorId || '1'));
      setMarketPositionData(generateMarketPositionData(competitorId || '1'));
      setLoading(false);
    }, 1000);
  }, [competitorId]);

  if (loading) {
    return (
      <div style={{ height: '100vh', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <Button 
          type="link" 
          icon={<LeftOutlined />} 
          onClick={() => navigate('/competitor-analysis')}
          style={{ padding: 0, fontSize: 20, color: 'gray' }}
        >
          Competitor Analysis
        </Button>
        
        {/* Header Section */}
        <Card>
          <Row gutter={[24, 24]} align="middle">
            <Col xs={24} md={8}>
              <div style={{ display: 'flex', alignItems: 'center' }}>
                <div style={{ 
                  width: 64, 
                  height: 64, 
                  backgroundColor: '#f0f0f0', 
                  borderRadius: '50%', 
                  display: 'flex', 
                  justifyContent: 'center', 
                  alignItems: 'center',
                  marginRight: 16,
                  fontSize: 28
                }}>
                  <ShopOutlined />
                </div>
                <div>
                  <Title level={3} style={{ margin: 0 }}>{competitorData.name}</Title>
                  <div style={{ marginTop: 8 }}>
                    {competitorData.categories.map((category, index) => (
                      <Tag color="blue" key={index} style={{ marginBottom: 4 }}>{category}</Tag>
                    ))}
                  </div>
                </div>
              </div>
            </Col>
            <Col xs={24} md={8} style={{ textAlign: 'center' }}>
              <Statistic
                title="Relative Price"
                value={competitorData.priceDifference}
                valueStyle={{
                  color: competitorData.status === 'higher' ? '#cf1322' : '#3f8600'
                }}
                prefix={competitorData.status === 'higher' ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
              />
              <Text type="secondary">compared to our prices</Text>
            </Col>
            <Col xs={24} md={8} style={{ textAlign: 'center' }}>
              <Statistic
                title="Similarity Score"
                value={competitorData.similarityScore}
                suffix="%"
                valueStyle={{ color: '#1890ff' }}
              />
              <Text type="secondary">based on menu overlap</Text>
            </Col>
          </Row>
        </Card>
        
        {/* Market Overview Card */}
        <Card>
          <Divider>Relative Market Position</Divider>
          <div style={{ padding: '80px 0 80px' }}>
            <div style={{ position: 'relative', height: 10, background: 'linear-gradient(to right, #f0f0f0, #d9d9d9, #bfbfbf)', borderRadius: 4 }}>
              {/* Our price dot */}
              <div
                style={{
                  position: 'absolute',
                  left: `${marketPositionData?.ourPricePosition}%`,
                  top: '50%',
                  width: 12,
                  height: 12,
                  backgroundColor: '#1890ff',
                  borderRadius: '50%',
                  transform: 'translate(-50%, -50%)',
                  border: '2px solid white',
                  zIndex: 2
                }}
              />
              
              {/* Competitor price dot */}
              <div
                style={{
                  position: 'absolute',
                  left: `${marketPositionData?.competitorPricePosition}%`,
                  top: '50%',
                  width: 12,
                  height: 12,
                  backgroundColor: '#cf1322',
                  borderRadius: '50%',
                  transform: 'translate(-50%, -50%)',
                  border: '2px solid white',
                  zIndex: 2
                }}
              />
              
              {/* Market average dot with hover effect */}
              <div style={{ position: 'relative' }}>
                <div
                  style={{
                    position: 'absolute',
                    left: `${(marketPositionData?.marketAverage ? (marketPositionData.marketAverage - 1) / 9 * 100 : 50)}%`,
                    top: 5,
                    width: 12,
                    height: 12,
                    backgroundColor: '#faad14',
                    borderRadius: '50%',
                    transform: 'translate(-50%, -50%)',
                    border: '2px solid white',
                    zIndex: 2,
                    cursor: 'pointer'
                  }}
                  onMouseOver={(e) => {
                    // Find the tooltip element
                    const tooltip = e.currentTarget.nextElementSibling as HTMLElement;
                    if (tooltip) {
                      tooltip.style.display = 'block';
                    }
                  }}
                  onMouseOut={(e) => {
                    // Find the tooltip element
                    const tooltip = e.currentTarget.nextElementSibling as HTMLElement;
                    if (tooltip) {
                      tooltip.style.display = 'none';
                    }
                  }}
                />
                <div
                  style={{
                    position: 'absolute',
                    left: `${(marketPositionData?.marketAverage ? (marketPositionData.marketAverage - 1) / 9 * 100 : 50)}%`,
                    top: -50,
                    transform: 'translateX(-50%)',
                    backgroundColor: '#fff8e6',
                    border: '1px solid #ffe58f',
                    borderRadius: '4px',
                    padding: '4px 8px',
                    zIndex: 3,
                    display: 'none',
                    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.15)',
                    whiteSpace: 'nowrap',
                    textAlign: 'center',
                    color: '#5c3c00',
                    fontSize: '14px',
                    fontWeight: 'bold'
                  }}
                >
                  Market Average: {marketPositionData?.marketAverage ? marketPositionData.marketAverage.toFixed(1) : '0.0'}
                </div>
              </div>
              {/* Scale markings */}
              {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map(mark => {
                // Calculate position - distributing marks from 0% to 100%
                const position = (mark - 1) / 9 * 100; // This ensures mark 1 is at 0% and mark 10 is at 100%
                
                return (
                  <div 
                    key={mark}
                    style={{
                      position: 'absolute',
                      left: `${position}%`,
                      bottom: -20,
                      color: '#666',
                      fontSize: '12px',
                      transform: 'translateX(-50%)'
                    }}
                  >
                    {mark}
                  </div>
                );
              })}
              
              {/* Our price marker */}
              <div 
                style={{ 
                  position: 'absolute', 
                  left: `${marketPositionData?.ourPricePosition}%`, 
                  bottom: -50, 
                  transform: 'translateX(-50%)',
                  color: '#1890ff',
                  textAlign: 'center',
                  backgroundColor: '#f0f9ff',
                  padding: '2px 8px',
                  borderRadius: '4px',
                  border: '1px solid #d6e4ff',
                  minWidth: '80px'
                }}
              >
                <ArrowUpOutlined style={{ fontSize: 20, position: 'absolute', top: -20, left: '50%', transform: 'translateX(-50%)', color: '#1890ff' }} />
                <div style={{ fontWeight: 'bold' }}>Your Price: {marketPositionData?.ourPrice ? marketPositionData.ourPrice.toFixed(1) : '0.0'}</div>
              </div>
              
              {/* Competitor price marker */}
              <div 
                style={{ 
                  position: 'absolute', 
                  left: `${marketPositionData?.competitorPricePosition}%`, 
                  top: -50, 
                  transform: 'translateX(-50%)',
                  color: '#cf1322',
                  textAlign: 'center',
                  backgroundColor: '#fff1f0',
                  padding: '2px 8px',
                  borderRadius: '4px',
                  border: '1px solid #ffccc7',
                  minWidth: '80px'
                }}
              >
                <div style={{ fontWeight: 'bold' }}>{competitorData.name}: {marketPositionData?.competitorPrice ? marketPositionData.competitorPrice.toFixed(1) : '0.0'}</div>
                <ArrowDownOutlined style={{ fontSize: 20, position: 'absolute', bottom: -20, left: '50%', transform: 'translateX(-50%)', color: '#cf1322' }} />
              </div>
            </div>
          </div>
          
          <Text type="secondary" style={{ display: 'block' }}>
            This chart shows the relative price positioning on a normalized scale of 1-10, where 1 represents the lowest market price and 10 represents the highest market price. 
            Original dollar prices are shown below each score.
          </Text>
        </Card>
        
        {/* Common Items Table */}
        <Card 
          title={<span><ShopOutlined /> Similar Menu Items</span>}
          style={{ marginTop: 24 }}
        >
          <Table 
            dataSource={commonItems}
            rowKey="key"
            pagination={{ pageSize: 5 }}
            onRow={(record) => ({
              onClick: () => navigate(`/product/${record.key}`),
              style: { cursor: 'pointer' }
            })}
            columns={[
              {
                title: 'Item Name',
                dataIndex: 'itemName',
                key: 'itemName',
                sorter: (a, b) => a.itemName.localeCompare(b.itemName),
                sortDirections: ['ascend', 'descend'],
                defaultSortOrder: 'ascend', // Start with alphabetical sorting by default
                render: (text, record) => (
                  <div>
                    <div>{text}</div>
                    <Tag color="blue">{record.category}</Tag>
                  </div>
                )
              },
              {
                title: 'Our Price',
                dataIndex: 'ourPrice',
                key: 'ourPrice',
                sorter: (a, b) => a.ourPrice - b.ourPrice,
                sortDirections: ['ascend', 'descend'],
                render: (price) => `$${price.toFixed(2)}`
              },
              {
                title: 'Their Price',
                dataIndex: 'theirPrice',
                key: 'theirPrice',
                sorter: (a, b) => a.theirPrice - b.theirPrice,
                sortDirections: ['ascend', 'descend'],
                render: (price) => `$${price.toFixed(2)}`
              },
              {
                title: 'Difference',
                dataIndex: 'difference',
                key: 'difference',
                sorter: (a, b) => a.diffValue - b.diffValue, // Sort by the actual numeric difference
                sortDirections: ['ascend', 'descend'],
                render: (text, record) => {
                  // Our price being lower is good (green down arrow)
                  // Our price being higher is bad (red up arrow)
                  const color = record.status === 'lower' ? '#3f8600' : '#cf1322';
                  const icon = record.status === 'lower' ? 
                    <ArrowDownOutlined style={{ marginRight: 4 }} /> : 
                    <ArrowUpOutlined style={{ marginRight: 4 }} />;
                  
                  return (
                    <span style={{ color }}>
                      {icon}
                      {text}
                    </span>
                  );
                }
              }
            ]}
          />
          <Text type="secondary" style={{ display: 'block', marginTop: 16 }}>
            Click on any item to view detailed product information and metrics.
          </Text>
        </Card>
      </Space>
    </div>
  );
};

export default CompetitorDetail;
