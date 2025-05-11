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
  Col,
  message
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
  EditOutlined,
  LoadingOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import pricingService, { PriceRecommendation } from '../../services/pricingService';

const { Title, Text } = Typography;

const PriceRecommendations: React.FC = () => {
  const navigate = useNavigate();
  const [timeFrame, setTimeFrame] = useState<string>('7d');
  const [loading, setLoading] = useState<boolean>(true);
  const [recommendations, setRecommendations] = useState<PriceRecommendation[]>([]);
  const [editingRow, setEditingRow] = useState<number | null>(null);
  const [editPrice, setEditPrice] = useState<number | null>(null);
  const [savingPrice, setSavingPrice] = useState<number | null>(null);
  
  // Calculate summary metrics with safety checks
  const totalRevenue = recommendations.reduce((sum, item) => sum + (item.revenue || 0), 0);
  const netRevenueImpact = recommendations.reduce((sum, item) => sum + (item.incrementalRevenue || 0), 0);
  const percentChange = (netRevenueImpact !== 0 && (totalRevenue - netRevenueImpact) !== 0) ? 
    (netRevenueImpact / (totalRevenue - netRevenueImpact)) * 100 : 0;

  // Fetch recommendations from the API
  useEffect(() => {
    const fetchRecommendations = async () => {
      setLoading(true);
      try {
        let data = await pricingService.getPriceRecommendations(timeFrame);
        console.log('Raw API data received:', data);
        
        // Ensure both quantity and quantitySold properties exist on each item
        if (data && data.length > 0) {
          // Ensure each item has the required properties
          data = data.map(item => {
            // Create a properly typed object
            const processedItem: PriceRecommendation = {
              ...item,
              quantity: item.quantity || 0
            };
            
            // Add the quantitySold property without TypeScript errors
            (processedItem as any).quantitySold = item.quantity || 0;
            
            return processedItem;
          });
          
          console.log('===== UNITS DATA DEBUG =====');
          data.forEach((item, index) => {
            console.log(`Item ${index} (${item.name}) - quantity:`, item.quantity, 
              '- quantitySold:', item.quantity,
              '- types:', typeof item.quantity, '/', typeof item.quantity);
          });
          console.log('========================');
        }
        
        setRecommendations(data);
      } catch (error) {
        console.error('Error fetching price recommendations:', error);
        message.error('Failed to load price recommendations');
      } finally {
        setLoading(false);
      }
    };
    
    fetchRecommendations();
  }, [timeFrame]);

  // Get unique categories for filtering
  const getUniqueCategories = () => {
    if (!recommendations.length) return [];
    
    // Get all categories
    const categories = recommendations.map(item => item.category);
    
    // Create a unique set using Array.filter for broader compatibility
    const uniqueCategories = categories.filter((value, index, self) => 
      self.indexOf(value) === index
    );
    
    return uniqueCategories.map(category => ({ text: category, value: category }));
  };

  // Handle time frame change
  const handleTimeFrameChange = (value: string) => {
    setTimeFrame(value);
  };

  // Handle edit mode for a row
  const startEditing = (record: PriceRecommendation) => {
    setEditingRow(record.id);
    setEditPrice(record.recommendedPrice || calculateRecommendedPrice(record));
  };

  // Calculate a recommended price based on performance data
  const calculateRecommendedPrice = (record: PriceRecommendation): number => {
    // Simple algorithm based on growth and profitability
    const elasticity = parseFloat(record.elasticity);
    let percentChange = 0;
    
    if (record.growth > 10 && record.profitMargin >= 0.3) {
      // High growth + good margin: recommend price increase
      percentChange = Math.min(5, Math.round(record.growth / 3));
    } else if (record.growth < -5 || record.profitMargin < 0.2) {
      // Negative growth or low margin: recommend price decrease
      percentChange = Math.max(-8, Math.round(record.growth / 2));
    } else {
      // Stable: small adjustment based on margin
      percentChange = record.profitMargin > 0.4 ? 2 : -2;
    }
    
    const newPrice = record.currentPrice * (1 + percentChange / 100);
    return Number(newPrice.toFixed(2));
  };

  // Cancel editing
  const cancelEditing = () => {
    setEditingRow(null);
    setEditPrice(null);
  };

  // Save edited price
  const saveEditing = async (record: PriceRecommendation) => {
    if (editPrice !== null) {
      setSavingPrice(record.id);
      
      // Calculate metrics for the UI update
      const percentChange = Math.round(((editPrice - record.currentPrice) / record.currentPrice) * 100);
      const demandElasticity = parseFloat(record.elasticity);
      const projectedQuantityChange = -percentChange * demandElasticity / 100;
      const projectedNewQuantity = Math.round(record.quantity * (1 + projectedQuantityChange));
      const projectedRevenue = projectedNewQuantity * editPrice;
      const revenueDiff = projectedRevenue - record.revenue;
      const revenueChangePercent = Math.round((revenueDiff / record.revenue) * 100);
      
      // Apply the price change using the service
      try {
        const success = await pricingService.applyRecommendation(record.id, editPrice);
        
        if (success) {
          // Update local state with the new price
          const updatedRecommendations = recommendations.map(item => {
            if (item.id === record.id) {
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
          message.success(`Price for ${record.name} updated to $${editPrice}`);
        } else {
          message.error('Failed to update price. Please try again.');
        }
      } catch (error) {
        console.error('Error saving price:', error);
        message.error('Error updating price');
      } finally {
        setSavingPrice(null);
        setEditingRow(null);
        setEditPrice(null);
      }
    } else {
      setEditingRow(null);
      setEditPrice(null);
    }
  };

  // Table columns
  const columns: TableColumnType<any>[] = [
    {
      title: 'Product',
      dataIndex: 'name',
      key: 'name',
      sorter: (a, b) => a.name.localeCompare(b.name),
      sortDirections: ['ascend', 'descend'] as TableColumnType<any>['sortDirections'],
      render: (text: string, record: PriceRecommendation) => (
        <div 
          style={{ fontWeight: 500, cursor: 'pointer' }} 
          onClick={() => navigate(`/product/${record.id}`)}
        >
          {text}
        </div>
      ),
    },
    {
      title: 'Tags',
      dataIndex: 'category',
      key: 'category',
      render: (category: string, record: PriceRecommendation) => (
        <Tag 
          color="#9370DB" 
          style={{ borderRadius: 12, padding: '0 8px', cursor: 'pointer' }}
          onClick={() => navigate(`/product/${record.id}`)}
        >
          {category}
        </Tag>
      ),
      filters: getUniqueCategories(),
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
      render: (text: number | undefined) => (
        <div>${typeof text === 'number' ? text.toFixed(2) : '0.00'}</div>
      ),
    },
    {
      title: 'Performance',
      key: 'performance',
      sorter: (a: any, b: any) => {
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
            <Text strong>${formatNumberWithCommas(Number((record.revenue || 0).toFixed(2)))}</Text>
            <Text type="secondary" style={{ fontSize: '0.85em', marginLeft: 4 }}>revenue</Text>
          </div>
          <div>
            {/* <Tooltip title="Units Sold"> */}
            {/* <Text>{formatNumberWithCommas(record.quantity !== undefined ? record.quantity : 0)} units</Text> */}
            {/* </Tooltip> */}
            <span style={{ marginLeft: 8 }}>
              {(record.growth || 0) > 0 ? (
                <Text style={{ color: '#3f8600' }}>
                  <ArrowUpOutlined /> {record.growth || 0}%
                </Text>
              ) : (
                <Text style={{ color: '#cf1322' }}>
                  <ArrowDownOutlined /> {Math.abs(record.growth || 0)}%
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
      sorter: (a: any, b: any) => {
        const changeA = Math.abs(a.currentPrice - a.previousPrice);
        const changeB = Math.abs(b.currentPrice - b.previousPrice);
        return changeB - changeA; // Sort by change size descending by default
      },
      sortDirections: ['descend', 'ascend'] as TableColumnType<any>['sortDirections'],
      render: (text: string, record: any) => {
        const currentPrice = record.currentPrice || 0;
        const previousPrice = record.previousPrice;
        const isPriceNeverChanged = previousPrice === 0 || previousPrice === undefined;
        
        // If price has never been changed, display a special message
        if (isPriceNeverChanged) {
          return (
            <Space direction="vertical" size={1}>
              <div>
                <Text strong>${formatNumberWithCommas(Number(currentPrice.toFixed(2)))}</Text>
              </div>
              <Text type="secondary" style={{ fontSize: '0.85em' }}>
                <InfoCircleOutlined style={{ marginRight: 4 }} />
                No previous price changes
              </Text>
            </Space>
          );
        }
        
        // Normal case: price has been changed before
        const priceIncreased = currentPrice > previousPrice;
        const changeAmount = Math.abs(currentPrice - previousPrice).toFixed(2);
        const changePercent = Math.round(Math.abs(currentPrice - previousPrice) / previousPrice * 100);
        
        return (
          <Space direction="vertical" size={1}>
            <div>
              <Text style={{ fontSize: '0.9em' }}>
                ${formatNumberWithCommas(Number(previousPrice.toFixed(2)))} → <Text strong>${formatNumberWithCommas(Number(currentPrice.toFixed(2)))}</Text>
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
              ${formatNumberWithCommas(Number(Math.abs(record.incrementalRevenue || 0).toFixed(2)))}
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
          onRow={(record) => ({
            onClick: () => navigate(`/product/${record.id}`),
            style: { cursor: 'pointer' }
          })}
        />
      </Card>
    </div>
  );
};

export default PriceRecommendations;
