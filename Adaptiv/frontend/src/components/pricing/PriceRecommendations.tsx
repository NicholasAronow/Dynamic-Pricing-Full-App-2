import React, { useState, useEffect } from 'react';
import { 
  Typography, 
  Card, 
  Table, 
  Tag, 
  Space, 
  Button, 
  InputNumber, 
  Radio, 
  Tooltip, 
  Badge, 
  Divider,
  Statistic,
  Row,
  Col
} from 'antd';
import type { RadioChangeEvent, TableProps, TableColumnType } from 'antd';
import { Key } from 'rc-table/lib/interface';
import { 
  ArrowUpOutlined, 
  ArrowDownOutlined, 
  InfoCircleOutlined, 
  DollarOutlined,
  CheckOutlined,
  CloseOutlined,
  EditOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';

const { Title, Text } = Typography;

// Using the same mock product data as in Dashboard
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

// Generate price recommendation data
const generateRecommendationData = (timeFrame: string) => {
  // Helper functions to create varied but deterministic recommendations
  const getVariationMultiplier = (timeFrame: string) => {
    switch (timeFrame) {
      case '1d': return 0.2;
      case '7d': return 0.5;
      case '1m': return 0.8;
      case '6m': return 1.2;
      case '1yr': return 2.0;
      default: return 0.5;
    }
  };

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

  const variationMultiplier = getVariationMultiplier(timeFrame);
  const baseQuantity = getBaseQuantity(timeFrame);
  
  // Create a seed based on the timeframe for consistent randomness
  let seed = timeFrame === '1d' ? 0.2 : 
             timeFrame === '7d' ? 0.3 : 
             timeFrame === '1m' ? 0.4 : 
             timeFrame === '6m' ? 0.5 : 0.6;

  return products.map(product => {
    // Use seed to create pseudo-random but consistent values
    seed = (seed * 9301 + 49297) % 233280;
    const random1 = seed / 233280;
    
    seed = (seed * 9301 + 49297) % 233280;
    const random2 = seed / 233280;
    
    seed = (seed * 9301 + 49297) % 233280;
    const random3 = seed / 233280;

    // Calculate current performance
    const quantity = Math.round(baseQuantity * product.popularity * (1 + (random1 * variationMultiplier - variationMultiplier/2)));
    const revenue = quantity * product.basePrice;
    const profitMargin = 0.3 + (random2 * 0.3);
    const profit = revenue * profitMargin;
    const growthVariance = variationMultiplier * 30;
    const growth = Math.round((random3 * growthVariance) - growthVariance/4);
    
    // Calculate price recommendation
    const demandElasticity = 0.5 + random1 * 1.5; // 0.5 - 2.0 range
    const currentDemandRatio = quantity / baseQuantity;
    
    // Recommended price change based on popularity and current demand
    let priceChangeDirection = 1;
    if (currentDemandRatio > 1.2 && growth > 5) {
      // High demand and positive growth: increase price
      priceChangeDirection = 1;
    } else if (currentDemandRatio < 0.8 || growth < -5) {
      // Low demand or negative growth: decrease price
      priceChangeDirection = -1;
    } else {
      // Stable demand: small adjustment based on profitability
      priceChangeDirection = profitMargin > 0.4 ? -1 : 1;
    }
    
    // Calculate percentage change (1-10%)
    const percentChange = Math.round((1 + random2 * 9) * priceChangeDirection);
    
    // Generate a previous price (slightly different from current to show history)
    const previousPriceVariation = (random2 > 0.5 ? 1 : -1) * (0.02 + random1 * 0.05);
    const previousPrice = Number((product.basePrice * (1 - previousPriceVariation)).toFixed(2));
    
    // Calculate measured impact from the price change
    const priceChangeRatio = product.basePrice / previousPrice;
    const estimatedPreviousQuantity = Math.round(quantity / (priceChangeRatio ** -demandElasticity));
    const previousRevenue = estimatedPreviousQuantity * previousPrice;
    const measuredRevenueDiff = revenue - previousRevenue;
    const measuredRevenueChangePercent = Math.round((measuredRevenueDiff / previousRevenue) * 100);
    const incrementalRevenue = measuredRevenueDiff;
    
    return {
      id: product.id,
      name: product.name,
      category: product.category,
      currentPrice: product.basePrice,
      previousPrice,
      quantity,
      revenue,
      growth,
      profitMargin,
      previousRevenue,
      incrementalRevenue,
      measuredRevenueChangePercent,
      elasticity: demandElasticity.toFixed(2),
      optimizationReason: percentChange > 0 
        ? 'Demand exceeds supply' 
        : percentChange < 0 
          ? 'Increase competitiveness' 
          : 'Maintain market position',
      timeFrame,
      editing: false
    };
  });
};

const PriceRecommendations: React.FC = () => {
  const navigate = useNavigate();
  const [timeFrame, setTimeFrame] = useState<string>('7d');
  const [loading, setLoading] = useState<boolean>(true);
  const [recommendations, setRecommendations] = useState<any[]>([]);
  const [editingRow, setEditingRow] = useState<number | null>(null);
  const [editPrice, setEditPrice] = useState<number | null>(null);
  
  // Calculate summary metrics
  const totalRevenue = recommendations.reduce((sum, item) => sum + item.revenue, 0);
  const netRevenueImpact = recommendations.reduce((sum, item) => sum + item.incrementalRevenue, 0);
  const percentChange = netRevenueImpact !== 0 ? (netRevenueImpact / (totalRevenue - netRevenueImpact)) * 100 : 0;

  // Fetch recommendations
  useEffect(() => {
    setLoading(true);
    // Simulate API call delay
    setTimeout(() => {
      const data = generateRecommendationData(timeFrame);
      setRecommendations(data);
      setLoading(false);
    }, 800);
  }, [timeFrame]);

  // Handle time frame change
  const handleTimeFrameChange = (value: string) => {
    setTimeFrame(value);
  };

  // Handle edit mode for a row
  const startEditing = (record: any) => {
    setEditingRow(record.id);
    setEditPrice(record.recommendedPrice);
  };

  // Cancel editing
  const cancelEditing = () => {
    setEditingRow(null);
    setEditPrice(null);
  };

  // Save edited price
  const saveEditing = (record: any) => {
    if (editPrice !== null) {
      const updatedRecommendations = recommendations.map(item => {
        if (item.id === record.id) {
          const percentChange = Math.round(((editPrice - item.currentPrice) / item.currentPrice) * 100);
          
          // Recalculate projected impact
          const demandElasticity = parseFloat(item.elasticity);
          const projectedQuantityChange = -percentChange * demandElasticity / 100;
          const projectedNewQuantity = Math.round(item.quantity * (1 + projectedQuantityChange));
          const projectedRevenue = projectedNewQuantity * editPrice;
          const revenueDiff = projectedRevenue - item.revenue;
          const revenueChangePercent = Math.round((revenueDiff / item.revenue) * 100);
          
          return {
            ...item,
            recommendedPrice: editPrice,
            percentChange,
            projectedRevenue,
            revenueChangePercent
          };
        }
        return item;
      });
      
      setRecommendations(updatedRecommendations);
    }
    
    setEditingRow(null);
    setEditPrice(null);
  };

  // Table columns
  const columns: TableColumnType<any>[] = [
    {
      title: 'Product',
      dataIndex: 'name',
      key: 'name',
      sorter: (a, b) => a.name.localeCompare(b.name),
      sortDirections: ['ascend', 'descend'] as TableColumnType<any>['sortDirections'],
      render: (text: string) => (
        <div style={{ fontWeight: 500 }}>{text}</div>
      ),
    },
    {
      title: 'Tags',
      dataIndex: 'category',
      key: 'category',
      render: (category: string) => (
        <Tag color="#9370DB" style={{ borderRadius: 12, padding: '0 8px' }}>{category}</Tag>
      ),
      filters: [
        { text: 'Coffee', value: 'Coffee' },
        { text: 'Pastry', value: 'Pastry' },
      ],
      onFilter: (value: Key | boolean, record: any) => record.category === value.toString(),
    },
    {
      title: 'Current Price',
      dataIndex: 'currentPrice',
      key: 'currentPrice',
      sorter: (a, b) => {
        // Primary sort by price
        if (a.currentPrice !== b.currentPrice) {
          return a.currentPrice - b.currentPrice;
        }
        // Tiebreaker by name (alphabetized)
        return a.name.localeCompare(b.name);
      },
      sortDirections: ['ascend', 'descend'] as TableColumnType<any>['sortDirections'],
      render: (text: number) => (
        <div>${text.toFixed(2)}</div>
      ),
    },
    {
      title: 'Performance',
      key: 'performance',
      sorter: (a, b) => {
        // Primary sort by revenue
        if (a.revenue !== b.revenue) {
          return b.revenue - a.revenue;
        }
        // Tiebreaker by name (alphabetized)
        return a.name.localeCompare(b.name);
      },
      sortDirections: ['descend', 'ascend'] as TableColumnType<any>['sortDirections'],
      defaultSortOrder: 'descend',
      render: (text: string, record: any) => (
        <Space direction="vertical" size={1}>
          <div>
            <Text strong>${formatNumberWithCommas(Number(record.revenue.toFixed(2)))}</Text>
            <Text type="secondary" style={{ fontSize: '0.85em', marginLeft: 4 }}>revenue</Text>
          </div>
          <div>
            <Tooltip title="Units Sold">
              <Text>{formatNumberWithCommas(record.quantity)} units</Text>
            </Tooltip>
            <span style={{ marginLeft: 8 }}>
              {record.growth > 0 ? (
                <Text style={{ color: '#3f8600' }}>
                  <ArrowUpOutlined /> {record.growth}%
                </Text>
              ) : (
                <Text style={{ color: '#cf1322' }}>
                  <ArrowDownOutlined /> {Math.abs(record.growth)}%
                </Text>
              )}
            </span>
          </div>
        </Space>
      ),
    },
    {
      title: 'Last Price Change',
      key: 'priceChange',
      sorter: (a, b) => {
        const changeA = Math.abs(a.currentPrice - a.previousPrice);
        const changeB = Math.abs(b.currentPrice - b.previousPrice);
        return changeB - changeA; // Sort by change size descending by default
      },
      sortDirections: ['descend', 'ascend'] as TableColumnType<any>['sortDirections'],
      render: (text: string, record: any) => {
        const priceIncreased = record.currentPrice > record.previousPrice;
        const changeAmount = Math.abs(record.currentPrice - record.previousPrice).toFixed(2);
        const changePercent = Math.round(Math.abs(record.currentPrice - record.previousPrice) / record.previousPrice * 100);
        
        return (
          <Space direction="vertical" size={1}>
            <div>
              <Text style={{ fontSize: '0.9em' }}>
                ${formatNumberWithCommas(Number(record.previousPrice.toFixed(2)))} → <Text strong>${formatNumberWithCommas(Number(record.currentPrice.toFixed(2)))}</Text>
              </Text>
              <Text 
                style={{ 
                  marginLeft: 8, 
                  color: priceIncreased ? '#3f8600' : '#cf1322'
                }}
              >
                {priceIncreased ? '+' : '-'}${formatNumberWithCommas(Number(changeAmount))} ({formatNumberWithCommas(changePercent)}%)
              </Text>
            </div>
            <Text type="secondary" style={{ fontSize: '0.85em' }}>
              <InfoCircleOutlined style={{ marginRight: 4 }} />
              {record.optimizationReason}
            </Text>
          </Space>
        );
      },
    },

    {
      title: 'Measured Impact',
      key: 'impact',
      sorter: (a, b) => a.incrementalRevenue - b.incrementalRevenue,
      sortDirections: ['descend', 'ascend'] as TableColumnType<any>['sortDirections'],
      render: (text: string, record: any) => (
        <Space direction="vertical" size={1}>
          <div>
            <Text type="secondary" style={{ fontSize: '0.85em' }}>Incremental Revenue</Text>
          </div>
          <div>
            <Text strong style={{ color: record.incrementalRevenue > 0 ? '#3f8600' : '#cf1322' }}>
              {record.incrementalRevenue > 0 ? '+' : ''}
              ${formatNumberWithCommas(Number(Math.abs(record.incrementalRevenue).toFixed(2)))}
            </Text>
          </div>
          <div>
            <Text 
              style={{ 
                color: record.measuredRevenueChangePercent > 0 ? '#3f8600' : record.measuredRevenueChangePercent < 0 ? '#cf1322' : 'inherit' 
              }}
            >
              {record.measuredRevenueChangePercent > 0 ? (
                <ArrowUpOutlined />
              ) : record.measuredRevenueChangePercent < 0 ? (
                <ArrowDownOutlined />
              ) : null}
              {' '}
              {record.measuredRevenueChangePercent > 0 ? '+' : ''}{formatNumberWithCommas(record.measuredRevenueChangePercent)}%
            </Text>
          </div>
        </Space>
      ),
    },
  ];

  // Function to format numbers with commas
  const formatNumberWithCommas = (num: number) => {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  };

  return (
    <div>
      <Title level={2}>Price Recommendations</Title>
      <Title level={5} type="secondary" style={{ marginTop: 0 }}>
        Optimize your product pricing strategy with AI-driven insights
      </Title>
      
      {/* Summary Card */}
      <Card style={{ marginTop: 24, marginBottom: 24 }}>
        <Row gutter={24}>
          <Col span={8}>
            <Statistic
              title="Net Revenue Impact"
              value={netRevenueImpact}
              precision={2}
              formatter={(value) => {
                // Handle both number and string cases safely
                const numValue = typeof value === 'number' ? value : Number(value);
                return formatNumberWithCommas(Number(numValue.toFixed(2)));
              }}
              valueStyle={{ color: netRevenueImpact > 0 ? '#3f8600' : netRevenueImpact < 0 ? '#cf1322' : 'inherit' }}
              prefix="$"
            />
            <Text type="secondary">
              {netRevenueImpact > 0 ? 'Increase' : netRevenueImpact < 0 ? 'Decrease' : 'No change'} of {formatNumberWithCommas(Math.abs(Math.round(percentChange * 10) / 10))}%
            </Text>
          </Col>
          <Col span={8}>
            <Statistic
              title="Price Changes"
              value={recommendations.length}
              formatter={(value) => {
                // Handle both number and string cases safely
                const numValue = typeof value === 'number' ? value : Number(value);
                return formatNumberWithCommas(numValue);
              }}
              valueStyle={{ color: '#9370DB' }}
              suffix="products"
            />
          </Col>
          <Col span={8}>
            <Statistic
              title="Analysis Period"
              value={timeFrame === '1d' ? 'Last 24 hours' : 
                     timeFrame === '7d' ? 'Last 7 days' : 
                     timeFrame === '1m' ? 'Last 30 days' : 
                     timeFrame === '6m' ? 'Last 6 months' : 'Last year'}
              valueStyle={{ color: '#1890ff' }}
            />
            <Radio.Group 
              value={timeFrame} 
              onChange={(e: RadioChangeEvent) => handleTimeFrameChange(e.target.value)}
              buttonStyle="solid"
              style={{ marginTop: 8 }}
              size="small"
            >
              <Radio.Button value="1d">1D</Radio.Button>
              <Radio.Button value="7d">7D</Radio.Button>
              <Radio.Button value="1m">1M</Radio.Button>
              <Radio.Button value="6m">6M</Radio.Button>
              <Radio.Button value="1yr">1Y</Radio.Button>
            </Radio.Group>
          </Col>
        </Row>
      </Card>
      
      {/* Recommendations Table */}
      <Card>
        <Table
          columns={columns}
          dataSource={recommendations}
          rowKey="id"
          loading={loading}
          pagination={false}
        />
      </Card>
    </div>
  );
};

export default PriceRecommendations;
