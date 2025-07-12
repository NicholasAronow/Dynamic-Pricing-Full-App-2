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
import { ShimmerPriceRecommendations } from '../../components/common/ShimmerLoaders';
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
  // Function to handle re-syncing Square orders with background task
  const handleSyncOrders = async () => {
    setSyncingOrders(true);
    
    try {
      // Start the background sync task
      const syncStart = await orderService.syncSquareOrders(false);
      
      if (!syncStart.success || !syncStart.task_id) {
        message.error(syncStart.message);
        setSyncingOrders(false);
        return;
      }
      
      // Show initial success message
      message.info('Square sync started in background. This may take a few minutes...');
      
      // Poll for completion with progress updates
      const result = await orderService.pollSquareSyncStatus(
        syncStart.task_id,
        (progress: number, status: string) => {
          // Update progress in the UI if needed
          console.log(`Sync progress: ${progress}% - ${status}`);
        }
      );
      
      if (result.success && result.result) {
        const { items_created, items_updated, orders_created, orders_updated, orders_failed } = result.result;
        const totalItems = (items_created || 0) + (items_updated || 0);
        const totalOrders = (orders_created || 0) + (orders_updated || 0);
        
        let successMessage = 'Square sync completed!';
        if (totalItems > 0) {
          successMessage += ` Items: ${items_created || 0} created, ${items_updated || 0} updated.`;
        }
        if (totalOrders > 0) {
          successMessage += ` Orders: ${orders_created || 0} created, ${orders_updated || 0} updated.`;
        }
        if (orders_failed && orders_failed > 0) {
          successMessage += ` (${orders_failed} orders failed)`;
        }
        
        message.success(successMessage);
        
        // Reload recommendations to reflect any newly synced orders
        const updatedRecommendations = await pricingService.getPriceRecommendations(timeFrame);
        setRecommendations(updatedRecommendations);
      } else {
        message.error(result.error || 'Sync failed');
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
    <div style={{ position: 'relative', maxWidth: '100%', margin: '24px 0px'}}>
      {/* Header with Re-sync Button on Right */}
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'flex-start',
        marginBottom: 40 
      }}>
        <div>
          <Title level={2} style={{ margin: 0, color: '#1f2937', fontWeight: 600 }}>
            Your Items
          </Title>
          <Text style={{ color: '#6b7280', fontSize: '16px' }}>
            Optimize your product pricing strategy with AI-driven insights
          </Text>
        </div>
        
        <div style={{ 
          display: 'flex', 
          alignItems: 'center',
          gap: '8px'
        }}>
          <Text type="secondary" style={{ fontSize: '13px' }}>
            Refresh data
          </Text>
          <Button 
            onClick={handleSyncOrders} 
            disabled={syncingOrders} 
            type="text"
            size="small"
            icon={syncingOrders ? <LoadingOutlined /> : <SyncOutlined />}
            style={{
              color: '#6b7280',
              border: '1px solid #e5e7eb',
              borderRadius: '6px',
              height: '32px'
            }}
          >
            {syncingOrders ? 'Syncing...' : 'Re-sync'}
          </Button>
        </div>
      </div>
      
      {/* POS Connection Overlay */}
      {!isPosConnected && (
        <div style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          backdropFilter: 'blur(8px)',
          backgroundColor: 'rgba(249, 250, 251, 0.95)',
          zIndex: 10,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          textAlign: 'center',
          padding: '40px',
          borderRadius: '12px'
        }}>
          <div style={{
            background: 'white',
            padding: '48px',
            borderRadius: '16px',
            boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
            maxWidth: '500px'
          }}>
            <div style={{ 
              width: '64px', 
              height: '64px', 
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 24px'
            }}>
              <ShoppingOutlined style={{ fontSize: '28px', color: 'white' }} />
            </div>
            <Title level={3} style={{ marginBottom: 16, color: '#1f2937' }}>
              Connect Your POS System
            </Title>
            <Text style={{ 
              fontSize: '15px', 
              color: '#6b7280', 
              display: 'block', 
              marginBottom: 32,
              lineHeight: '1.6'
            }}>
              Connect your Square account to import sales data and menu items for personalized pricing insights.
            </Text>
            <Button 
              type="primary" 
              icon={<ShoppingOutlined />}
              onClick={handleSquareIntegration}
              size="large"
              style={{
                height: '48px',
                paddingLeft: '24px',
                paddingRight: '24px',
                fontSize: '15px',
                fontWeight: 500,
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                border: 'none',
                borderRadius: '8px',
                boxShadow: '0 4px 14px 0 rgba(102, 126, 234, 0.4)'
              }}
            >
              Connect Square Account
            </Button>
            <Text style={{ 
              marginTop: 16, 
              fontSize: '13px', 
              color: '#9ca3af',
              display: 'block'
            }}>
              Access all price recommendation features after connecting
            </Text>
          </div>
        </div>
      )}
      {loading ? (
        <ShimmerPriceRecommendations />
      ) : usingMock ? (
        <div style={{ position: 'relative' }}>
          {/* Minimal blurred background */}
          <div style={{ filter: 'blur(3px)', opacity: 0.3 }}>
            {/* Clean Summary Stats */}
            <div style={{ 
              display: 'grid', 
              gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', 
              gap: '24px',
              marginBottom: 32
            }}>
              <div style={{
                background: 'white',
                padding: '24px',
                borderRadius: '12px',
                border: '1px solid #f3f4f6'
              }}>
                <Text style={{ fontSize: '13px', color: '#6b7280', fontWeight: 500 }}>
                  PRICE CHANGES
                </Text>
                <div style={{ fontSize: '24px', fontWeight: 600, color: '#1f2937', marginTop: '4px' }}>
                  10 <span style={{ fontSize: '14px', fontWeight: 400, color: '#9ca3af' }}>products</span>
                </div>
              </div>
              <div style={{
                background: 'white',
                padding: '24px',
                borderRadius: '12px',
                border: '1px solid #f3f4f6'
              }}>
                <Text style={{ fontSize: '13px', color: '#6b7280', fontWeight: 500 }}>
                  ANALYSIS PERIOD
                </Text>
                <div style={{ fontSize: '24px', fontWeight: 600, color: '#1f2937', marginTop: '4px' }}>
                  Last 7 days
                </div>
              </div>
            </div>
            
            {/* Minimal Table */}
            <div style={{
              background: 'white',
              borderRadius: '12px',
              border: '1px solid #f3f4f6',
              overflow: 'hidden'
            }}>
              <Table
                columns={columns}
                dataSource={sampleRecommendations}
                rowKey="id"
                pagination={false}
                showHeader={false}
              />
            </div>
          </div>
          
          {/* Clean overlay message */}
          <div style={{ 
            position: 'absolute', 
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            background: 'white',
            padding: '40px',
            borderRadius: '16px',
            textAlign: 'center',
            boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
            minWidth: '400px'
          }}>
            <div style={{ 
              width: '48px', 
              height: '48px', 
              background: '#f3f4f6',
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 20px'
            }}>
              <ShoppingOutlined style={{ fontSize: '20px', color: '#6b7280' }} />
            </div>
            <Title level={4} style={{ marginBottom: 12, fontWeight: 600 }}>
              No data available
            </Title>
            <Text style={{ color: '#6b7280', marginBottom: 24, fontSize: '14px' }}>
              Connect your POS provider to view AI-powered price recommendations
            </Text>
            <Button 
              type="primary" 
              style={{
                background: '#1f2937',
                border: 'none',
                borderRadius: '8px',
                height: '40px',
                paddingLeft: '20px',
                paddingRight: '20px'
              }}
            >
              Connect POS Provider
            </Button>
          </div>
        </div>
      ) : (
        <>
          {/* Clean Summary Stats Grid */}
          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', 
            gap: '24px',
            marginBottom: 32
          }}>
            <div style={{
              background: 'white',
              padding: '24px',
              borderRadius: '12px',
              border: '1px solid #f3f4f6',
              boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.05)'
            }}>
              <Text style={{ fontSize: '13px', color: '#6b7280', fontWeight: 500, letterSpacing: '0.5px' }}>
                NET REVENUE IMPACT
              </Text>
              <div style={{ 
                fontSize: '28px', 
                fontWeight: 700, 
                color: netRevenueImpact > 0 ? '#059669' : netRevenueImpact < 0 ? '#dc2626' : '#1f2937',
                marginTop: '8px',
                marginBottom: '4px'
              }}>
                ${typeof netRevenueImpact === 'number' ? formatNumberWithCommas(Number(netRevenueImpact.toFixed(2))) : formatNumberWithCommas(Number(netRevenueImpact))}
              </div>
              <Text style={{ fontSize: '12px', color: '#9ca3af' }}>
                Feature in development
              </Text>
            </div>

            <div style={{
              background: 'white',
              padding: '24px',
              borderRadius: '12px',
              border: '1px solid #f3f4f6',
              boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.05)'
            }}>
              <Text style={{ fontSize: '13px', color: '#6b7280', fontWeight: 500, letterSpacing: '0.5px' }}>
                PRICE CHANGES
              </Text>
              <div style={{ fontSize: '28px', fontWeight: 700, color: '#1f2937', marginTop: '8px' }}>
                {typeof recommendations.length === 'number' ? formatNumberWithCommas(recommendations.length) : formatNumberWithCommas(Number(recommendations.length))}
                <span style={{ fontSize: '14px', fontWeight: 400, color: '#9ca3af', marginLeft: '8px' }}>
                  products
                </span>
              </div>
            </div>

            <div style={{
              background: 'white',
              padding: '24px',
              borderRadius: '12px',
              border: '1px solid #f3f4f6',
              boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.05)'
            }}>
              <Text style={{ fontSize: '13px', color: '#6b7280', fontWeight: 500, letterSpacing: '0.5px' }}>
                ANALYSIS PERIOD
              </Text>
              <div style={{ fontSize: '28px', fontWeight: 700, color: '#1f2937', marginTop: '8px', marginBottom: '12px' }}>
                {timeFrame === '1d' ? 'Last 24h' : 
                 timeFrame === '7d' ? 'Last 7d' : 
                 timeFrame === '1m' ? 'Last 30d' : 
                 timeFrame === '6m' ? 'Last 6m' : 'Last year'}
              </div>
              <Radio.Group 
                value={timeFrame} 
                onChange={(e: RadioChangeEvent) => handleTimeFrameChange(e.target.value)}
                buttonStyle="solid"
                size="small"
                style={{
                  background: '#f9fafb',
                  borderRadius: '6px',
                  padding: '0px',
                  border: '0px solid #fff',
                }}
              >
                <Radio.Button 
                  value="1d" 
                  style={{ 
                    border: 'none', 
                    height: '28px',
                    fontSize: '12px'
                  }}
                >
                  1D
                </Radio.Button>
                <Radio.Button 
                  value="7d"
                  style={{ 
                    border: 'none', 
                    height: '28px',
                    fontSize: '12px'
                  }}
                >
                  7D
                </Radio.Button>
                <Radio.Button 
                  value="1m"
                  style={{ 
                    border: 'none', 
                    height: '28px',
                    fontSize: '12px'
                  }}
                >
                  1M
                </Radio.Button>
                <Radio.Button 
                  value="6m"
                  style={{ 
                    border: 'none', 
                    height: '28px',
                    fontSize: '12px'
                  }}
                >
                  6M
                </Radio.Button>
                <Radio.Button 
                  value="1yr"
                  style={{ 
                    border: 'none', 
                    height: '28px',
                    fontSize: '12px'
                  }}
                >
                  1Y
                </Radio.Button>
              </Radio.Group>
            </div>
          </div>
      
          {/* Minimal Table */}
          <div style={{
            background: 'white',
            borderRadius: '12px',
            border: '1px solid #f3f4f6',
            boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.05)',
            overflow: 'hidden'
          }}>
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
          </div>
        </>
      )}
    </div>
  );
};

export default PriceRecommendations;
