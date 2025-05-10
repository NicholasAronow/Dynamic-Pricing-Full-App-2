import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../../services/api';
import {
  Typography,
  Card,
  Row,
  Col,
  Statistic,
  Tag,
  Space,
  Radio,
  RadioChangeEvent,
  DatePicker,
  Table,
  Divider,
  Tabs,
  Progress,
  Spin,
  Alert,
  Button
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

// Import our API services
import itemService, { Item, PriceHistory } from '../../services/itemService';
import competitorService, { CompetitorItem } from '../../services/competitorService';
import analyticsService, { PriceElasticityData, CompetitorData } from '../../services/analyticsService';

const { Title, Text } = Typography;
const { TabPane } = Tabs;

// Legacy mock data generator functions - these will be used as fallbacks
// when API data isn't available yet
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
const generateElasticityData = (productId: string): PriceElasticityData[] => {
  const data: PriceElasticityData[] = [];
  
  // Generate data points for prices between $3.00 and $6.00
  for (let price = 3.0; price <= 6.0; price += 0.5) {
    // Simple elasticity model: as price increases, demand decreases
    // with a non-linear relationship
    const baseDemand = 100;
    const priceElasticity = -1.5; // More elastic than -1
    
    // Apply elasticity formula: % change in demand = elasticity * % change in price
    const basePrice = 4.5;
    const pctPriceChange = (price - basePrice) / basePrice;
    const pctDemandChange = priceElasticity * pctPriceChange;
    
    // Calculate actual demand value
    const sales_volume = baseDemand * (1 + pctDemandChange);
    
    // Calculate revenue
    const revenue = price * sales_volume;
    
    data.push({
      price,
      sales_volume,
      revenue
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
    current_price: 4.50,
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
  
  let value: number;
  
  // Convert to number
  if (typeof num === 'string') {
    value = Number(num);
  } else if (typeof num === 'number') {
    value = num;
  } else {
    // Fallback
    return String(num);
  }
  
  // Round to 2 decimal places to avoid floating point issues
  const roundedValue = Math.round(value * 100) / 100;
  
  // Split into whole and decimal parts
  const parts = roundedValue.toString().split('.');
  
  // Add commas to the whole part
  parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  
  // Combine whole and decimal parts (if any)
  return parts.length > 1 ? parts.join('.') : parts[0];
};

const ProductDetail: React.FC = () => {
  const { productId } = useParams<{ productId: string }>();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<string>('summary');
  const [salesTimeFrame, setSalesTimeFrame] = useState<string>('7d');
  const [selectedDate, setSelectedDate] = useState<moment.Moment>(moment().subtract(1, 'day'));
  const [salesData, setSalesData] = useState<any[]>([]);
  const [intradayData, setIntradayData] = useState<any[]>([]);
  const [elasticityData, setElasticityData] = useState<PriceElasticityData[]>([]);
  const [competitorData, setCompetitorData] = useState<CompetitorItem[]>([]);
  const [weeklyData, setWeeklyData] = useState<any[]>([]);
  const [forecastData, setForecastData] = useState<any[]>([]);
  const [forecastMetrics, setForecastMetrics] = useState<any>({nextMonthForecast: 0, growthRate: 0, forecastAccuracy: 0});
  const [totalWeeklyUnits, setTotalWeeklyUnits] = useState<number>(0);
  const [totalWeeklyRevenue, setTotalWeeklyRevenue] = useState<number>(0);
  const [marketData, setMarketData] = useState<CompetitorData | null>(null);
  const [marketPositionData, setMarketPositionData] = useState<{
    marketLow: number;
    marketHigh: number;
    marketAverage: number;
    ourPrice: number;
    ourPricePosition: number;
    averagePosition: number;
  } | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [product, setProduct] = useState<Item | null>(null);
  const [priceHistory, setPriceHistory] = useState<PriceHistory[]>([]);

  // Function to set market position from API data or calculate it if needed
  const setMarketPositionFromData = (product: Item, marketData: any) => {
    if (!product || !marketData) {
      setMarketPositionData(null);
      return;
    }

    setMarketPositionData({
      marketLow: marketData.marketStats.low,
      marketHigh: marketData.marketStats.high,
      marketAverage: marketData.marketStats.average,
      ourPrice: product.current_price,
      ourPricePosition: marketData.ourPosition,
      averagePosition: marketData.marketStats.averagePosition
    });
  };

  // Fallback calculation in case we need to calculate market position from raw competitor data
  const calculateMarketPosition = (product: Item, competitors: any[]) => {
    if (!product || !competitors || competitors.length === 0) {
      // If no data, set null or default values
      setMarketPositionData(null);
      return;
    }

    const competitorPrices = competitors.map(comp => comp.price || 0);
    const allPrices = [...competitorPrices, product.current_price];
    const minPrice = Math.min(...allPrices);
    const maxPrice = Math.max(...allPrices);
    
    // Calculate average market price (excluding our product)
    const avgMarketPrice = competitorPrices.reduce((sum, price) => sum + price, 0) / competitorPrices.length;
    
    // Calculate position percentage (0-100%)
    const priceRange = maxPrice - minPrice;
    const ourPricePosition = priceRange > 0 
      ? ((product.current_price - minPrice) / priceRange) * 100
      : 50;
      
    // Calculate average position on a scale of 1-10
    const avgPosition = priceRange > 0
      ? ((avgMarketPrice - minPrice) / priceRange * 9) + 1
      : 5;
    
    setMarketPositionData({
      marketLow: minPrice,
      marketHigh: maxPrice,
      marketAverage: avgMarketPrice,
      ourPrice: product.current_price,
      ourPricePosition: ourPricePosition,
      averagePosition: avgPosition
    });
  };

  useEffect(() => {
    const fetchProductData = async () => {
      try {
        setLoading(true);
        setError(null);
        
        if (!productId) {
          setError('Product ID is required');
          setLoading(false);
          return;
        }

        // Convert string productId to number
        const numericProductId = parseInt(productId, 10);
        
        if (isNaN(numericProductId)) {
          setError('Invalid product ID');
          setLoading(false);
          return;
        }

        // Fetch product details
        const productData = await itemService.getItem(numericProductId);
        setProduct(productData);
        
        // Fetch price history
        const history = await itemService.getPriceHistory(numericProductId);
        setPriceHistory(history);
        
        try {
          // Fetch competitor data using our updated service method
          console.log('Fetching similar competitors for item:', numericProductId);
          const marketData = await competitorService.getSimilarCompetitors(numericProductId);
          
          if (marketData && marketData.competitors) {
            console.log('Successfully received market data with competitors:', marketData);
            // Set competitor data from the response
            setCompetitorData(marketData.competitors);
            // Set market position directly from the API data
            setMarketPositionFromData(productData, marketData);
          } else {
            throw new Error('No competitors found in market data');
          }
        } catch (error) {
          console.error('Error with similar competitors endpoint:', error);
          // Use the original method as fallback
          console.log('Falling back to basic competitor data');
          const competitorItems = await competitorService.getCompetitorItemsByItemId(numericProductId);
          setCompetitorData(competitorItems);
          if (competitorItems.length > 0) {
            // Calculate market position from raw competitor data as fallback
            calculateMarketPosition(productData, competitorItems);
          }
        }
        
        // Fetch or generate sales data
        try {
          // Fetch real sales data
          console.log('Fetching sales data for item:', numericProductId);
          const realSalesData = await analyticsService.getItemSalesData(numericProductId, salesTimeFrame);
          setSalesData(realSalesData);
          
          // Fetch weekly sales data
          console.log('Fetching weekly sales data for item:', numericProductId);
          const weekData = await analyticsService.getItemWeeklySales(numericProductId);
          setWeeklyData(weekData);
          
          // Calculate totals for weekly data
          const totalUnits = weekData.reduce((sum: number, day: any) => sum + day.units, 0);
          const totalRevenue = weekData.reduce((sum: number, day: any) => sum + day.revenue, 0);
          setTotalWeeklyUnits(totalUnits);
          setTotalWeeklyRevenue(totalRevenue);
          
          // Fetch or generate hourly (intraday) data
          console.log('Fetching hourly data for item:', numericProductId);
          try {
            // Convert selectedDate to string format if needed by the API
            const dateString = selectedDate.format('YYYY-MM-DD');
            const hourlySales = await analyticsService.getItemHourlySales(numericProductId, dateString);
            setIntradayData(hourlySales);
          } catch (err) {
            console.error('Failed to fetch hourly data, falling back to mock data', err);
            setIntradayData(generateIntradayData(productId || '1', selectedDate));
          }
          
          // Fetch or generate price elasticity data
          try {
            console.log('Fetching elasticity data for item:', numericProductId);
            const elasticityResult = await analyticsService.getPriceElasticity(numericProductId);
            setElasticityData(elasticityResult);
          } catch (err) {
            console.error('Failed to fetch elasticity data, falling back to mock data', err);
            setElasticityData(generateElasticityData(productId || '1'));
          }
          
        } catch (err) {
          console.error('Failed to fetch sales data, falling back to mock data', err);
          // Fallback to mock data
          const mockSalesData = generateSalesData(productId || '1', salesTimeFrame);
          setSalesData(mockSalesData);
          
          // Generate mock weekly data
          const mockWeeklyData = [
            { key: '1', day: 'Monday', units: 125, revenue: 750 },
            { key: '2', day: 'Tuesday', units: 145, revenue: 870 },
            { key: '3', day: 'Wednesday', units: 165, revenue: 990 },
            { key: '4', day: 'Thursday', units: 180, revenue: 1080 },
            { key: '5', day: 'Friday', units: 210, revenue: 1260 },
            { key: '6', day: 'Saturday', units: 230, revenue: 1380 },
            { key: '7', day: 'Sunday', units: 190, revenue: 1140 }
          ];
          setWeeklyData(mockWeeklyData);
          
          // Calculate mock totals
          const totalUnits = mockWeeklyData.reduce((sum, day) => sum + day.units, 0);
          const totalRevenue = mockWeeklyData.reduce((sum, day) => sum + day.revenue, 0);
          setTotalWeeklyUnits(totalUnits);
          setTotalWeeklyRevenue(totalRevenue);
          
          // Generate mock intraday data
          setIntradayData(generateIntradayData(productId || '1', selectedDate));
          
          // Generate mock elasticity data
          setElasticityData(generateElasticityData(productId || '1'));
        }
        
        setLoading(false);
      } catch (err) {
        console.error('Error fetching product data:', err);
        setError('Failed to load product data. Please try again.');
        setLoading(false);
      }
    };
    
    fetchProductData();
  }, [productId, selectedDate]);
  
  // Handle changing the time frame for sales data
  const handleTimeFrameChange = async (e: RadioChangeEvent) => {
    // Prevent default form submission behavior
    e.preventDefault();
    e.stopPropagation();
    
    // Update timeframe immediately without loading indicator
    const newTimeFrame = e.target.value;
    setSalesTimeFrame(newTimeFrame);
    
    try {
      // Fetch real sales data for the selected time frame
      const numericProductId = parseInt(productId || '1', 10);
      const realSalesData = await analyticsService.getItemSalesData(numericProductId, newTimeFrame);
      setSalesData(realSalesData);
    } catch (err) {
      console.error('Failed to fetch real sales data for time frame, falling back to mock data', err);
      // Fallback to mock data only if API fails
      const newData = generateSalesData(productId || '1', newTimeFrame);
      setSalesData(newData);
    }
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
          
          <Col xs={24} md={4}>
            <Statistic
              title="Current Price"
              value={product.current_price}
              precision={2}
              formatter={(value) => {
                const numValue = typeof value === 'number' ? value : Number(value);
                return '$' + formatNumberWithCommas(Number(numValue.toFixed(2)));
              }}
              valueStyle={{ color: 'rgba(0, 0, 0, 0.85)' }}
            />
          </Col>
          
          <Col xs={24} md={4}>
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
          
          <Col xs={24} md={4}>
            <Statistic
              title="Weekly Units"
              value={totalWeeklyUnits}
              formatter={(value) => {
                const numValue = typeof value === 'number' ? value : Number(value);
                return formatNumberWithCommas(numValue);
              }}
              valueStyle={{ color: 'rgba(0, 0, 0, 0.85)' }}
              suffix="units"
            />
          </Col>
          
          <Col xs={24} md={4}>
            <Statistic
              title="Weekly Revenue"
              value={totalWeeklyRevenue}
              formatter={(value) => {
                const numValue = typeof value === 'number' ? value : Number(value);
                return '$' + formatNumberWithCommas(numValue);
              }}
              valueStyle={{ color: 'rgba(0, 0, 0, 0.85)' }}
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
                  dataSource={weeklyData}
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
                      value={marketPositionData ? marketPositionData.marketLow : 0}
                      precision={2}
                      prefix="$"
                      valueStyle={{ color: 'rgba(0, 0, 0, 0.85)' }}
                    />
                  </Col>
                  <Col span={8}>
                    <Statistic
                      title="Our Price"
                      value={product.current_price}
                      precision={2}
                      prefix="$"
                      valueStyle={{ fontWeight: 'bold' }}
                    />
                  </Col>
                  <Col span={8}>
                    <Statistic
                      title="Market High"
                      value={marketPositionData ? marketPositionData.marketHigh : 0}
                      precision={2}
                      prefix="$"
                      valueStyle={{ color: 'rgba(0, 0, 0, 0.85)' }}
                    />
                  </Col>
                </Row>
                
                <Divider>Top Competitors</Divider>
                
                <Table
                  dataSource={competitorData.map((competitor, index) => {
                    // Get the competitor name (handle both API response formats)
                    const competitorName = 'name' in competitor 
                      ? (competitor.name as string) 
                      : competitor.competitor_name;
                    
                    // Calculate price difference
                    const difference = competitor.price - (product?.current_price || 0);
                    const formattedDiff = difference > 0 ? 
                      `+$${Math.abs(difference).toFixed(2)}` : 
                      `-$${Math.abs(difference).toFixed(2)}`;
                    
                    return {
                      key: index,
                      name: competitorName,
                      logo: '☕', // Simple coffee icon for all competitors
                      price: competitor.price,
                      difference: formattedDiff
                    };
                  }).slice(0, 5)} // Show top 5 competitors
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
                          return <span style={{ color: '#cf1322' }}>{diff}</span>; // They're more expensive (red)
                        } else if (diff.startsWith('-$0.00')) {
                          return <span style={{ color: '#888' }}>$0.00</span>; // Same price (gray)
                        } else {
                          return <span style={{ color: '#3f8600' }}>{diff}</span>; // They're cheaper (green)
                        }
                      }
                    }
                  ]}
                  locale={{ emptyText: 'No competitor data available' }}
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
                  value={forecastMetrics.nextMonthForecast}
                  precision={0}
                  prefix="$"
                  valueStyle={{ color: 'rgba(0, 0, 0, 0.85)' }}
                />
              </Col>
              <Col xs={24} sm={8}>
                <Statistic
                  title="Growth Rate"
                  value={forecastMetrics.growthRate}
                  precision={1}
                  suffix="%"
                  valueStyle={{ color: forecastMetrics.growthRate >= 0 ? '#3f8600' : '#cf1322' }}
                  prefix={forecastMetrics.growthRate >= 0 ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
                />
              </Col>
              <Col xs={24} sm={8}>
                <Statistic
                  title="Forecast Accuracy"
                  value={forecastMetrics.forecastAccuracy}
                  suffix="%"
                  valueStyle={{ color: forecastMetrics.forecastAccuracy > 90 ? '#3f8600' : forecastMetrics.forecastAccuracy > 80 ? '#d48806' : '#cf1322' }}
                />
              </Col>
            </Row>
            
            <Divider />
            
            <div style={{ width: '100%', height: 300 }}>
              <ResponsiveContainer>
                <LineChart
                  data={forecastData}
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
                  value={marketPositionData ? marketPositionData.marketAverage.toFixed(2) : '0.00'}
                  precision={2}
                  prefix="$"
                  valueStyle={{ color: 'rgba(0, 0, 0, 0.85)' }}
                />
              </Col>
              <Col xs={24} sm={12} md={6}>
                <Statistic
                  title="Market Low"
                  value={marketPositionData ? marketPositionData.marketLow.toFixed(2) : '0.00'}
                  precision={2}
                  prefix="$"
                  valueStyle={{ color: 'rgba(0, 0, 0, 0.85)' }}
                />
              </Col>
              <Col xs={24} sm={12} md={6}>
                <Statistic
                  title="Market High"
                  value={marketPositionData ? marketPositionData.marketHigh.toFixed(2) : '0.00'}
                  precision={2}
                  prefix="$"
                  valueStyle={{ color: 'rgba(0, 0, 0, 0.85)' }}
                />
              </Col>
              <Col xs={24} sm={12} md={6}>
                <Statistic
                  title="Competitors"
                  value={competitorData ? competitorData.length : 0}
                  valueStyle={{ color: 'rgba(0, 0, 0, 0.85)' }}
                />
              </Col>
            </Row>
            
            <Divider>Relative Market Position</Divider>
            
            <div style={{ padding: '80px 0 80px' }}>
              <div style={{ position: 'relative', height: 10, background: 'linear-gradient(to right, #f0f0f0, #d9d9d9, #bfbfbf)', borderRadius: 4 }}>
                {marketPositionData && (
                  <>
                    {/* Our price dot */}
                    <div
                      style={{
                        position: 'absolute',
                        left: `${marketPositionData.ourPricePosition}%`,
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
                    
                    {/* Market average dot with hover effect */}
                    <div style={{ position: 'relative' }}>
                      <div
                        style={{
                          position: 'absolute',
                          left: `${((marketPositionData.averagePosition - 1) / 9) * 100}%`,
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
                          left: `${((marketPositionData.averagePosition - 1) / 9) * 100}%`,
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
                        Market Average: ${marketPositionData.marketAverage.toFixed(2)}
                      </div>
                    </div>
                    
                    {/* Scale markings - showing actual prices instead of 1-10 */}
                    <div 
                      style={{
                        position: 'absolute',
                        left: '0%',
                        bottom: -20,
                        color: '#666',
                        fontSize: '12px',
                        fontWeight: 'bold',
                        transform: 'translateX(-50%)'
                      }}
                    >
                      ${marketPositionData ? marketPositionData.marketLow.toFixed(2) : '0.00'}
                    </div>
                    <div
                      style={{
                        position: 'absolute',
                        left: '100%',
                        bottom: -20,
                        color: '#666',
                        fontSize: '12px',
                        fontWeight: 'bold',
                        transform: 'translateX(-50%)'
                      }}
                    >
                      ${marketPositionData ? marketPositionData.marketHigh.toFixed(2) : '0.00'}
                    </div>
                    
                    {/* Our price marker */}
                    <div 
                      style={{ 
                        position: 'absolute', 
                        left: `${marketPositionData.ourPricePosition}%`,
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
                      <div style={{ fontWeight: 'bold' }}>Your Price: ${marketPositionData.ourPrice.toFixed(2)}</div>
                    </div>
                  </>
                )}
              </div>
            </div>
            
            <Text type="secondary" style={{ display: 'block' }}>
              This chart shows the relative price positioning in the market range, with the market low and high prices displayed on the ends of the scale.
              Your price and the market average are positioned proportionally between these extremes.
            </Text>
          </Card>
          
          {/* Competitor Data Card */}
          <Card
            title={<span><ShopOutlined /> Competitor Pricing Data</span>}
            style={{ marginBottom: 24 }}
          >
            <Table
              dataSource={competitorData.map((competitor, index) => {
                // Get the competitor name (handle both API response formats)
                const competitorName = 'name' in competitor 
                  ? (competitor.name as string) 
                  : competitor.competitor_name;
                  
                // Calculate price difference
                const difference = competitor.price - (product?.current_price || 0);
                const formattedDiff = difference === 0
                  ? '$0.00'
                  : difference > 0
                    ? `+$${Math.abs(difference).toFixed(2)}` 
                    : `-$${Math.abs(difference).toFixed(2)}`;
                
                // Format update time - using updated_at property
                const getRelativeTimeString = (timestamp: string): string => {
                  const date = new Date(timestamp);
                  const now = new Date();
                  const diffMs = now.getTime() - date.getTime();
                  const diffHrs = diffMs / (1000 * 60 * 60);
                  
                  if (diffHrs < 1) return 'Just now';
                  if (diffHrs < 2) return '1 hour ago';
                  if (diffHrs < 24) return `${Math.floor(diffHrs)} hours ago`;
                  if (diffHrs < 48) return '1 day ago';
                  return `${Math.floor(diffHrs / 24)} days ago`;
                };
                
                // Calculate a relative distance based on index (simulated data)
                const distance = ((index + 1) * 0.3).toFixed(1) + ' mi';
                
                return {
                  key: index,
                  name: competitorName,
                  logo: '', // Coffee emoji for all competitors
                  price: competitor.price,
                  difference: formattedDiff,
                  updated: getRelativeTimeString(competitor.updated_at),
                  distance: distance
                };
              })}
              pagination={{ pageSize: 6 }}
              columns={[
                {
                  title: 'Competitor',
                  dataIndex: 'name',
                  key: 'name',
                  render: (text, record) => (
                    <div style={{ display: 'flex', alignItems: 'center' }}>
                      <span style={{ fontSize: '18px', marginRight: 8 }}>{record.logo}</span>
                      <span style={{ fontWeight: 'bold' }}>{text}</span>
                    </div>
                  )
                },
                {
                  title: 'Price',
                  dataIndex: 'price',
                  key: 'price',
                  render: (price: number) => <span>${price.toFixed(2)}</span>,
                  sorter: (a: any, b: any) => a.price - b.price
                },
                {
                  title: 'Diff',
                  dataIndex: 'difference',
                  key: 'difference',
                  render: (diff: string) => {
                    let color = 'black';
                    if (diff.includes('+')) color = '#cf1322'; // Red for higher prices
                    if (diff.includes('-')) color = '#3f8600'; // Green for lower prices
                    return <span style={{ color, fontWeight: 'bold' }}>{diff}</span>
                  },
                  sorter: (a: any, b: any) => {
                    // Extract numeric values for sorting
                    const getNumericValue = (str: string): number => {
                      const val = parseFloat(str.replace(/[^0-9.-]+/g, ''));
                      return str.includes('-') ? -val : val; // Make negative if it has a minus
                    };
                    return getNumericValue(a.difference) - getNumericValue(b.difference);
                  }
                },
                {
                  title: 'Last Updated',
                  dataIndex: 'updated',
                  key: 'updated',
                  sorter: (a: any, b: any) => {
                    // Approximate sorting based on relative time strings
                    const timeValue = (str: string): number => {
                      if (str === 'Just now') return 0;
                      const match = str.match(/(\d+)\s+(\w+)/); // Extract number and unit
                      if (!match) return 0;
                      
                      const num = parseInt(match[1]);
                      const unit = match[2];
                      
                      if (unit.includes('hour')) return num;
                      if (unit.includes('day')) return num * 24;
                      return 0;
                    };
                    return timeValue(a.updated) - timeValue(b.updated);
                  }
                },
                {
                  title: 'Distance',
                  dataIndex: 'distance',
                  key: 'distance',
                  sorter: (a: any, b: any) => {
                    const distA = parseFloat(a.distance.split(' ')[0]);
                    const distB = parseFloat(b.distance.split(' ')[0]);
                    return distA - distB;
                  }
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
