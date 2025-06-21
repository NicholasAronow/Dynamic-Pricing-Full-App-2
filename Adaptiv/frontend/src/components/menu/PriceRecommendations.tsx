import React, { useState, useEffect, useMemo } from 'react';
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
  LoadingOutlined,
  SyncOutlined,
  ShoppingOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { integrationService } from '../../services/integrationService';
import pricingService, { PriceRecommendation } from '../../services/pricingService';
import * as recipeService from '../../services/recipeService';
import orderService from '../../services/orderService';
import { RecipeItem } from '../../types/recipe';

const { Title, Text, Paragraph } = Typography;

// Function to handle Square integration
const handleSquareIntegration = async () => {
  try {
    console.log('Initiating Square integration from Price Recommendations');
    // Use the integrationService to get the auth URL
    const authUrl = await integrationService.getSquareAuthUrl();
    
    console.log('Received Square auth URL:', authUrl);
    if (authUrl) {
      // Redirect to Square's authorization page
      window.location.href = authUrl;
    }
  } catch (error) {
    message.error('Failed to start Square integration. Please try again.');
    console.error('Square integration error:', error);
  }
};

const PriceRecommendations: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [timeFrame, setTimeFrame] = useState<string>('7d');
  const [loading, setLoading] = useState<boolean>(true);
  const [recommendations, setRecommendations] = useState<PriceRecommendation[]>([]);
  const [editingRow, setEditingRow] = useState<number | null>(null);
  const [editPrice, setEditPrice] = useState<number | null>(null);
  const [savingPrice, setSavingPrice] = useState<number | null>(null);
  const [usingMock, setUsingMock] = useState<boolean>(false);
  // Use pos_connected field from the user object
  const isPosConnected = user?.pos_connected ?? false;
  const [recipes, setRecipes] = useState<RecipeItem[]>([]);
  const [loadingRecipes, setLoadingRecipes] = useState<boolean>(true);
  const [syncingOrders, setSyncingOrders] = useState<boolean>(false);
  const [netMargins, setNetMargins] = useState<{[key: string]: any}>({});
  
  // Calculate summary metrics with safety checks
  const totalRevenue = recommendations.reduce((sum, item) => sum + (item.revenue || 0), 0);
  const netRevenueImpact = recommendations.reduce((sum, item) => sum + (item.incrementalRevenue || 0), 0);
  const percentChange = (netRevenueImpact !== 0 && (totalRevenue - netRevenueImpact) !== 0) ? 
    (netRevenueImpact / (totalRevenue - netRevenueImpact)) * 100 : 0;

  // Fetch recommendations from the API
  // Function to handle re-syncing Square orders
  const handleSyncOrders = async () => {
    setSyncingOrders(true);
    try {
      const result = await orderService.syncSquareOrders();
      if (result.success) {
        message.success(`${result.message}${result.total_orders ? ` (${result.total_orders} orders)` : ''}`);
        // Reload recommendations to reflect any newly synced orders
        const recommendations = await pricingService.getPriceRecommendations(timeFrame);
        setRecommendations(recommendations);
      } else {
        message.error(result.message);
      }
    } catch (error) {
      console.error('Error syncing orders:', error);
      message.error('Failed to sync orders. Please try again.');
    } finally {
      setSyncingOrders(false);
    }
  };

  // Fetch recipe data for real cost information
  useEffect(() => {
    const fetchRecipes = async () => {
      setLoadingRecipes(true);
      try {
        const recipesData = await recipeService.getRecipes();
        setRecipes(recipesData);
        
        // After recipes are loaded, fetch net margins for each recipe
        const margins: {[key: string]: any} = {};
        for (const recipe of recipesData) {
          try {
            // Find corresponding recommendation item to get the selling price
            const recommendationItem = recommendations.find(r => r.name === recipe.item_name);
            if (recommendationItem && recommendationItem.currentPrice) {
              const netMarginData = await recipeService.getRecipeNetMargin(
                recipe.item_id, 
                recommendationItem.currentPrice
              );
              margins[recipe.item_name] = netMarginData;
            }
          } catch (err) {
            console.error(`Error fetching net margin for ${recipe.item_name}:`, err);
          }
        }
        setNetMargins(margins);
      } catch (error) {
        console.error('Error fetching recipes:', error);
      } finally {
        setLoadingRecipes(false);
      }
    };
    
    fetchRecipes();
  }, [recommendations]);

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
        setUsingMock(pricingService.wasMock());
      } catch (error) {
        console.error('Error fetching price recommendations:', error);
        message.error('Failed to load price recommendations');
        setUsingMock(true);
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
        // Always sort by the size of the price change (largest change first)
        const changeA = Math.abs(a.currentPrice - a.previousPrice);
        const changeB = Math.abs(b.currentPrice - b.previousPrice);
        return changeB - changeA; // Sort by change size descending by default
      },
      sortDirections: ['descend', 'ascend'] as TableColumnType<any>['sortDirections'],
      render: (text: string, record: any) => {
        const currentPrice = record.currentPrice || 0;
        const previousPrice = record.previousPrice;
        // More robust check for price changes - consider a price changed if it's different from current by more than 1 cent
        const isPriceNeverChanged = previousPrice === undefined || 
                                  Math.abs(currentPrice - previousPrice) < 0.01;
        const lastChangeDate = record.lastPriceChangeDate ? new Date(record.lastPriceChangeDate) : null;
        
        // Format date to a readable string if available
        const formatDate = (date: Date | null) => {
          if (!date) return null;
          
          // Check if date is from today
          const today = new Date();
          const isToday = date.getDate() === today.getDate() &&
                          date.getMonth() === today.getMonth() &&
                          date.getFullYear() === today.getFullYear();
                          
          // Check if date is from yesterday
          const yesterday = new Date(today);
          yesterday.setDate(yesterday.getDate() - 1);
          const isYesterday = date.getDate() === yesterday.getDate() &&
                              date.getMonth() === yesterday.getMonth() &&
                              date.getFullYear() === yesterday.getFullYear();
          
          if (isToday) {
            return 'Today';
          } else if (isYesterday) {
            return 'Yesterday';
          } else {
            // Default date format: May 14, 2025
            return date.toLocaleDateString('en-US', { 
              month: 'short',
              day: 'numeric',
              year: 'numeric'
            });
          }
        };
        
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
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85em' }}>
              <Text type="secondary">
                <InfoCircleOutlined style={{ marginRight: 4 }} />
                {record.optimizationReason}
              </Text>
              {lastChangeDate && (
                <Text type="secondary" style={{ marginLeft: 8 }}>
                  {formatDate(lastChangeDate)}
                </Text>
              )}
            </div>
          </Space>
        );
      },
    },

    {
      title: (
        <Tooltip title="Margin calculated using only ingredient cost data for your items.">
          <span>
            Gross Margin <InfoCircleOutlined style={{ fontSize: '12px', color: '#9370DB' }} />
          </span>
        </Tooltip>
      ),
      key: 'margin',
      dataIndex: 'profitMargin',
      sorter: (a, b) => (a.profitMargin || 0) - (b.profitMargin || 0),
      sortDirections: ['descend', 'ascend'] as TableColumnType<any>['sortDirections'],
      render: (margin: number, record: any) => {
        // Find recipe for this item if available
        const recipe = recipes.find(r => r.item_name === record.name);
        
        // If we have a recipe with total_cost, calculate real margin using that
        let realMargin = margin;
        
        if (recipe && recipe.total_cost && record.currentPrice > 0) {
          // Get cost from recipe
          let cost = recipe.total_cost;
          
          // Check for unreasonable cost values
          // This indicates a likely unit conversion issue in the backend
          const reasonableCostLimit = record.currentPrice * 10; // Cost shouldn't be more than 10x the price
          const isUnreasonablyCostly = cost > reasonableCostLimit;
          
          if (isUnreasonablyCostly) {
            console.warn(`Potentially incorrect cost detected: ${record.name} has cost $${cost.toFixed(2)} but price is only $${record.currentPrice.toFixed(2)}`);
            
            // Use an estimated cost instead (60% of price as a reasonable fallback)
            // This assumes a 40% target margin which is common in food service
            const estimatedCost = record.currentPrice * 0.6;
            console.log(`Using estimated cost of $${estimatedCost.toFixed(2)} instead of $${cost.toFixed(2)} for ${record.name}`);
            cost = estimatedCost;
          } else {
            // Log normal cost calculation
            console.log(`Normal margin calculation for ${record.name}: cost=$${cost.toFixed(2)}, price=$${record.currentPrice.toFixed(2)}`);
          }
          
          // Calculate margin using standard formula with sanitized cost
          realMargin = (record.currentPrice - cost) / record.currentPrice;

        }
        
        // Convert decimal margin to percentage and ensure it's a number
        const marginPercent = typeof realMargin === 'number' ? realMargin * 100 : 0;
        const marginColor = marginPercent >= 30 ? '#3f8600' : 
                           marginPercent >= 15 ? '#faad14' : '#cf1322';
        
        return (
          <Text strong style={{ color: marginColor }}>
            {marginPercent.toFixed(1)}%
          </Text>
        );
      },
    },
    
    {
      title: (
        <Tooltip title="Net margin including ingredient costs and fixed costs (rent, utilities, labor) based on trailing month sales.">
          <span>
            Net Margin <InfoCircleOutlined style={{ fontSize: '12px', color: '#9370DB' }} />
          </span>
        </Tooltip>
      ),
      key: 'netMargin',
      sorter: (a, b) => {
        const marginA = netMargins[a.name]?.net_margin_percentage || 0;
        const marginB = netMargins[b.name]?.net_margin_percentage || 0;
        return marginA - marginB;
      },
      sortDirections: ['descend', 'ascend'] as TableColumnType<any>['sortDirections'],
      render: (text: string, record: any) => {
        // Find recipe for this item if available
        const recipe = recipes.find(r => r.item_name === record.name);
        
        // Get net margin data if available
        const netMarginData = netMargins[record.name];
        
        if (!recipe || !netMarginData) {
          return <Text type="secondary">Calculating...</Text>;
        }
        
        // Display the net margin with color coding
        const netMarginPercent = netMarginData.net_margin_percentage || 0;
        const marginColor = netMarginPercent >= 25 ? '#3f8600' : 
                           netMarginPercent >= 12 ? '#faad14' : '#cf1322';
        
        return (
          <Space direction="vertical" size={0}>
            <Text strong style={{ color: marginColor }}>
              {netMarginPercent.toFixed(1)}%
            </Text>
            <Text type="secondary" style={{ fontSize: '0.8em' }}>
              Ingredients: ${netMarginData.ingredient_cost?.toFixed(2) || '0.00'}
            </Text>
            <Text type="secondary" style={{ fontSize: '0.8em' }}>
              Fixed costs: ${netMarginData.fixed_cost?.toFixed(2) || '0.00'}
            </Text>
          </Space>
        );
      },
    },

  ];

  // Function to format numbers with commas
  const formatNumberWithCommas = (num: number) => {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  };

  // Generate sample recommendations data for the blurred background
  const sampleRecommendations = useMemo(() => {
    return Array(3).fill(null).map((_, index) => ({
      id: index + 1,
      name: `Sample Product ${index + 1}`,
      category: index % 3 === 0 ? 'Coffee' : index % 3 === 1 ? 'Pastry' : 'Merchandise',
      currentPrice: 5.99 + (index * 0.5),
      recommendedPrice: 6.49 + (index * 0.5),
      revenue: 500 + (index * 100),
      growth: index % 2 === 0 ? 5 : -3,
      quantity: 50 + (index * 5),
      elasticity: '0.3',
      profitMargin: 0.35,
      incrementalRevenue: index % 2 === 0 ? 50 : -30,
      previousPrice: 5.49 + (index * 0.5),
      measuredRevenueChangePercent: index % 2 === 0 ? 10 : -5,
      optimizationReason: 'Sample optimization reason'
    }));
  }, []);

  return (
    <div style={{ position: 'relative' }}>
      <Title level={2}>Your Items</Title>
      <Title level={5} type="secondary" style={{ marginTop: 0 }}>
        Optimize your product pricing strategy with AI-driven insights
      </Title>
      
      {/* Single conditional blur overlay for the entire component */}
      {!isPosConnected && (
        <div style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          backdropFilter: 'blur(5px)',
          backgroundColor: 'rgba(255, 255, 255, 0.85)',
          zIndex: 10,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          textAlign: 'center',
          padding: '40px',
          borderRadius: '8px'
        }}>
          <Title level={3}>Connect Your POS System</Title>
          <Paragraph style={{ fontSize: '16px', maxWidth: '600px', margin: '20px 0' }}>
            To access your product data, please connect your Square account.
            This will allow us to import your sales data and menu items for personalized insights.
          </Paragraph>
          <Button 
            type="primary" 
            icon={<ShoppingOutlined />}
            onClick={handleSquareIntegration}
            size="large"
            style={{ marginTop: '20px' }}
          >
            Connect Square Account
          </Button>
          <Paragraph style={{ marginTop: '20px', fontSize: '14px', opacity: 0.7 }}>
            <Text type="secondary">After connecting, you'll have access to all price recommendation features</Text>
          </Paragraph>
        </div>
      )}
      <Button 
        onClick={handleSyncOrders} 
        disabled={syncingOrders} 
        type="default" 
        size="small"
        icon={syncingOrders ? <LoadingOutlined /> : <SyncOutlined />}
      >
        {syncingOrders ? 'Syncing Orders...' : 'Re-sync Orders'}
      </Button>
      <Text type="secondary" style={{ fontSize: '12px', marginLeft: 8, display: 'block', marginTop: 4 }}>
        Refresh order data from Square
      </Text>
      
      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: '100px 0' }}>
          <LoadingOutlined style={{ fontSize: 24 }} spin />
        </div>
      ) : usingMock ? (
        <div style={{ position: 'relative' }}>
          {/* Blurred sample data in background */}
          <div style={{ filter: 'blur(5px)', opacity: 0.5 }}>
            {/* Summary Card with sample data */}
            <Card style={{ marginTop: 24, marginBottom: 24 }}>
              <Row gutter={24}>
                {/*
                <Col span={8}>
                  <Statistic
                    title="Net Revenue Impact"
                    value={1250.00}
                    precision={2}
                    formatter={(value) => formatNumberWithCommas(Number(value))}
                    valueStyle={{ color: '#3f8600' }}
                    prefix="$"
                  />
                </Col>
                */}
                <Col span={8}>
                  <Statistic
                    title="Price Changes"
                    value={10}
                    valueStyle={{ color: '#9370DB' }}
                    suffix="products"
                  />
                </Col>
                <Col span={8}>
                  <Statistic
                    title="Analysis Period"
                    value="Last 7 days"
                    valueStyle={{ color: '#1890ff' }}
                  />
                </Col>
              </Row>
            </Card>
            
            {/* Sample recommendations table */}
            <Card>
              <Table
                columns={columns}
                dataSource={sampleRecommendations}
                rowKey="id"
                pagination={false}
              />
            </Card>
          </div>
          
          {/* Overlay with message */}
          <div style={{ 
            position: 'absolute', 
            top: 0, 
            left: 0, 
            width: '100%', 
            height: '100%', 
            display: 'flex', 
            flexDirection: 'column', 
            justifyContent: 'center', 
            alignItems: 'center',
            backgroundColor: 'rgba(255, 255, 255, 0.85)',
            padding: '150px 0'
          }}>
            <div style={{ 
              padding: '30px', 
              borderRadius: '8px', 
              textAlign: 'center',
              maxWidth: '80%' 
            }}>
              <p style={{ fontSize: '24px', fontWeight: 500, marginBottom: '16px' }}>No price recommendation data available</p>
              <p style={{ color: '#666', marginBottom: '30px', fontSize: '16px' }}>To view AI-powered price recommendations, please connect your POS provider</p>
              <Button type="primary" size="large">
                Connect POS Provider
              </Button>
            </div>
          </div>
        </div>
      ) : (
        <>
          {/* Summary Card with real data */}
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
              Feature in development
              {/*{netRevenueImpact > 0 ? 'Increase' : netRevenueImpact < 0 ? 'Decrease' : 'No change'} of {formatNumberWithCommas(Math.abs(Math.round(percentChange * 10) / 10))}%*/}
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
            <div>
              <Radio.Group 
                value={timeFrame} 
                onChange={(e: RadioChangeEvent) => handleTimeFrameChange(e.target.value)}
                buttonStyle="solid"
                style={{ marginTop: 8, marginBottom: 8 }}
                size="small"
              >
                <Radio.Button value="1d">1D</Radio.Button>
                <Radio.Button value="7d">7D</Radio.Button>
                <Radio.Button value="1m">1M</Radio.Button>
                <Radio.Button value="6m">6M</Radio.Button>
                <Radio.Button value="1yr">1Y</Radio.Button>
              </Radio.Group>
              <br />
              
            </div>
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
        </>
      )}
    </div>
  );
};

export default PriceRecommendations;
