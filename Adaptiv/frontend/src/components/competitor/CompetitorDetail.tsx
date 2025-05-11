import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Typography, Card, Button, Row, Col, Space, Statistic, Table, Tag, Divider, Spin, Alert } from 'antd';
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
import competitorService, { CompetitorItem } from '../../services/competitorService';
import itemService, { Item } from '../../services/itemService';

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

// Interface for our processed competitor data
interface CompetitorData {
  id: string;
  name: string;
  similarityScore: number;
  priceDifference: string;
  status: 'higher' | 'lower' | 'same';
  categories: string[];
}

// Interface for common items between our menu and competitor menu
interface CommonItem {
  key: string;
  itemName: string;
  ourPrice: number;
  theirPrice: number;
  category: string;
  difference: string;
  diffValue: number;
  status: 'higher' | 'lower' | 'same';
  productId: string; // Added product ID for navigation
  ourItemName: string; // Our menu item name for reference
}

// Interface for market position visualization
interface MarketPosition {
  marketLow: number;
  marketHigh: number;
  ourPrice: number;
  competitorPrice: number;
  marketAverage: number;
  ourPricePosition: number;
  competitorPricePosition: number;
  originalMarketLow: number;
  originalMarketHigh: number;
  originalOurPrice: number;
  originalCompetitorPrice: number;
  originalMarketAverage: number;
}

const CompetitorDetail: React.FC = () => {
  // Renamed from competitorId to competitorName for clarity
  const { competitorId: competitorName } = useParams<{ competitorId: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [commonItems, setCommonItems] = useState<CommonItem[]>([]);
  const [marketPositionData, setMarketPositionData] = useState<MarketPosition | null>(null);
  const [competitorData, setCompetitorData] = useState<CompetitorData | null>(null);
  
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        
        if (!competitorName) {
          setError('Competitor name is required');
          setLoading(false);
          return;
        }
        
        // Get all competitor names to find the right one
        const competitorNames = await competitorService.getCompetitors();
        
        // Decode the URI component to match with the actual competitor name
        const decodedName = decodeURIComponent(competitorName);
        
        // Check if the name exists in our competitor list
        if (!competitorNames.includes(decodedName)) {
          setError(`Competitor '${decodedName}' not found`);
          setLoading(false);
          return;
        }
        
        // Get competitor items - use the decoded name
        const competitorItems = await competitorService.getCompetitorItems(decodedName);
        
        // Get our items
        const ourItems = await itemService.getItems();
        
        // Create common items array by matching categories
        const processedCommonItems: CommonItem[] = [];
        
        // Helper function to find string similarity
        const findStringSimilarity = (str1: string, str2: string): number => {
          // Convert both strings to lowercase for case-insensitive comparison
          const s1 = str1.toLowerCase();
          const s2 = str2.toLowerCase();
          
          // Count common words
          const words1 = s1.split(/\s+/);
          const words2 = s2.split(/\s+/);
          
          let commonWords = 0;
          words1.forEach(w1 => {
            if (words2.some(w2 => w2.includes(w1) || w1.includes(w2))) {
              commonWords++;
            }
          });
          
          // Return similarity score (0 to 1)
          return commonWords / Math.max(words1.length, words2.length);
        };
        
        // Find common items by category and name similarity
        competitorItems.forEach((compItem, index) => {
          // Find our items in the same category
          const ourCategoryItems = ourItems.filter(item => item.category === compItem.category);
          
          if (ourCategoryItems.length > 0) {
            // Find the most similar item by name
            let bestMatch = ourCategoryItems[0];
            let highestSimilarity = findStringSimilarity(compItem.item_name, bestMatch.name);
            
            // Look for a better match among our items in the same category
            ourCategoryItems.forEach(ourItem => {
              const similarity = findStringSimilarity(compItem.item_name, ourItem.name);
              if (similarity > highestSimilarity) {
                highestSimilarity = similarity;
                bestMatch = ourItem;
              }
            });
            
            const ourItem = bestMatch;
            console.log(`Matched '${compItem.item_name}' with '${ourItem.name}' (similarity: ${highestSimilarity.toFixed(2)})`);
            
            // Calculate price difference
            const priceDiff = ((ourItem.current_price - compItem.price) / compItem.price) * 100;
            const status = priceDiff < 0 ? 'lower' : priceDiff > 0 ? 'higher' : 'same';
            const formattedDiff = `${priceDiff > 0 ? '+' : ''}${priceDiff.toFixed(1)}%`;
            
            processedCommonItems.push({
              key: String(index),
              itemName: compItem.item_name,
              ourPrice: ourItem.current_price,
              theirPrice: compItem.price,
              category: compItem.category,
              difference: formattedDiff,
              diffValue: priceDiff,
              status: status as 'higher' | 'lower' | 'same',
              productId: String(ourItem.id), // Store the actual product ID for navigation
              ourItemName: ourItem.name // Store our item name for reference
            });
          }
        });
        
        // Sort by category
        processedCommonItems.sort((a, b) => a.category.localeCompare(b.category));
        
        setCommonItems(processedCommonItems);
        
        // Create market position data
        const generateMarketData = (): MarketPosition => {
          // Get all price points for visualization
          const allPrices = [...ourItems.map(item => item.current_price), ...competitorItems.map(item => item.price)];
          const marketLow = Math.min(...allPrices);
          const marketHigh = Math.max(...allPrices);
          
          // Calculate average prices
          const ourAvgPrice = ourItems.reduce((acc, item) => acc + item.current_price, 0) / ourItems.length;
          const competitorAvgPrice = competitorItems.reduce((acc, item) => acc + item.price, 0) / competitorItems.length;
          const marketAvgPrice = allPrices.reduce((a, b) => a + b, 0) / allPrices.length;
          
          // Normalize prices to 1-10 scale
          const normalize = (price: number) => {
            return ((price - marketLow) / (marketHigh - marketLow)) * 9 + 1;
          };
          
          // Calculate percentage position for visualization
          const ourPricePosition = ((ourAvgPrice - marketLow) / (marketHigh - marketLow)) * 100;
          const competitorPricePosition = ((competitorAvgPrice - marketLow) / (marketHigh - marketLow)) * 100;
          
          return {
            marketLow: 1,
            marketHigh: 10,
            ourPrice: normalize(ourAvgPrice),
            competitorPrice: normalize(competitorAvgPrice),
            marketAverage: normalize(marketAvgPrice),
            ourPricePosition,
            competitorPricePosition,
            originalMarketLow: marketLow,
            originalMarketHigh: marketHigh,
            originalOurPrice: ourAvgPrice,
            originalCompetitorPrice: competitorAvgPrice,
            originalMarketAverage: marketAvgPrice
          };
        };
        
        setMarketPositionData(generateMarketData());
        
        // Calculate overall competitor data
        const categoriesSet = new Set<string>();
        competitorItems.forEach(item => categoriesSet.add(item.category));
        
        // Calculate average price difference based on the same data used for market position
        const ourAvgPrice = ourItems.reduce((acc, item) => acc + item.current_price, 0) / ourItems.length;
        const competitorAvgPrice = competitorItems.reduce((acc, item) => acc + item.price, 0) / competitorItems.length;
        
        // Use the same calculation method for both price difference and market position
        const avgPriceDiff = ((competitorAvgPrice - ourAvgPrice) / competitorAvgPrice) * 100;
        const formattedDiff = `${avgPriceDiff > 0 ? '+' : ''}${avgPriceDiff.toFixed(1)}%`;
        const status = avgPriceDiff > 0 ? 'higher' : avgPriceDiff < 0 ? 'lower' : 'same';
        
        // Calculate average similarity score
        const avgSimilarityScore = competitorItems.reduce((acc, item) => acc + (item.similarity_score || 75), 0) / competitorItems.length;
        
        setCompetitorData({
          id: '0', // Using a placeholder ID since we're now using names
          name: decodedName,
          similarityScore: Math.round(avgSimilarityScore),
          priceDifference: formattedDiff,
          status: status as 'higher' | 'lower' | 'same',
          categories: Array.from(categoriesSet)
        });
        
        setLoading(false);
      } catch (err) {
        console.error('Error fetching competitor data:', err);
        setError('Failed to load competitor data. Please try again later.');
        setLoading(false);
      }
    };
    
    if (competitorName) {
      fetchData();
    }
  }, [competitorName]);

  if (loading) {
    return (
      <div style={{ height: '100vh', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
        <Spin size="large" />
      </div>
    );
  }
  
  if (error || !competitorData || !competitorName) {
    return (
      <div>
        <Button 
          type="link" 
          icon={<LeftOutlined />} 
          onClick={() => navigate('/competitor-analysis')}
          style={{ padding: 0, fontSize: 16, marginBottom: 16 }}
        >
          Back to Competitor Analysis
        </Button>
        
        <Alert
          message="Error"
          description={error || 'Failed to load competitor data'}
          type="error"
          showIcon
        />
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
                  <Title level={3} style={{ margin: 0 }}>{competitorData?.name}</Title>
                  <div style={{ marginTop: 8 }}>
                    {competitorData?.categories.map((category, index) => (
                      <Tag color="blue" key={index} style={{ marginBottom: 4 }}>{category}</Tag>
                    ))}
                  </div>
                </div>
              </div>
            </Col>
            <Col xs={24} md={8} style={{ textAlign: 'center' }}>
              <Statistic
                title="Relative Price"
                value={competitorData?.priceDifference}
                valueStyle={{
                  color: competitorData?.status === 'higher' ? '#cf1322' : '#3f8600'
                }}
                prefix={competitorData?.status === 'higher' ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
              />
              <Text type="secondary">compared to your prices</Text>
            </Col>
            <Col xs={24} md={8} style={{ textAlign: 'center' }}>
              <Statistic
                title="Similarity Score"
                value={competitorData?.similarityScore}
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
          <Divider orientation="left">Menu Items Comparison</Divider>
          
          {commonItems.length === 0 ? (
            <Alert
              message="No Common Items Found"
              description="No menu items were found that match between your business and this competitor."
              type="info"
              showIcon
            />
          ) : (
            <Table 
              dataSource={commonItems}
              style={{ marginTop: 20 }}
              onRow={(record) => ({
                onClick: () => navigate(`/product/${record.productId}`),
                style: { cursor: 'pointer' }
              })}
              columns={[
                {
                  title: 'Competitor Item',
                  dataIndex: 'itemName',
                  key: 'itemName',
                },
                {
                  title: 'Your Item',
                  dataIndex: 'ourItemName',
                  key: 'ourItemName',
                },
                {
                  title: 'Category',
                  dataIndex: 'category',
                  key: 'category',
                  filters: Array.from(new Set(commonItems.map(item => item.category)))
                    .map(category => ({ text: category, value: category })),
                  onFilter: (value, record) => record.category === value,
                  render: (category) => (
                    <Tag color="blue">{category}</Tag>
                  )
                },
                {
                  title: 'Our Price',
                  dataIndex: 'ourPrice',
                  key: 'ourPrice',
                  render: (price) => `$${price.toFixed(2)}`,
                  sorter: (a, b) => a.ourPrice - b.ourPrice,
                },
                {
                  title: 'Their Price',
                  dataIndex: 'theirPrice',
                  key: 'theirPrice',
                  render: (price) => `$${price.toFixed(2)}`,
                  sorter: (a, b) => a.theirPrice - b.theirPrice,
                },
                {
                  title: 'Difference',
                  dataIndex: 'difference',
                  key: 'difference',
                  sorter: (a, b) => a.diffValue - b.diffValue,
                  render: (text, record) => (
                    <span style={{ 
                      color: record.status === 'higher' ? '#cf1322' : record.status === 'lower' ? '#3f8600' : 'inherit'
                    }}>
                      {record.status === 'higher' 
                        ? <ArrowUpOutlined style={{ marginRight: 4 }} /> 
                        : record.status === 'lower' 
                          ? <ArrowDownOutlined style={{ marginRight: 4 }} /> 
                          : null
                      }
                      {text}
                    </span>
                  )
                },
              ]}
            />
          )}
          
          <Text type="secondary" style={{ display: 'block', marginTop: 16 }}>
            Click on any item to view detailed product information and metrics.
          </Text>
        </Card>
      </Space>
    </div>
  );
};

export default CompetitorDetail;
