import React, { useState, useEffect } from 'react';
import { Typography, Card, Row, Col, Statistic, Button, Radio, Spin, Table, Tag, Space, Tooltip as AntTooltip } from 'antd';
import { useNavigate } from 'react-router-dom';
import { 
  ArrowUpOutlined, 
  ArrowDownOutlined, 
  DollarOutlined, 
  TeamOutlined,
  LineChartOutlined,
  RiseOutlined,
  FallOutlined,
  InfoCircleOutlined
} from '@ant-design/icons';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Legend, ResponsiveContainer } from 'recharts';
import { useAuth } from '../../context/AuthContext';
import moment from 'moment';

const { Title } = Typography;

// Mock product data
const products = [
  { id: 1, name: 'Small Coffee', category: 'Coffee', basePrice: 2.99, popularity: 0.9 },
  { id: 2, name: 'Medium Coffee', category: 'Coffee', basePrice: 3.99, popularity: 1.5 },
  { id: 3, name: 'Large Coffee', category: 'Coffee', basePrice: 4.99, popularity: 0.6 },
  { id: 4, name: 'Cappucino', category: 'Coffee', basePrice: 5.99, popularity: 0.8 },
  { id: 5, name: 'Latte', category: 'Coffee', basePrice: 6.99, popularity: 0.7 },
  { id: 6, name: 'Americano', category: 'Coffee', basePrice: 7.99, popularity: 1.2 },
  { id: 7, name: 'Espresso', category: 'Coffee', basePrice: 8.99, popularity: 1.1 },
  { id: 8, name: 'Mocha', category: 'Coffee', basePrice: 9.99, popularity: 1.3 },
  { id: 9, name: 'Croissant', category: 'Pastry', basePrice: 1.99, popularity: 0.85 },
  { id: 10, name: 'Danish', category: 'Pastry', basePrice: 2.99, popularity: 0.95 },
];

// Generate mock product performance data
const generateProductPerformanceData = (timeFrame: string) => {
  // Create a variation multiplier based on the time frame
  const getVariationMultiplier = () => {
    // More variation for longer time periods
    switch (timeFrame) {
      case '1d': return 0.2;
      case '7d': return 0.5;
      case '1m': return 0.8;
      case '6m': return 1.2;
      case '1yr': return 2.0;
      default: return 0.5;
    }
  };

  // Calculate base quantities based on time frame
  const getBaseQuantity = (timeFrame: string) => {
    switch (timeFrame) {
      case '1d': return 5;
      case '7d': return 50;
      case '1m': return 200;
      case '6m': return 800;
      case '1yr': return 2000;
      default: return 50;
    }
  };

  const variationMultiplier = getVariationMultiplier();
  const baseQuantity = getBaseQuantity(timeFrame);

  return products.map(product => {
    // Calculate a sales quantity that varies by product popularity and has some randomness
    const quantity = Math.round(baseQuantity * product.popularity * (1 + (Math.random() * variationMultiplier - variationMultiplier/2)));
    const revenue = quantity * product.basePrice;
    
    // Calculate profit margin (randomized between 30-60%)
    const profitMargin = 0.3 + (Math.random() * 0.3);
    const profit = revenue * profitMargin;
    
    // Calculate growth based on time frame (compared to previous period)
    // More variance for longer time periods
    const growthVariance = variationMultiplier * 30; // convert to percentage points
    const growth = Math.round((Math.random() * growthVariance) - growthVariance/4);
    
    return {
      id: product.id,
      name: product.name,
      category: product.category,
      price: product.basePrice,
      quantity,
      revenue,
      profit,
      growth,
      timeFrame
    };
  });
};

// Generating mock sales data
const generateMockData = (timeFrame: string) => {
  const data = [];
  const now = moment();
  
  let numPoints: number;
  let format: string;
  let dateFormat: string;
  let step: number;
  let unit: any;
  
  switch (timeFrame) {
    case '1d':
      numPoints = 24;
      format = 'HH:mm';
      dateFormat = 'YYYY-MM-DD HH:00';
      step = 1;
      unit = 'hours';
      break;
    case '7d':
      numPoints = 7;
      format = 'MMM DD';
      dateFormat = 'YYYY-MM-DD';
      step = 1;
      unit = 'days';
      break;
    case '1m':
      numPoints = 30;
      format = 'MMM DD';
      dateFormat = 'YYYY-MM-DD';
      step = 1;
      unit = 'days';
      break;
    case '6m':
      numPoints = 26;
      format = 'MMM DD';
      dateFormat = 'YYYY-MM-DD';
      step = 1;
      unit = 'weeks';
      break;
    case '1yr':
      numPoints = 12;
      format = 'MMM YYYY';
      dateFormat = 'YYYY-MM';
      step = 1;
      unit = 'months';
      break;
    default:
      numPoints = 7;
      format = 'MMM DD';
      dateFormat = 'YYYY-MM-DD';
      step = 1;
      unit = 'days';
  }
  
  // Generate data points
  for (let i = numPoints - 1; i >= 0; i--) {
    const date = moment(now).subtract(i * step, unit);
    const baseValue = 5000 + Math.random() * 5000; // Base value between 5000 and 10000
    
    // Add some weekly patterns for daily data
    let modifier = 1;
    if (timeFrame === '1d') {
      // More sales during business hours
      const hour = date.hour();
      if (hour >= 9 && hour <= 17) {
        modifier = 1.5;
      } else if (hour < 6 || hour > 21) {
        modifier = 0.5;
      }
    } else if (timeFrame === '7d' || timeFrame === '1m') {
      // More sales on weekends
      const day = date.day();
      if (day === 0 || day === 6) {
        modifier = 1.3;
      }
    } else if (timeFrame === '1yr') {
      // Seasonal variations
      const month = date.month();
      if (month === 10 || month === 11) { // Holiday season
        modifier = 1.5;
      } else if (month >= 5 && month <= 7) { // Summer
        modifier = 1.2;
      }
    }
    
    // Calculate profit (simplified calculation)
    const cost = baseValue * modifier * 0.65; // Assume COGS is about 65% of sales
    const profit = baseValue * modifier - cost;
    
    // Calculate profit margin (more stable between 25-35%)
    // Small variations based on volume and time patterns, but much less variable
    let baseMargin = 30; // 30% base margin
    
    // Small adjustments based on volume - higher volume slightly lower margin
    if (baseValue * modifier > 7000) {
      baseMargin -= 1.5;
    } else if (baseValue * modifier < 4000) {
      baseMargin += 1;
    }
    
    // Add subtle time patterns
    if (timeFrame === '1d') {
      const hour = date.hour();
      if (hour < 8 || hour > 18) {
        baseMargin += 0.5; // Slightly better margins during off-hours
      }
    } else if (timeFrame === '1m' || timeFrame === '6m') {
      const month = date.month();
      if (month === 10 || month === 11) {
        baseMargin += 0.7; // Slightly better margins during holiday seasons
      }
    }
    
    // Add small random variation (+/- 1.5%)
    const marginVariation = (Math.random() * 3) - 1.5;
    const profitMargin = Math.max(25, Math.min(35, baseMargin + marginVariation));
    
    data.push({
      date: date.format(format),
      fullDate: date.format(dateFormat),
      sales: Math.round(baseValue * modifier),
      profit: Math.round(profit),
      profitMargin: parseFloat(profitMargin.toFixed(1))
    });
  }
  
  return data;
};

// Utility function to format numbers with commas
const formatNumberWithCommas = (num: number | string) => {
  if (typeof num === 'string') {
    return Number(num).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  }
  return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
};

const Dashboard: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [timeFrame, setTimeFrame] = useState('7d');
  const [salesData, setSalesData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [chartView, setChartView] = useState<'sales' | 'margin'>('sales'); // Toggle between sales and profit margin
  const [productsLoading, setProductsLoading] = useState(true);
  const [productPerformance, setProductPerformance] = useState<any[]>([]);
  const [itemsTimeFrame, setItemsTimeFrame] = useState('7d');
  
  // Fetch sales data
  useEffect(() => {
    // Simulate loading data
    setLoading(true);
    // Generate mock data based on selected time frame
    setTimeout(() => {
      setSalesData(generateMockData(timeFrame));
      setLoading(false);
    }, 500);
  }, [timeFrame]);
  
  // Fetch product performance data
  useEffect(() => {
    setProductsLoading(true);
    // Generate mock product performance data
    setTimeout(() => {
      const data = generateProductPerformanceData(itemsTimeFrame);
      setProductPerformance(data);
      setProductsLoading(false);
    }, 600);
  }, [itemsTimeFrame]);
  
  // Extract the user's name for the welcome message
  const userName = user?.email?.split('@')[0] || 'User';
  // Capitalize the first letter of the name
  const formattedName = userName.charAt(0).toUpperCase() + userName.slice(1);
  
  const handleTimeFrameChange = (e: any) => {
    setTimeFrame(e.target.value);
  };
  
  const handleItemsTimeFrameChange = (e: any) => {
    setItemsTimeFrame(e.target.value);
  };
  
  // Get top and bottom 3 products by revenue
  const getTopProducts = () => {
    if (!productPerformance.length) return [];
    return [...productPerformance].sort((a, b) => b.revenue - a.revenue).slice(0, 3);
  };
  
  const getBottomProducts = () => {
    if (!productPerformance.length) return [];
    return [...productPerformance].sort((a, b) => a.revenue - b.revenue).slice(0, 3).sort((a, b) => b.revenue - a.revenue);
  };
  
  const topProducts = getTopProducts();
  const bottomProducts = getBottomProducts();
  
  return (
    <div>
      <Title level={2}>Dashboard</Title>
      <Title level={5} type="secondary" style={{ marginTop: 0, marginBottom: 24 }}>
        Welcome back, {formattedName}! Here's your dynamic pricing overview
      </Title>
      
      {/* Sales/Profit Margin Chart */}
      <Card 
        title={
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span><LineChartOutlined /> {chartView === 'sales' ? 'Sales' : 'Profit Margin'} Over Time</span>
            <div style={{ display: 'flex', gap: '16px' }}>
              <Radio.Group 
                value={chartView}
                onChange={(e) => setChartView(e.target.value)}
                optionType="button"
                buttonStyle="solid"
                size="small"
              >
                <Radio.Button value="sales">Sales</Radio.Button>
                <Radio.Button value="margin">Profit Margin</Radio.Button>
              </Radio.Group>
              <Radio.Group 
                value={timeFrame}
                onChange={handleTimeFrameChange}
                optionType="button"
                buttonStyle="solid"
                size="small"
              >
                <Radio.Button value="1d">1D</Radio.Button>
                <Radio.Button value="7d">7D</Radio.Button>
                <Radio.Button value="1m">1M</Radio.Button>
                <Radio.Button value="6m">6M</Radio.Button>
                <Radio.Button value="1yr">1Y</Radio.Button>
              </Radio.Group>
            </div>
          </div>
        }
        style={{ marginBottom: 24 }}
      >
        {loading ? (
          <div style={{ height: 300, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
            <Spin size="large" />
          </div>
        ) : (
          <div style={{ width: '100%', height: 300 }}>
            <ResponsiveContainer>
              <LineChart
                data={salesData}
                margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                {chartView === 'sales' ? (
                  <YAxis 
                    tickFormatter={(tick) => `$${formatNumberWithCommas(tick)}`}
                  />
                ) : (
                  <YAxis 
                    domain={[20, 40]} 
                    tickFormatter={(tick) => `${formatNumberWithCommas(tick)}%`}
                  />
                )}
                <RechartsTooltip 
                  formatter={(value: number) => {
                    if (chartView === 'sales') {
                      return [`$${formatNumberWithCommas(value)}`, 'Sales'];
                    } else {
                      return [`${formatNumberWithCommas(value)}%`, 'Profit Margin'];
                    }
                  }}
                  labelFormatter={(label: string) => `Date: ${label}`}
                />
                <Legend />
                {chartView === 'sales' ? (
                  <Line 
                    type="monotone" 
                    dataKey="sales" 
                    name="Sales" 
                    stroke="#9370DB" 
                    activeDot={{ r: 8 }} 
                    strokeWidth={2}
                  />
                ) : (
                  <Line 
                    type="monotone" 
                    dataKey="profitMargin" 
                    name="Profit Margin" 
                    stroke="#52c41a" 
                    activeDot={{ r: 8 }} 
                    strokeWidth={2}
                  />
                )}
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </Card>
      
      {/* Main dashboard layout */}
      <Row gutter={[24, 24]} style={{ marginTop: 24 }}>
        {/* Left side - Best and Worst Performing Items */}
        <Col xs={24} md={12}>
          {/* Best and Worst Performing Items Card */}
          <div style={{ justifyContent: 'center', marginTop: 0, marginBottom: 0 }}>
            <Card
              title={
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span>Best and Worst Performing Items</span>
                  <Radio.Group 
                    value={itemsTimeFrame}
                    onChange={handleItemsTimeFrameChange}
                    optionType="button"
                    buttonStyle="solid"
                    size="small"
                  >
                    <Radio.Button value="1d">1D</Radio.Button>
                    <Radio.Button value="7d">7D</Radio.Button>
                    <Radio.Button value="1m">1M</Radio.Button>
                    <Radio.Button value="6m">6M</Radio.Button>
                    <Radio.Button value="1yr">1Y</Radio.Button>
                  </Radio.Group>
                </div>
              }
              style={{ width: '100%' }}
              bodyStyle={{ padding: '24px' }}
            >
            {productsLoading ? (
              <div style={{ height: 400, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
                <Spin size="large" />
              </div>
            ) : (
              <div>
                {/* Top Performers */}
                <div>
                  <Title level={4} style={{ color: '#3f8600', display: 'flex', alignItems: 'center', marginTop: -5, marginBottom: 16 }}>
                    Best Selling Items
                  </Title>
                  <div style={{ marginBottom: 36 }}>
                    {topProducts.map((product, index) => (
                      <Card
                        key={product.id}
                        style={{ marginBottom: 8, borderRadius: 0, border: 'none'}}
                        size="small"
                        className="dashboard-card-item"
                        onClick={() => navigate(`/product/${product.id}`)}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <div>
                            <div style={{ display: 'flex', alignItems: 'center' }}>
                              <strong>{product.name}</strong>
                              <Tag color="blue" style={{ marginLeft: 8, borderRadius: 12, padding: '0 8px' }}>{product.category}</Tag>
                            </div>
                            <div style={{ marginTop: 4 }}>
                              <span>
                                <AntTooltip title="Price">
                                  <InfoCircleOutlined style={{ marginRight: 4 }} />
                                </AntTooltip>
                                ${formatNumberWithCommas(Number(product.price.toFixed(2)))}
                              </span>
                            </div>
                          </div>
                          <div style={{ textAlign: 'right' }}>
                            <div>
                              <strong>${formatNumberWithCommas(Number(product.revenue.toFixed(2)))}</strong>
                              <span style={{ fontSize: '0.85em', color: '#8c8c8c', marginLeft: 4 }}>revenue</span>
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', marginTop: 4 }}>
                              <div style={{ marginRight: 12 }}>
                                <AntTooltip title="Units Sold">
                                  <span>{formatNumberWithCommas(product.quantity)} units</span>
                                </AntTooltip>
                              </div>
                              {product.growth > 0 ? (
                                <span style={{ color: '#3f8600' }}>
                                  <ArrowUpOutlined /> {product.growth}%
                                </span>
                              ) : (
                                <span style={{ color: '#cf1322' }}>
                                  <ArrowDownOutlined /> {Math.abs(product.growth)}%
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                      </Card>
                    ))}
                  </div>
                </div>
    
                {/* Bottom Performers */}
                <div>
                  <Title level={4} style={{ color: '#cf1322', display: 'flex', alignItems: 'center', marginBottom: 16, marginTop: 12 }}>
                    Worst Selling Items 
                  </Title>
                  <div>
                    {bottomProducts.map((product, index) => (
                      <Card
                        key={product.id}
                        style={{ marginBottom: 8, borderRadius: 0, border: 'none'}}
                        size="small"
                        className="dashboard-card-item"
                        onClick={() => navigate(`/product/${product.id}`)}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <div>
                            <div style={{ display: 'flex', alignItems: 'center' }}>
                              <strong>{product.name}</strong>
                              <Tag color="blue" style={{ marginLeft: 8, borderRadius: 12, padding: '0 8px' }}>{product.category}</Tag>
                            </div>
                            <div style={{ marginTop: 4 }}>
                              <span>
                                <AntTooltip title="Price">
                                  <InfoCircleOutlined style={{ marginRight: 4 }} />
                                </AntTooltip>
                                ${formatNumberWithCommas(Number(product.price.toFixed(2)))}
                              </span>
                            </div>
                          </div>
                          <div style={{ textAlign: 'right' }}>
                            <div>
                              <strong>${formatNumberWithCommas(Number(product.revenue.toFixed(2)))}</strong>
                              <span style={{ fontSize: '0.85em', color: '#8c8c8c', marginLeft: 4 }}>revenue</span>
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', marginTop: 4 }}>
                              <div style={{ marginRight: 12 }}>
                                <AntTooltip title="Units Sold">
                                  <span>{formatNumberWithCommas(product.quantity)} units</span>
                                </AntTooltip>
                              </div>
                              {product.growth > 0 ? (
                                <span style={{ color: '#3f8600' }}>
                                  <ArrowUpOutlined /> {product.growth}%
                                </span>
                              ) : (
                                <span style={{ color: '#cf1322' }}>
                                  <ArrowDownOutlined /> {Math.abs(product.growth)}%
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                      </Card>
                    ))}
                  </div>
                </div>
              </div>
            )}
            </Card>
          </div>
        </Col>
        
        {/* Right side - Sales Overview and Competitor Analysis stacked */}
        <Col xs={24} md={12}>
          <Space direction="vertical" style={{ width: '100%' }} size={24}>
            {/* Adaptiv Overview Card */}
            <Card 
              title="Adaptiv Overview" 
              extra={<Button type="link">View All</Button>}
              style={{ width: '100%' }}
            >
              <Statistic
                title="Revenue Increase from Adaptiv"
                value={12750}
                precision={0}
                formatter={(value) => {
                  const numValue = typeof value === 'number' ? value : Number(value);
                  return formatNumberWithCommas(Number(numValue.toFixed(0)));
                }}
                valueStyle={{ color: '#3f8600' }}
                prefix={<DollarOutlined />}
                suffix="/mo"
              />
              <div style={{ marginTop: 16 }}>
                <p><strong>Margin Improvement:</strong> <span style={{ color: '#3f8600' }}><ArrowUpOutlined /> 4.3%</span></p>
                <p><strong>Price Optimization Score:</strong> <span style={{ fontWeight: 'bold' }}>92/100</span></p>
                <p><strong>ROI:</strong> <span style={{ color: '#3f8600' }}>428%</span> (6-month trailing)</p>
              </div>
            </Card>
            
            {/* Competitor Analysis Card */}
            <Card 
              title="Competitor Analysis" 
              extra={<Button type="link">View All</Button>}
              style={{ width: '100%' }}
            >
              <Statistic
                title="Market Position"
                value="Top 15%"
                valueStyle={{ color: '#9370DB' }}
                prefix={<TeamOutlined />}
              />
              <div style={{ marginTop: 16 }}>
                <p>Competitors Tracked: 23</p>
                <p>Price Differential: <span style={{ color: '#cf1322' }}><ArrowDownOutlined /> 5.3%</span></p>
                <p>Feature Parity: 92%</p>
              </div>
            </Card>
          </Space>
        </Col>
      </Row>
      
      {/* Best and Worst Performing Items Card */}
      <div style={{ justifyContent: 'center', marginTop: 24, marginBottom: 24 }}>
      
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} sm={12}>
          <Card 
            title="Recent Price Changes" 
            style={{ height: '100%' }}
          >
            <p>Premium Plan: <span style={{ color: '#3f8600' }}>$149.99 → $169.99</span> (May 1, 2025)</p>
            <p>Basic Plan: <span style={{ color: '#3f8600' }}>$49.99 → $59.99</span> (Apr 15, 2025)</p>
            <p>Enterprise Add-on: <span style={{ color: '#cf1322' }}>$299.99 → $279.99</span> (Apr 5, 2025)</p>
          </Card>
        </Col>
        
        <Col xs={24} sm={12}>
          <Card 
            title="Pricing Opportunities" 
            style={{ height: '100%' }}
          >
            <p><strong>High Priority:</strong> Premium subscription has price elasticity</p>
            <p><strong>Medium Priority:</strong> Bundle discount optimization needed</p>
            <p><strong>Low Priority:</strong> Seasonal promotion planning</p>
          </Card>
        </Col>
      </Row>
    </div>
    </div>
  );
};

export default Dashboard;
