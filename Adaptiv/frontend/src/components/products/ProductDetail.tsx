import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import {
  Typography,
  Card,
  Row,
  Col,
  Statistic,
  Tag,
  Space,
  Radio,
  DatePicker,
  Table,
  Divider,
  Tabs,
  Progress,
  Spin
} from 'antd';
import { 
  ArrowUpOutlined, ArrowDownOutlined, DollarOutlined, AreaChartOutlined,
  LineChartOutlined, ClockCircleOutlined, BarChartOutlined, 
  ShopOutlined, InfoCircleOutlined, RiseOutlined, TeamOutlined, CalendarOutlined
} from '@ant-design/icons';
import moment from 'moment';
import { 
  ResponsiveContainer, LineChart, Line, AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Legend 
} from 'recharts';

const { Title, Text } = Typography;
const { TabPane } = Tabs;

// Mock data generator functions
const generateSalesData = (productId: string, timeFrame: string) => {
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
      step = 7;
      unit = 'days';
      break;
    default: // 1yr
      numPoints = 12;
      format = 'MMM YYYY';
      dateFormat = 'YYYY-MM-01';
      step = 1;
      unit = 'months';
  }
  
  // Generate data points
  for (let i = numPoints - 1; i >= 0; i--) {
    const date = moment(now).subtract(i * step, unit);
    
    // Base value with some randomness
    const baseValue = 500 + Math.random() * 300; 
    
    // Add some time-based patterns
    let modifier = 1;
    if (timeFrame === '1d') {
      // More sales during business hours
      const hour = date.hour();
      if (hour >= 9 && hour <= 17) {
        modifier = 1.5;
      } else if (hour < 6 || hour > 21) {
        modifier = 0.5;
      }
    } else {
      // Weekend vs weekday patterns for longer timeframes
      const dayOfWeek = date.day();
      if (dayOfWeek === 0 || dayOfWeek === 6) { // Weekend
        modifier = 1.4;
      }
    }
    
    const sales = Math.round(baseValue * modifier);
    const cost = sales * 0.6; // 60% COGS
    const profit = sales - cost;
    const margin = (profit / sales) * 100;
    
    data.push({
      date: date.format(format),
      fullDate: date.format(dateFormat),
      sales,
      units: Math.round(sales / 4.5), // Assuming average price of $4.50
      profit: Math.round(profit),
      margin: parseFloat(margin.toFixed(1))
    });
  }
  
  return data;
};

// Generate hourly sales data for a specific day
const generateIntradayData = (productId: string, date: moment.Moment) => {
  const data = [];
  
  // Generate 24 hours of data
  for (let hour = 0; hour < 24; hour++) {
    const timePoint = moment(date).hour(hour).minute(0);
    
    // Base value with more variance throughout the day
    let baseValue = 20 + Math.random() * 15;
    
    // Add typical daily patterns
    if (hour >= 7 && hour <= 9) { // Morning rush
      baseValue *= 2.5;
    } else if (hour >= 11 && hour <= 13) { // Lunch rush
      baseValue *= 2.2;
    } else if (hour >= 16 && hour <= 18) { // After work
      baseValue *= 1.8;
    } else if (hour >= 22 || hour <= 5) { // Late night/early morning
      baseValue *= 0.3;
    }
    
    const sales = Math.round(baseValue);
    const units = Math.round(sales / 4.5);
    
    data.push({
      hour: timePoint.format('HH:mm'),
      sales,
      units
    });
  }
  
  return data;
};

// Generate price elasticity data
const generateElasticityData = (productId: string) => {
  const data = [];
  
  // Generate data points for prices between $3.00 and $6.00
  for (let price = 300; price <= 600; price += 25) {
    const displayPrice = price / 100;
    
    // Calculate demand with elasticity model
    // Higher elasticity at higher prices
    let elasticity = -1.2;
    if (price > 500) elasticity = -1.8;
    else if (price > 400) elasticity = -1.5;
    
    // Base demand at $4.00 (reference price)
    const basePrice = 400;
    const baseDemand = 200;
    
    // Simplified constant elasticity demand function
    const demand = baseDemand * Math.pow(price/basePrice, elasticity);
    
    // Revenue at this price point
    const revenue = demand * displayPrice;
    
    // Cost per unit (assuming 60% COGS)
    const costPerUnit = displayPrice * 0.6;
    const totalCost = demand * costPerUnit;
    const profit = revenue - totalCost;
    
    // Optimal price indicator
    let isOptimal = false;
    if (price === 450) { // Set $4.50 as the optimal price for this example
      isOptimal = true;
    }
    
    data.push({
      price: displayPrice,
      demand: Math.round(demand),
      revenue: Math.round(revenue),
      profit: Math.round(profit),
      isOptimal
    });
  }
  
  return data;
};

// Generate competitor data
const generateCompetitorData = (productId: string) => {
  // Simulate data for coffee product
  return [
    {
      name: 'Starbucks',
      price: 4.95,
      difference: '+10%',
      location: '0.3 miles away',
      logo: '🟢' // Placeholder for logo
    },
    {
      name: 'Local Roastery',
      price: 4.25,
      difference: '-5.6%',
      location: '0.8 miles away',
      logo: '☕' // Placeholder for logo
    },
    {
      name: 'Coffee Bean',
      price: 4.75,
      difference: '+5.6%',
      location: '1.2 miles away',
      logo: '🟤' // Placeholder for logo
    }
  ];
};

// Mock product data
const getProductData = (productId: string) => {
  // In a real app, this would fetch from an API
  return {
    id: productId,
    name: "Signature Latte",
    category: "Beverages",
    basePrice: 4.50,
    currentPrice: 4.50,
    weeklyUnits: 834,
    weeklySales: 3753,
    costToMake: 2.70,
    margin: 40,
    description: "Our premium signature latte with house-made syrup.",
    image: "https://via.placeholder.com/150" // Placeholder image
  };
};

// Utility function to format numbers with commas that works with various types
const formatNumberWithCommas = (num: any): string => {
  // Handle arrays (ValueType in Recharts can sometimes be an array)
  if (Array.isArray(num)) {
    return formatNumberWithCommas(num[0]); // Format the first element
  }
  // Handle strings
  if (typeof num === 'string') {
    return Number(num).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  }
  // Handle numbers
  if (typeof num === 'number') {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  }
  // Fallback
  return String(num);
};

const ProductDetail: React.FC = () => {
  const { productId } = useParams<{ productId: string }>();
  const [activeTab, setActiveTab] = useState<string>('summary');
  const [salesTimeFrame, setSalesTimeFrame] = useState<string>('7d');
  const [selectedDate, setSelectedDate] = useState<moment.Moment>(moment().subtract(1, 'day'));
  const [salesData, setSalesData] = useState<any[]>([]);
  const [intradayData, setIntradayData] = useState<any[]>([]);
  const [elasticityData, setElasticityData] = useState<any[]>([]);
  const [competitorData, setCompetitorData] = useState<any[]>([]);
  const [weeklyData, setWeeklyData] = useState<any[]>([]);
  const [forecastData, setForecastData] = useState<any[]>([]);
  const [marketPositionData, setMarketPositionData] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [product, setProduct] = useState<any>(null);

  useEffect(() => {
    // Simulate API loading
    setLoading(true);
    
    setTimeout(() => {
      if (productId) {
        const productData = getProductData(productId);
        setProduct(productData);
        setSalesData(generateSalesData(productId, salesTimeFrame));
        setIntradayData(generateIntradayData(productId, selectedDate));
        setElasticityData(generateElasticityData(productId));
        setCompetitorData(generateCompetitorData(productId));
        setLoading(false);
      }
    }, 1000);
  }, [productId, selectedDate]); // Removed salesTimeFrame from dependency array
  
  // Handle changing the time frame for sales data
  const handleTimeFrameChange = (e: any) => {
    // Prevent default form submission behavior
    e.preventDefault();
    e.stopPropagation();
    
    // Update timeframe immediately without loading indicator
    const newTimeFrame = e.target.value;
    setSalesTimeFrame(newTimeFrame);
    
    // Generate new data for the selected time frame without triggering a reload
    const newData = generateSalesData(productId || '1', newTimeFrame);
    setSalesData(newData);
  };
  
  const handleDateChange = (date: moment.Moment | null) => {
    if (date) {
      setSelectedDate(date);
      
      // Update intraday data immediately when date changes
      setIntradayData(generateIntradayData(productId || '1', date));
    }
  };
  
  if (loading || !product) {
    return (
      <div style={{ height: '100vh', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
        <Spin size="large" />
      </div>
    );
  }
  
  return (
    <div>
      {/* Product Header Card */}
      <Card style={{ marginBottom: 24, marginTop: 24 }}>
        <Row gutter={24}>
          <Col xs={24} md={8}>
            <div style={{ display: 'flex', alignItems: 'center' }}>
              <img 
                src={product.image} 
                alt={product.name} 
                style={{ width: 80, height: 80, marginRight: 16, borderRadius: 8 }}
              />
              <div>
                <Title level={3} style={{ margin: 0 }}>{product.name}</Title>
                <Tag color="blue" style={{ marginTop: 8, borderRadius: 12 }}>
                  {product.category}
                </Tag>
              </div>
            </div>
          </Col>
          
          <Col xs={24} md={5}>
            <Statistic
              title="Current Price"
              value={product.currentPrice}
              precision={2}
              formatter={(value) => {
                const numValue = typeof value === 'number' ? value : Number(value);
                return '$' + formatNumberWithCommas(Number(numValue.toFixed(2)));
              }}
              valueStyle={{ color: 'rgba(0, 0, 0, 0.85)' }}
            />
          </Col>
          
          <Col xs={24} md={5}>
            <Statistic
              title="Margin"
              value={product.margin}
              formatter={(value) => {
                const numValue = typeof value === 'number' ? value : Number(value);
                return formatNumberWithCommas(numValue) + '%';
              }}
              valueStyle={{ color: 'rgba(0, 0, 0, 0.85)' }}
            />
          </Col>
          
          <Col xs={24} md={6}>
            <Statistic
              title="Weekly Units"
              value={product.weeklyUnits}
              formatter={(value) => {
                const numValue = typeof value === 'number' ? value : Number(value);
                return formatNumberWithCommas(numValue);
              }}
              valueStyle={{ color: 'rgba(0, 0, 0, 0.85)' }}
              suffix="units"
            />
          </Col>
        </Row>
      </Card>
      
      {/* Tab-based content */}
      <Tabs defaultActiveKey="summary" onChange={(key) => setActiveTab(key)} size="large">
        {/* Summary Tab */}
        <Tabs.TabPane 
          tab={<span><InfoCircleOutlined /> Summary</span>}
          key="summary"
        >
          {/* Weekly Sales and Intraday Sales Row */}
          <Row gutter={24}>
            <Col xs={24} lg={12}>
              {/* Weekly Sales Table */}
              <Card 
                title={<span><CalendarOutlined /> Weekly Sales</span>}
                style={{ marginBottom: 24 }}
              >
                <Table
                  dataSource={[
                    { day: 'Monday', units: 45, revenue: 224.55 },
                    { day: 'Tuesday', units: 38, revenue: 189.62 },
                    { day: 'Wednesday', units: 52, revenue: 259.48 },
                    { day: 'Thursday', units: 65, revenue: 324.35 },
                    { day: 'Friday', units: 87, revenue: 434.13 },
                    { day: 'Saturday', units: 103, revenue: 513.97 },
                    { day: 'Sunday', units: 72, revenue: 359.28 }
                  ]}
                  pagination={false}
                  columns={[
                    {
                      title: 'Day',
                      dataIndex: 'day',
                      key: 'day'
                    },
                    {
                      title: 'Units Sold',
                      dataIndex: 'units',
                      key: 'units',
                      render: (units) => <span>{formatNumberWithCommas(units)}</span>
                    },
                    {
                      title: 'Revenue',
                      dataIndex: 'revenue',
                      key: 'revenue',
                      render: (revenue) => <span>${formatNumberWithCommas(Number(revenue.toFixed(2)))}</span>
                    }
                  ]}
                  summary={(pageData) => {
                    let totalUnits = 0;
                    let totalRevenue = 0;
                    pageData.forEach(({ units, revenue }) => {
                      totalUnits += units;
                      totalRevenue += revenue;
                    });
                    return (
                      <Table.Summary.Row>
                        <Table.Summary.Cell index={0}><strong>Total</strong></Table.Summary.Cell>
                        <Table.Summary.Cell index={1}>
                          <strong>{formatNumberWithCommas(totalUnits)}</strong>
                        </Table.Summary.Cell>
                        <Table.Summary.Cell index={2}>
                          <strong>${formatNumberWithCommas(Number(totalRevenue.toFixed(2)))}</strong>
                        </Table.Summary.Cell>
                      </Table.Summary.Row>
                    );
                  }}
                  size="small"
                />
              </Card>
            </Col>
            
            <Col xs={24} lg={12}>
              {/* Intraday Sales Card */}
              <Card 
                title={
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span><ClockCircleOutlined /> Hourly Sales</span>
                    <DatePicker 
                      value={selectedDate} 
                      onChange={handleDateChange} 
                      allowClear={false}
                      disabledDate={(current) => current && current > moment().endOf('day')}
                      onClick={(e) => e.stopPropagation()}
                    />
                  </div>
                }
                style={{ marginBottom: 24 }}
              >
                <div style={{ width: '100%', height: 300 }}>
                  <ResponsiveContainer>
                    <BarChart
                      data={intradayData}
                      margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="hour" />
                      <YAxis 
                        orientation="left" 
                        stroke="#666" 
                        tickFormatter={(value) => `$${formatNumberWithCommas(value)}`}
                      />
                      <RechartsTooltip 
                        formatter={(value) => {
                          // Safe approach to format any value type
                          const numValue = typeof value === 'number' ? value : Number(value);
                          return [`$${formatNumberWithCommas(numValue)}`, 'Sales'];
                        }} 
                      />
                      <Legend />
                      <Bar 
                        dataKey="sales" 
                        name="Sales" 
                        fill="#666" 
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </Card>
            </Col>
          </Row>
          
          {/* Row for Price Elasticity and Competitors */}
          <Row gutter={24}>
            <Col xs={24} lg={12}>
              {/* Price Elasticity Card */}
              <Card 
                title={<span><BarChartOutlined /> Price Elasticity Analysis</span>}
                style={{ marginBottom: 24 }}
              >
                <div style={{ width: '100%', height: 250 }}>
                  <ResponsiveContainer>
                    <LineChart
                      data={elasticityData}
                      margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis 
                        dataKey="price" 
                        label={{ value: 'Price ($)', position: 'insideBottomRight', offset: -10 }}
                        tickFormatter={(value) => `$${formatNumberWithCommas(value)}`}
                      />
                      <YAxis 
                        yAxisId="left" 
                        orientation="left" 
                        stroke="#9370DB" 
                        tickFormatter={(value) => formatNumberWithCommas(value)}
                      />
                      <YAxis 
                        yAxisId="right" 
                        orientation="right" 
                        stroke="#52c41a"
                        tickFormatter={(value) => `$${formatNumberWithCommas(value)}`}
                      />
                      <RechartsTooltip 
                        formatter={(value, name) => {
                          // Safe approach to format any value type
                          const numValue = typeof value === 'number' ? value : Number(value);
                          if (name === 'Demand') return [formatNumberWithCommas(numValue), 'Units'];
                          return [`$${formatNumberWithCommas(numValue)}`, name];
                        }} 
                      />
                      <Legend />
                      <Line 
                        yAxisId="left"
                        type="monotone" 
                        dataKey="demand" 
                        name="Demand" 
                        stroke="#9370DB" 
                        strokeWidth={2}
                        dot={(props: any) => {
                          const { cx, cy, payload } = props;
                          return payload.isOptimal ? (
                            <svg x={cx - 6} y={cy - 6} width={12} height={12} fill="#f5222d">
                              <circle cx={6} cy={6} r={6} />
                            </svg>
                          ) : (
                            <svg x={cx - 4} y={cy - 4} width={0} height={0} fill="#9370DB">
                              <circle cx={4} cy={4} r={4} />
                            </svg>
                          );
                        }}
                      />
                      <Line 
                        yAxisId="right"
                        type="monotone" 
                        dataKey="profit" 
                        name="Profit" 
                        stroke="#52c41a" 
                        strokeWidth={2}
                        dot={(props: any) => {
                          const { cx, cy, payload } = props;
                          return payload.isOptimal ? (
                            <svg x={cx - 6} y={cy - 6} width={12} height={12} fill="#f5222d">
                              <circle cx={6} cy={6} r={6} />
                            </svg>
                          ) : (
                            <svg x={cx - 4} y={cy - 4} width={0} height={0} fill="#52c41a">
                              <circle cx={4} cy={4} r={4} />
                            </svg>
                          );
                        }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
                <div style={{ marginTop: 8 }}>
                  <Text type="secondary" style={{ fontSize: '12px' }}>
                    <strong>The red dot</strong> indicates the optimal price point that maximizes profit while maintaining 
                    reasonable demand. Current elasticity: <strong>-1.5</strong>
                  </Text>
                </div>
              </Card>
            </Col>
            
            <Col xs={24} lg={12}>
              {/* Competitor Snapshot Card */}
              <Card 
                title={<span><ShopOutlined /> Competitor Snapshot</span>}
                style={{ marginBottom: 24 }}
              >
                <Row gutter={[16, 16]}>
                  <Col span={8}>
                    <Statistic
                      title="Market Low"
                      value={3.99}
                      precision={2}
                      prefix="$"
                      valueStyle={{ color: 'rgba(0, 0, 0, 0.85)' }}
                    />
                  </Col>
                  <Col span={8}>
                    <Statistic
                      title="Our Price"
                      value={product.currentPrice}
                      precision={2}
                      prefix="$"
                      valueStyle={{ fontWeight: 'bold' }}
                    />
                  </Col>
                  <Col span={8}>
                    <Statistic
                      title="Market High"
                      value={6.99}
                      precision={2}
                      prefix="$"
                      valueStyle={{ color: 'rgba(0, 0, 0, 0.85)' }}
                    />
                  </Col>
                </Row>
                
                <Divider>Top Competitors</Divider>
                
                <Table
                  dataSource={[
                    { name: 'Java Junction', logo: '☕', price: 4.99, difference: '-$0.00' },
                    { name: 'Bean Scene', logo: '🌱', price: 5.49, difference: '+$0.50' },
                    { name: 'Brew Haven', logo: '🍵', price: 4.49, difference: '-$0.50' }
                  ]}
                  pagination={false}
                  size="small"
                  columns={[
                    {
                      title: 'Competitor',
                      dataIndex: 'name',
                      key: 'name',
                      render: (text, record) => (
                        <div style={{ display: 'flex', alignItems: 'center' }}>
                          <span style={{ fontSize: '18px', marginRight: 8 }}>{record.logo}</span>
                          <span>{text}</span>
                        </div>
                      )
                    },
                    {
                      title: 'Price',
                      dataIndex: 'price',
                      key: 'price',
                      render: (price) => `$${price.toFixed(2)}`
                    },
                    {
                      title: 'Difference',
                      dataIndex: 'difference',
                      key: 'difference',
                      render: (diff) => {
                        if (diff.startsWith('+')) {
                          return <span style={{ color: 'rgba(0, 0, 0, 0.85)' }}>{diff}</span>;
                        } else {
                          return <span style={{ color: 'rgba(0, 0, 0, 0.85)' }}>{diff}</span>;
                        }
                      }
                    }
                  ]}
                />
              </Card>
            </Col>
          </Row>
        </Tabs.TabPane>
        
        {/* Demand Tab */}
        <Tabs.TabPane 
          tab={<span><RiseOutlined /> Demand</span>}
          key="demand"
        >
          {/* Sales Performance Card */}
          <Card 
            title={
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span><LineChartOutlined /> Sales Performance</span>
                <Radio.Group 
                  value={salesTimeFrame}
                  onChange={handleTimeFrameChange}
                  optionType="button"
                  buttonStyle="solid"
                  size="small"
                >
                  <Radio.Button value="1d" onClick={(e: React.MouseEvent) => e.stopPropagation()}>1D</Radio.Button>
                  <Radio.Button value="7d" onClick={(e: React.MouseEvent) => e.stopPropagation()}>7D</Radio.Button>
                  <Radio.Button value="1m" onClick={(e: React.MouseEvent) => e.stopPropagation()}>1M</Radio.Button>
                  <Radio.Button value="6m" onClick={(e: React.MouseEvent) => e.stopPropagation()}>6M</Radio.Button>
                  <Radio.Button value="1yr" onClick={(e: React.MouseEvent) => e.stopPropagation()}>1Y</Radio.Button>
                </Radio.Group>
              </div>
            }
            style={{ marginBottom: 24 }}
          >
            <div id="sales-chart-container" style={{ width: '100%', height: 300, position: 'relative' }}>
              <ResponsiveContainer>
                <AreaChart
                  data={salesData}
                  margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <RechartsTooltip 
                    formatter={(value: number) => [`$${value}`, 'Sales']}
                    labelFormatter={(label: string) => `Date: ${label}`}
                  />
                  <Legend />
                  <Area 
                    type="monotone" 
                    dataKey="sales" 
                    name="Sales" 
                    stroke="#666" 
                    fill="#666" 
                    fillOpacity={0.3}
                  />
                  <Area 
                    type="monotone" 
                    dataKey="profit" 
                    name="Profit" 
                    stroke="#666" 
                    fill="#666" 
                    fillOpacity={0.3}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </Card>
          
          {/* Sales Forecast Card */}
          <Card
            title={<span><AreaChartOutlined /> Sales Forecast</span>}
            style={{ marginBottom: 24 }}
          >
            <Row gutter={[24, 24]}>
              <Col xs={24} sm={8}>
                <Statistic
                  title="Forecast (Next Month)"
                  value={2750}
                  precision={0}
                  prefix="$"
                  valueStyle={{ color: 'rgba(0, 0, 0, 0.85)' }}
                />
              </Col>
              <Col xs={24} sm={8}>
                <Statistic
                  title="Growth Rate"
                  value={12.4}
                  precision={1}
                  suffix="%"
                  valueStyle={{ color: 'rgba(0, 0, 0, 0.85)' }}
                  prefix={<ArrowUpOutlined />}
                />
              </Col>
              <Col xs={24} sm={8}>
                <Statistic
                  title="Forecast Accuracy"
                  value={92}
                  suffix="%"
                  valueStyle={{ color: 'rgba(0, 0, 0, 0.85)' }}
                />
              </Col>
            </Row>
            
            <Divider />
            
            <div style={{ width: '100%', height: 300 }}>
              <ResponsiveContainer>
                <LineChart
                  data={[
                    { month: 'Jan', actual: 1200, forecast: null },
                    { month: 'Feb', actual: 1350, forecast: null },
                    { month: 'Mar', actual: 1500, forecast: null },
                    { month: 'Apr', actual: 1750, forecast: null },
                    { month: 'May', actual: 2100, forecast: null },
                    { month: 'Jun', actual: 2450, forecast: null },
                    { month: 'Jul', actual: null, forecast: 2750 },
                    { month: 'Aug', actual: null, forecast: 3050 },
                    { month: 'Sep', actual: null, forecast: 3400 }
                  ]}
                  margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" />
                  <YAxis />
                  <RechartsTooltip />
                  <Legend />
                  <Line 
                    type="monotone" 
                    dataKey="actual" 
                    name="Actual Sales" 
                    stroke="#666" 
                    strokeWidth={2}
                    dot={{ r: 5 }}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="forecast" 
                    name="Forecast" 
                    stroke="#666" 
                    strokeWidth={2}
                    strokeDasharray="5 5"
                    dot={{ r: 5 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </Tabs.TabPane>
        
        {/* Competitors Tab */}
        <Tabs.TabPane 
          tab={<span><ShopOutlined /> Competitors</span>}
          key="competitors"
        >
          {/* Market Overview Card */}
          <Card
            title={<span><ShopOutlined /> Market Overview</span>}
            style={{ marginBottom: 24 }}
          >
            <Row gutter={[24, 24]}>
              <Col xs={24} sm={12} md={6}>
                <Statistic
                  title="Market Average"
                  value={4.99}
                  precision={2}
                  prefix="$"
                  valueStyle={{ color: 'rgba(0, 0, 0, 0.85)' }}
                />
              </Col>
              <Col xs={24} sm={12} md={6}>
                <Statistic
                  title="Market Low"
                  value={3.99}
                  precision={2}
                  prefix="$"
                  valueStyle={{ color: 'rgba(0, 0, 0, 0.85)' }}
                />
              </Col>
              <Col xs={24} sm={12} md={6}>
                <Statistic
                  title="Market High"
                  value={6.99}
                  precision={2}
                  prefix="$"
                  valueStyle={{ color: 'rgba(0, 0, 0, 0.85)' }}
                />
              </Col>
              <Col xs={24} sm={12} md={6}>
                <Statistic
                  title="Competitors"
                  value={12}
                  valueStyle={{ color: 'rgba(0, 0, 0, 0.85)' }}
                />
              </Col>
            </Row>
            
            <Divider>Your Market Position</Divider>
            
            <div style={{ padding: '20px 0' }}>
              <div style={{ position: 'relative', height: 10, background: 'linear-gradient(to right, #666, #666, #666)', borderRadius: 4 }}>
                <div style={{ position: 'absolute', left: 0, bottom: -20, color: '#666' }}>
                  <strong>$3.99</strong>
                </div>
                <div style={{ position: 'absolute', right: 0, bottom: -20, color: '#666' }}>
                  <strong>$6.99</strong>
                </div>
                <div 
                  style={{ 
                    position: 'absolute', 
                    left: '40%', 
                    bottom: -40, 
                    transform: 'translateX(-50%)',
                    color: '#666'
                  }}
                >
                  <div style={{ position: 'relative' }}>
                    <ArrowUpOutlined style={{ fontSize: 16, position: 'absolute', top: -18, left: '50%', transform: 'translateX(-50%)' }} />
                    <strong>Your Price: $4.99</strong>
                  </div>
                </div>
              </div>
            </div>
          </Card>
          
          {/* Competitor Data Card */}
          <Card
            title={<span><ShopOutlined /> Competitor Pricing Data</span>}
            style={{ marginBottom: 24 }}
          >
            <Table
              dataSource={[
                { name: 'Coffee Bean', logo: '☕', price: 4.29, difference: '-$0.70', updated: '2 hours ago', distance: '0.2 mi' },
                { name: 'Java Junction', logo: '☕', price: 4.99, difference: '$0.00', updated: '1 day ago', distance: '0.5 mi' },
                { name: 'Bean Scene', logo: '🌱', price: 5.49, difference: '+$0.50', updated: '5 hours ago', distance: '0.8 mi' },
                { name: 'Brew Haven', logo: '🍵', price: 4.49, difference: '-$0.50', updated: '3 hours ago', distance: '1.2 mi' },
                { name: 'Morning Cup', logo: '☕', price: 3.99, difference: '-$1.00', updated: '12 hours ago', distance: '1.5 mi' },
                { name: 'Star Coffee', logo: '⭐', price: 5.99, difference: '+$1.00', updated: '1 hour ago', distance: '1.8 mi' },
                { name: 'The Roastery', logo: '🔥', price: 6.49, difference: '+$1.50', updated: '6 hours ago', distance: '2.0 mi' },
                { name: 'Cafe Delight', logo: '✨', price: 5.29, difference: '+$0.30', updated: '2 days ago', distance: '2.3 mi' },
                { name: 'Brew & Co', logo: '🍵', price: 6.99, difference: '+$2.00', updated: '8 hours ago', distance: '2.8 mi' }
              ]}
              pagination={{ pageSize: 6 }}
              columns={[
                {
                  title: 'Competitor',
                  dataIndex: 'name',
                  key: 'name',
                  render: (text, record) => (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
                      <span style={{ fontSize: '18px', marginRight: 8 }}>{record.logo}</span>
                      <span>{text}</span>
                    </div>
                  )
                },
                {
                  title: 'Price',
                  dataIndex: 'price',
                  key: 'price',
                  sorter: (a, b) => a.price - b.price,
                  render: (price) => `$${price.toFixed(2)}`
                },
                {
                  title: 'Difference',
                  dataIndex: 'difference',
                  key: 'difference',
                  sorter: (a, b) => parseFloat(a.difference.replace('$', '')) - parseFloat(b.difference.replace('$', '')),
                  render: (diff) => {
                    if (diff.startsWith('+')) {
                      return <span style={{ color: '#cf1322' }}>{diff}</span>;
                    } else if (diff.startsWith('-')) {
                      return <span style={{ color: '#3f8600' }}>{diff}</span>;
                    } else {
                      return <span>{diff}</span>;
                    }
                  }
                },
                {
                  title: 'Last Updated',
                  dataIndex: 'updated',
                  key: 'updated'
                },
                {
                  title: 'Distance',
                  dataIndex: 'distance',
                  key: 'distance',
                  sorter: (a, b) => parseFloat(a.distance) - parseFloat(b.distance)
                }
              ]}
            />
          </Card>
        </Tabs.TabPane>
      </Tabs>
    </div>
  );
};

export default ProductDetail;
