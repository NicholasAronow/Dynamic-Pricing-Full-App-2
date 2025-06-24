import React, { useState, useEffect } from 'react';
import { Typography, Card, Row, Col, Button, Tag, Space, Spin, Radio, Tooltip, message } from 'antd';
import { useNavigate } from 'react-router-dom';
import { ShoppingOutlined, ArrowUpOutlined, ArrowDownOutlined, TagsOutlined, ShopOutlined, QuestionCircleOutlined, LineChartOutlined} from '@ant-design/icons';
import { ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Legend, ResponsiveContainer } from 'recharts';
import { useAuth } from '../../context/AuthContext';
import moment from 'moment';

// Import components and services
import ActionItemsCard from './ActionItemsCard';
import cogsService, { COGSEntry } from '../../services/cogsService';
import itemService, { Item } from '../../services/itemService';
import orderService, { Order } from '../../services/orderService';
import analyticsService, { SalesAnalytics } from '../../services/analyticsService';
import competitorService from '../../services/competitorService';
import { integrationService } from '../../services/integrationService';

const { Title, Text, Paragraph } = Typography;

// Function to handle Square integration
const handleSquareIntegration = async () => {
  try {
    console.log('Initiating Square integration from Dashboard');
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



// Note: Mock data generator functions were removed as they're now unused

// Utility function to format numbers with commas that safely handles undefined/null
const formatNumberWithCommas = (num: number | string | undefined | null) => {
  if (num === undefined || num === null) return '0';
  return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
};

// Safe number formatting with toFixed that handles undefined/null values
const safeNumberFormat = (value: any, decimals: number = 2) => {
  if (value === undefined || value === null) return '0.00';
  return Number(value).toFixed(decimals);
};

// Define colors for charts and graphs
const barColors = ['#3f8600', '#52c41a', '#73d13d', '#95de64', '#b7eb8f', '#d9f7be'];

const Dashboard: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [timeFrame, setTimeFrame] = useState('7d');
  const [salesData, setSalesData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // Removed profit margin toggle - only showing sales now
  const [productsLoading, setProductsLoading] = useState(true);
  const [productPerformance, setProductPerformance] = useState<any[]>([]);
  const [itemsTimeFrame, setItemsTimeFrame] = useState('7d');
  const [analyticsData, setAnalyticsData] = useState<SalesAnalytics | null>(null);
  const [competitors, setCompetitors] = useState<any[]>([]);
  const [competitorsLoading, setCompetitorsLoading] = useState(true);
  // States to track if we have any data
  const [hasSalesData, setHasSalesData] = useState(false);
  const [hasProductsData, setHasProductsData] = useState(false);
  const [hasCustomersData, setHasCustomersData] = useState(false);
  // We'll check competitors.length > 0 directly instead of using a separate state
  const [hasAdaptivData, setHasAdaptivData] = useState(false);
  const [showCOGSPrompt, setShowCOGSPrompt] = useState(false);
  // Flag to track if we've ever had an order (used to determine if we should show "Connect POS" prompt)
  const [hasEverHadOrders, setHasEverHadOrders] = useState(false);
  // Use pos_connected field from the user object
  const isPosConnected = user?.pos_connected ?? false;
  
  // Helper function to convert timeframe to dates
  const getDateRangeFromTimeFrame = (timeFrame: string) => {
    // For all views except 1d, include today in the range to ensure we capture current week's COGS data
    const end = timeFrame === '1d' ? moment().subtract(1, 'day').endOf('day') : moment().endOf('day');
    let start;
    
    switch (timeFrame) {
      case '1d':
        // For 1-day view, use yesterday's full day (midnight to midnight)
        start = moment().subtract(1, 'day').startOf('day');
        break;
      case '7d':
        // For 7-day view, include today to ensure we capture data from the current week
        // This ensures we include the current week's COGS data which is critical
        start = moment().subtract(6, 'days').startOf('day');
        break;
      case '1m':
        start = moment().subtract(30, 'days').startOf('day');
        break;
      case '6m':
        start = moment().subtract(180, 'days').startOf('day');
        break;
      case '1yr':
        start = moment().subtract(365, 'days').startOf('day');
        break;
      default:
        start = moment().subtract(30, 'days').startOf('day');
    }
    
    console.log(`Time frame selected: ${timeFrame}, Date range: ${start.format('YYYY-MM-DD')} to ${end.format('YYYY-MM-DD')}`);
    
    return {
      startDate: start.format('YYYY-MM-DD'),
      endDate: end.format('YYYY-MM-DD')
    };
  };

  // Fetch sales data and COGS data from API
  // Keep track of whether we have ANY sales data across all time frames
  const [hasAnySalesData, setHasAnySalesData] = useState(false);
  const [cogsData, setCogsData] = useState<any[]>([]);
  const [processedCogsData, setProcessedCogsData] = useState<Record<string, number>>({});
  
  // Check if the user has ever had orders - this is used to determine if we should show the "Connect POS" prompt
  useEffect(() => {
    const checkForAnyOrders = async () => {
      try {
        const hasOrders = await orderService.checkHasEverHadOrders();
        console.log('User has ever had orders:', hasOrders);
        setHasEverHadOrders(hasOrders);
      } catch (error) {
        console.error('Error checking if user has ever had orders:', error);
        // If there's an error, assume test accounts have orders to avoid showing unnecessary prompts
        if (user?.email?.includes('test')) {
          setHasEverHadOrders(true);
        }
      }
    };
    
    checkForAnyOrders();
  }, [user?.email]);
  // Add cache for monthly aggregated data to ensure consistency
  const [monthlyAggregatedData, setMonthlyAggregatedData] = useState<Record<string, Record<string, { revenue: number; orders: number; cogs: number; profitMargin: number | null }>>>({});
  
  // Helper function to convert weekly COGS to daily values
  // Can process either the current cogsData state or a directly provided array
  const processCogsDataToDaily = (cogsDataToProcess = cogsData) => {
    // Create a map of daily COGS by date
    const dailyCogsByDate: Record<string, number> = {};
    
    console.log('Processing COGS data to daily values:', cogsData);
    
    // If we have no COGS data, let's add some test data to ensure the line appears
    if (!cogsData || cogsData.length === 0) {
      console.log('No COGS data found');
    }
    
    // Process each COGS entry (weekly) into daily values
    cogsDataToProcess.forEach(cogsEntry => {
      const weekStart = moment(cogsEntry.week_start_date);
      const weekEnd = moment(cogsEntry.week_end_date);
      const daysInWeek = weekEnd.diff(weekStart, 'days') + 1;
      const dailyCogs = cogsEntry.amount / daysInWeek; // Distribute weekly COGS evenly to each day
      
      console.log(`Processing COGS entry: ${weekStart.format('YYYY-MM-DD')} to ${weekEnd.format('YYYY-MM-DD')}, amount: ${cogsEntry.amount}, daily: ${dailyCogs}`);
      
      // For each day in the week, add the daily COGS value
      for (let day = 0; day < daysInWeek; day++) {
        const currentDate = moment(weekStart).add(day, 'days').format('YYYY-MM-DD');
        dailyCogsByDate[currentDate] = dailyCogs;
      }
    });
    
    console.log('Processed daily COGS data:', dailyCogsByDate);
    return dailyCogsByDate;
  };
  
  // Check if we have Adaptiv metrics data
  useEffect(() => {
    // This would typically be a real API call to get Adaptiv metrics
    // For now, we're using the presence of other data as a proxy
    const checkAdaptivData = () => {
      // If we have sales data, assume we have Adaptiv data too
      setHasAdaptivData(hasAnySalesData);
    };
    
    checkAdaptivData();
  }, [hasAnySalesData]);

  // Generate empty chart data structure
  const getEmptyChartData = (timeFrame: string) => {
    switch (timeFrame) {
      case '1d':
        return Array.from({ length: 24 }, (_, i) => ({
          name: moment().subtract(1, 'day').startOf('day').add(i, 'hours').format('HH:00'),
          revenue: 0,
          orders: 0,
          profitMargin: null
        }));
      case '7d':
        return Array.from({ length: 7 }, (_, i) => ({
          name: moment().subtract(6 - i, 'days').format('MMM DD'),
          revenue: 0,
          orders: 0,
          profitMargin: null
        }));
      case '1m':
        return Array.from({ length: 30 }, (_, i) => ({
          name: moment().subtract(29 - i, 'days').format('MMM DD'),
          revenue: 0,
          orders: 0,
          profitMargin: null
        }));
      case '6m':
        return Array.from({ length: 6 }, (_, i) => ({
          name: moment().subtract(5 - i, 'months').format('MMM'),
          revenue: 0,
          orders: 0,
          profitMargin: null
        }));
      case '1yr':
        return Array.from({ length: 12 }, (_, i) => ({
          name: moment().subtract(11 - i, 'months').format('MMM'),
          revenue: 0,
          orders: 0,
          profitMargin: null
        }));
      default:
        return [];
    }
  };

  // Add this function to process chart data efficiently
  const processChartData = (
    salesData: any[], 
    cogsEntries: COGSEntry[], 
    timeFrame: string,
    startDate: string,
    endDate: string
  ) => {
    // Create a map of COGS by date for O(1) lookup
    const cogsByDate: Record<string, number> = {};
    cogsEntries.forEach(entry => {
      // Since COGS entries now have daily granularity from the service
      cogsByDate[entry.week_start_date] = entry.amount;
    });
    
    // Create a map of sales by date for O(1) lookup
    const salesByDate: Record<string, { revenue: number; orders: number }> = {};
    salesData.forEach(day => {
      salesByDate[day.date] = { revenue: day.revenue, orders: day.orders };
    });
    
    switch (timeFrame) {
      case '1d':
        return processHourlyData(salesByDate, cogsByDate);
      case '7d':
        return processDailyData(salesByDate, cogsByDate, 7);
      case '1m':
        return processDailyData(salesByDate, cogsByDate, 30);
      case '6m':
      case '1yr':
        return processMonthlyData(salesByDate, cogsByDate, timeFrame);
      default:
        return [];
    }
  };

  // Process hourly data for 1d view
  const processHourlyData = (
    salesByDate: Record<string, { revenue: number; orders: number }>,
    cogsByDate: Record<string, number>
  ) => {
    const yesterday = moment().subtract(1, 'day').startOf('day');
    const yesterdayStr = yesterday.format('YYYY-MM-DD');
    const dailySales = salesByDate[yesterdayStr] || { revenue: 0, orders: 0 };
    const dailyCogs = cogsByDate[yesterdayStr] || 0;
    
    const hourlyData = [];
    for (let hour = 0; hour < 24; hour++) {
      // Distribute daily values across hours (simplified - could be enhanced with hourly patterns)
      const hourlyRevenue = dailySales.revenue / 24;
      const hourlyCogs = dailyCogs / 24;
      
      const profitMargin = hourlyRevenue > 0 && hourlyCogs > 0
        ? ((hourlyRevenue - hourlyCogs) / hourlyRevenue * 100)
        : null;
      
      hourlyData.push({
        name: moment(yesterday).add(hour, 'hours').format('HH:00'),
        revenue: Math.round(hourlyRevenue * 100) / 100,
        orders: Math.round(dailySales.orders / 24),
        profitMargin: profitMargin ? Math.round(profitMargin * 100) / 100 : null
      });
    }
    
    return hourlyData;
  };

  // Process daily data for 7d and 1m views
  const processDailyData = (
    salesByDate: Record<string, { revenue: number; orders: number }>,
    cogsByDate: Record<string, number>,
    days: number
  ) => {
    const endDate = moment().endOf('day');
    const startDate = moment().subtract(days - 1, 'days').startOf('day');
    
    const dailyData = [];
    for (let i = 0; i < days; i++) {
      const currentDate = moment(startDate).add(i, 'days');
      const dateStr = currentDate.format('YYYY-MM-DD');
      
      const sales = salesByDate[dateStr] || { revenue: 0, orders: 0 };
      const cogs = cogsByDate[dateStr] || 0;
      
      const profitMargin = sales.revenue > 0 && cogs > 0
        ? ((sales.revenue - cogs) / sales.revenue * 100)
        : null;
      
      dailyData.push({
        name: currentDate.format('MMM DD'),
        revenue: Math.round(sales.revenue * 100) / 100,
        orders: sales.orders,
        profitMargin: profitMargin ? Math.round(profitMargin * 100) / 100 : null
      });
    }
    
    return dailyData;
  };

  // Process monthly data for 6m and 1yr views
  const processMonthlyData = (
    salesByDate: Record<string, { revenue: number; orders: number }>,
    cogsByDate: Record<string, number>,
    timeFrame: string
  ) => {
    // Aggregate by month
    const monthlyAggregates: Record<string, { revenue: number; orders: number; cogs: number }> = {};
    
    // Process sales data
    Object.entries(salesByDate).forEach(([date, data]) => {
      const monthKey = moment(date).format('YYYY-MM');
      if (!monthlyAggregates[monthKey]) {
        monthlyAggregates[monthKey] = { revenue: 0, orders: 0, cogs: 0 };
      }
      monthlyAggregates[monthKey].revenue += data.revenue;
      monthlyAggregates[monthKey].orders += data.orders;
    });
    
    // Process COGS data
    Object.entries(cogsByDate).forEach(([date, amount]) => {
      const monthKey = moment(date).format('YYYY-MM');
      if (!monthlyAggregates[monthKey]) {
        monthlyAggregates[monthKey] = { revenue: 0, orders: 0, cogs: 0 };
      }
      monthlyAggregates[monthKey].cogs += amount;
    });
    
    // Convert to sorted array and calculate profit margins
    const allMonths = Object.entries(monthlyAggregates)
      .map(([monthKey, data]) => {
        const profitMargin = data.revenue > 0 && data.cogs > 0
          ? ((data.revenue - data.cogs) / data.revenue * 100)
          : null;
        
        return {
          monthKey,
          name: moment(monthKey, 'YYYY-MM').format('MMM'),
          revenue: Math.round(data.revenue * 100) / 100,
          orders: data.orders,
          profitMargin: profitMargin ? Math.round(profitMargin * 100) / 100 : null
        };
      })
      .sort((a, b) => a.monthKey.localeCompare(b.monthKey));
    
    // Return the appropriate number of months
    if (timeFrame === '6m') {
      return allMonths.slice(-6);
    } else {
      return allMonths.slice(-12);
    }
  };
  
  // Replace the existing useEffect for fetchSalesData with this optimized version:
  useEffect(() => {
    const fetchSalesData = async () => {
      try {
        setLoading(true);
        setError(null);
        
        // Get the appropriate date range
        const dateRange = getDateRangeFromTimeFrame(timeFrame);
        const { startDate, endDate } = dateRange;
        
        // Fetch sales data
        const analytics = await analyticsService.getSalesAnalytics(startDate, endDate);
        setAnalyticsData(analytics);
        setHasAnySalesData(analytics.salesByDay && analytics.salesByDay.length > 0);
        
        // Fetch COGS data
        const fetchedCogsData = await cogsService.getCOGSData(startDate, endDate);
        console.log('Fetched COGS data:', fetchedCogsData.length, 'entries');
        
        // Process the data based on timeframe
        if (analytics.salesByDay && analytics.salesByDay.length > 0) {
          const chartData = processChartData(
            analytics.salesByDay, 
            fetchedCogsData, 
            timeFrame,
            startDate,
            endDate
          );
          
          setSalesData(chartData);
          setHasSalesData(true);
        } else {
          // Handle no data case
          setSalesData(getEmptyChartData(timeFrame));
          setHasSalesData(false);
        }
        
      } catch (err) {
        console.error('Error fetching sales data:', err);
        setError('Failed to load sales data');
        setSalesData(getEmptyChartData(timeFrame));
        setHasSalesData(false);
      } finally {
        setLoading(false);
      }
    };
    
    fetchSalesData();
  }, [timeFrame]);
  
  // Fetch product performance data from API
  useEffect(() => {
    const fetchProductPerformance = async () => {
      try {
        setProductsLoading(true);
        
        // Try to fetch real item performance data
        try {
          const data = await analyticsService.getItemPerformance(itemsTimeFrame);
          setProductPerformance(data);
          setHasProductsData(data && data.length > 0);
        } catch (err) {
          console.error('Failed to fetch item performance:', err);
          // No mock data fallback, just set empty array
          setProductPerformance([]);
          setHasProductsData(false);
        }
      } catch (err) {
        console.error('Error fetching product performance:', err);
        // No mock data fallback, just set empty array
        setProductPerformance([]);
      } finally {
        setProductsLoading(false);
      }
    };
    
    fetchProductPerformance();
  }, [itemsTimeFrame]);
  
  // Fetch competitor data using Gemini API endpoint (same as Competitors component)
  useEffect(() => {
    const fetchCompetitorData = async () => {
      try {
        setCompetitorsLoading(true);
        console.log('Dashboard: Fetching competitor data');
        
        // Fetch the full competitor data from the Gemini API
        const geminiCompetitors = await competitorService.getGeminiCompetitors();
        console.log('Dashboard: Received competitors from API:', geminiCompetitors);
        
        if (geminiCompetitors && geminiCompetitors.length > 0) {
          // Process and enhance competitor data 
          const competitorData = [];
          
          for (let i = 0; i < geminiCompetitors.length; i++) {
            const competitor = geminiCompetitors[i];
            
            try {
              // Get similarity scores for this competitor
              const similarityData = await competitorService.calculateSimilarityScore(competitor.name);
              
              // Create enriched competitor object using both data sources
              competitorData.push({
                key: String(i + 1),
                name: competitor.name,
                address: competitor.address,
                category: competitor.category,
                distance: competitor.distance_km || similarityData.distance || 0,
                menu_url: competitor.menu_url,
                report_id: competitor.report_id,
                created_at: competitor.created_at,
                similarityScore: similarityData.similarityScore || 0,
                priceSimScore: similarityData.priceSimScore || 0,
                menuSimScore: similarityData.menuSimScore || 0,
                distanceScore: similarityData.distanceScore || 0,
                // We'll use estimates based on similarity score for menu items
                menuItemsCount: Math.round((similarityData.menuSimScore / 10) + 7),
                menuItemsInCommon: Math.round((similarityData.menuSimScore / 20) + 3)
              });
            } catch (err) {
              console.error(`Error calculating similarity for ${competitor.name}:`, err);
              // Still add the competitor with default values
              competitorData.push({
                key: String(i + 1),
                name: competitor.name,
                address: competitor.address,
                category: competitor.category,
                distance: competitor.distance_km || 0,
                menu_url: competitor.menu_url,
                report_id: competitor.report_id,
                created_at: competitor.created_at,
                similarityScore: 50, // Default value
                menuItemsCount: 5,
                menuItemsInCommon: 2
              });
            }
          }
          
          console.log('Dashboard: Processed competitor data:', competitorData);
          setCompetitors(competitorData);
        } else {
          console.log('Dashboard: No Gemini competitors found, trying fallback');
          // Fallback to the old method if no Gemini competitors are available
          try {
            // Get all competitor names
            const competitorNames = await competitorService.getCompetitors();
            
            if (competitorNames && competitorNames.length > 0) {
              const fallbackData = [];
              
              for (let i = 0; i < competitorNames.length; i++) {
                const name = competitorNames[i];
                
                try {
                  // Get similarity scores for this competitor
                  const similarityData = await competitorService.calculateSimilarityScore(name);
                  
                  fallbackData.push({
                    key: String(i + 1),
                    name: name,
                    similarityScore: similarityData.similarityScore || 0,
                    priceSimScore: similarityData.priceSimScore || 0,
                    menuSimScore: similarityData.menuSimScore || 0,
                    distanceScore: similarityData.distanceScore || 0,
                    distance: similarityData.distance || 0,
                    menuItemsCount: Math.round(Math.random() * 20) + 5,
                    menuItemsInCommon: Math.round(Math.random() * 10) + 2
                  });
                } catch (err) {
                  fallbackData.push({
                    key: String(i + 1),
                    name: name,
                    similarityScore: 0,
                    menuItemsCount: 0,
                    menuItemsInCommon: 0
                  });
                }
              }
              
              console.log('Dashboard: Using fallback competitor data:', fallbackData);
              setCompetitors(fallbackData);
            } else {
              console.log('Dashboard: No competitor names found in fallback');
              setCompetitors([]);
            }
          } catch (err) {
            console.error('Error in fallback competitor fetching:', err);
            setCompetitors([]);
          }
        }
      } catch (err) {
        console.error('Error in competitor data fetching:', err);
        setCompetitors([]);
      } finally {
        setCompetitorsLoading(false);
      }
    };
    
    fetchCompetitorData();
  }, []);
  
  // Ensure the current week's COGS data is always included in dashboard calculations
  useEffect(() => {
    const ensureCurrentWeekCOGSData = async () => {
      if (!user) return;
      
      try {
        // Use our specialized function to get current week's COGS data specifically
        const currentWeekCOGS = await cogsService.getCurrentWeekCOGSData();
        
        // Check if we have current week COGS data
        const hasCurrentWeekData = currentWeekCOGS.length > 0;
        
        // Update the COGS prompt visibility based on whether we have data
        setShowCOGSPrompt(!hasCurrentWeekData);
        
        // If we have current week data, ensure it's included in our processed COGS data
        if (hasCurrentWeekData) {
          console.log('Found current week COGS data, processing for display', currentWeekCOGS);
          
          // Process current week's COGS data into daily values
          const currentWeekProcessed = processCogsDataToDaily(currentWeekCOGS);
          
          // Debug logging
          console.log('Processed current week COGS data into daily values:', currentWeekProcessed);
          Object.entries(currentWeekProcessed).forEach(([date, amount]) => {
            console.log(`Daily COGS for ${date}: $${amount.toFixed(2)}`);
          });
          
          // Ensure all timeframes have access to this current week's data
          setProcessedCogsData(prevData => {
            const updatedData = { ...prevData, ...currentWeekProcessed };
            console.log('Updated processedCogsData with current week data', updatedData);
            return updatedData;
          });
          
          // Also update the raw COGS data array to include current week entries
          setCogsData(prevData => {
            // Remove any entries for the current week that might be outdated
            const today = moment();
            const startOfWeek = today.clone().startOf('week');
            
            const filteredData = prevData.filter(entry => 
              !moment(entry.week_start_date).isSame(startOfWeek, 'day')
            );
            
            // Add the new current week entries
            const updatedData = [...filteredData, ...currentWeekCOGS];
            console.log('Updated cogsData with current week entries', updatedData);
            return updatedData;
          });
          
          // Force a re-calculation of all data that depends on COGS
          if (timeFrame === '7d' || timeFrame === '1m') {
            console.log(`Force refreshing ${timeFrame} view to include current week COGS data`);
            // This will trigger the useEffect that depends on timeFrame
            setTimeFrame(prev => prev === '7d' ? '7d_refresh' : '1m_refresh');
            // Immediately set it back to avoid double refresh
            setTimeout(() => setTimeFrame(prev => prev.includes('refresh') ? prev.split('_')[0] : prev), 10);
          }
        }
      } catch (error) {
        console.error('Error ensuring current week COGS data:', error);
        setShowCOGSPrompt(true); // Show prompt on error as a safe default
      }
    };
    
    // Always check for current week's COGS data when component loads or user changes
    ensureCurrentWeekCOGSData();
    
    // We'll also set up an interval to check for updates every 5 minutes if the dashboard stays open
    const intervalId = setInterval(() => {
      console.log('Scheduled COGS data refresh');
      ensureCurrentWeekCOGSData();
    }, 5 * 60 * 1000); // 5 minutes
    
    return () => clearInterval(intervalId);
  }, [user]);

  // Handle completion of COGS data entry
  const handleCOGSComplete = () => {
    setShowCOGSPrompt(false);
  };

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
  
  // Get top 3 competitors by similarity score
  const getTopCompetitors = () => {
    if (!competitors.length) return [];
    return [...competitors].sort((a, b) => b.similarityScore - a.similarityScore).slice(0, 3);
  };
  
  // Add CSS styles for competitor items
  useEffect(() => {
    // Add CSS for hover effects
    const styleTag = document.createElement('style');
    styleTag.innerHTML = `
      .dashboard-competitor-item:hover {
        background-color: rgba(240, 240, 240, 0.8) !important;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
      }
    `;
    document.head.appendChild(styleTag);
    
    // Cleanup function to remove style tag on unmount
    return () => {
      document.head.removeChild(styleTag);
    };
  }, []);

  // Function to calculate price differential average
  const getAveragePriceDifferential = () => {
    if (competitors.length === 0) return { direction: 'higher', value: 0 };
    
    // Average price differential calculation
    // Check if we have priceSimScore data
    let totalDiff = 0;
    let count = 0;
    
    for (const competitor of competitors) {
      if (competitor.priceSimScore) {
        // Convert priceSimScore to a differential
        // We use a formula that derives differential from similarity
        // Higher sim score means closer to our prices
        // If similarityScore is 100, diff is 0
        // If similarityScore is 0, diff could be up to 50%
        const diff = Math.max(0, (100 - competitor.priceSimScore) / 2);
        totalDiff += diff;
        count++;
      }
    }
    
    if (count === 0) return { direction: 'higher', value: 0 };
    
    // Determine if our prices are higher or lower
    // This is a simplified logic - in a real app we'd need more data
    // For now, we assume if priceSimScore > 50, our prices are lower
    // This is just for demonstration
    const avgPriceSimScore = competitors.reduce((sum, c) => sum + (c.priceSimScore || 0), 0) / competitors.length;
    
    return {
      direction: avgPriceSimScore > 60 ? 'lower' : 'higher',
      value: parseFloat((totalDiff / count).toFixed(1))
    };
  };
  
  // Calculate normalized prices for relative price line chart
  const getNormalizedPrices = () => {
    if (competitors.length === 0) return [];
    
    // Extract prices from competitors (using priceSimScore as a proxy for actual price)
    // In a real app, we'd have actual price data
    const competitorPrices = competitors.map(comp => {
      // We invert priceSimScore because higher similarity means closer price
      // Lower similarity often indicates more price difference
      return {
        id: comp.key,
        name: comp.name,
        price: 100 - (comp.priceSimScore || 50), // Convert to a price proxy
        isUs: false
      };
    });
    
    // Calculate our price based on the price differential data
    // This ensures we're positioned relatively compared to competitors
    const priceDiff = getAveragePriceDifferential();
    
    // Get the average competitor price
    const avgCompetitorPrice = competitorPrices.reduce((sum, c) => sum + c.price, 0) / competitorPrices.length;
    
    // Calculate our price - higher or lower based on the differential
    const ourPrice = priceDiff.direction === 'higher' 
      ? avgCompetitorPrice + (avgCompetitorPrice * (priceDiff.value / 100))
      : avgCompetitorPrice - (avgCompetitorPrice * (priceDiff.value / 100));
    
    // Add our business with the calculated price
    competitorPrices.push({
      id: 'us',
      name: 'Your Restaurant',
      price: ourPrice,
      isUs: true
    });
    
    // Find min and max for normalization
    const prices = competitorPrices.map(c => c.price);
    const minPrice = Math.min(...prices);
    const maxPrice = Math.max(...prices);
    
    // Normalize prices to 0-10 scale
    return competitorPrices.map(comp => ({
      ...comp,
      normalizedPrice: maxPrice === minPrice ? 5 : // handle edge case where all prices are equal
        parseFloat(((comp.price - minPrice) / (maxPrice - minPrice) * 10).toFixed(1))
    }));
  };

  // Calculate market position percentile based on competitor data
  const getMarketPosition = () => {
    if (!competitors.length) return "Unknown";
    
    // Calculate position based on similarity scores and menu items in common
    const competitorCount = competitors.length;
    const avgSimilarity = competitors.reduce(
      (sum, c) => sum + (c.similarityScore || 0), 0
    ) / Math.max(competitorCount, 1); // Avoid division by zero
    
    // Higher similarity and more competitors = better market position
    // Lower percentile is better (e.g., Top 5% is better than Top 50%)
    let percentile = 50; // Default to middle
    
    if (avgSimilarity > 70) percentile = 10;
    else if (avgSimilarity > 50) percentile = 25;
    else if (avgSimilarity < 30) percentile = 75;
    
    // Adjust for number of competitors (more competitors = better knowledge)
    if (competitorCount >= 5) percentile = Math.max(5, percentile - 5);
    if (competitorCount <= 2) percentile = Math.min(95, percentile + 15);
    
    return `Top ${percentile}%`;
  };
  
  // Get total menu items being tracked across all competitors
  const getTotalMenuItems = () => {
    if (!competitors.length) return 0;
    return competitors.reduce((sum, c) => sum + (c.menuItemsCount || 0), 0);
  };
  
  // Get total menu items in common with competitors
  const getTotalMenuItemsInCommon = () => {
    if (!competitors.length) return 0;
    return competitors.reduce((sum, c) => sum + (c.menuItemsCount || 0), 0);
  };
  
  const topProducts = getTopProducts();
  const bottomProducts = getBottomProducts();
  
  return (
    <div style={{ position: 'relative' }}>
      <Title level={2}>Dashboard</Title>
      <Title level={5} type="secondary" style={{ marginTop: 0, marginBottom: 24 }}>
        Welcome back, {formattedName}! Here's your dynamic pricing overview
      </Title>
      
      {/* Single conditional blur overlay for the entire dashboard */}
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
            To access your dynamic pricing dashboard, please connect your Square account.
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
            <Text type="secondary">After connecting, you'll have access to all dashboard features</Text>
          </Paragraph>
        </div>
      )}
      
      {/* Chart Row with Sales Chart and Action Items */}
      <Row gutter={24} style={{ marginBottom: 24 }}>
        {/* Sales/Profit Margin Chart - Takes up more space */}
        <Col xs={24} sm={24} md={14} lg={14} xl={14}>
          <Card 
            title={
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span><LineChartOutlined /> Sales Over Time</span>
                <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
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
            style={{ height: '100%' }}
          >
        {loading ? (
          <div style={{ height: 300, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
            <Spin size="large" />
          </div>
        ) : !isPosConnected ? (
          <div style={{ width: '100%', height: 300, position: 'relative' }}>
            {/* Blurred sample data in background */}
            <div style={{ width: '100%', height: '100%', filter: 'blur(5px)', opacity: 0.6 }}>
              <ResponsiveContainer>
                <ComposedChart
                  data={[]}
                  margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis tickFormatter={(tick) => `$${formatNumberWithCommas(tick)}`} />
                  <Bar 
                    dataKey="revenue" 
                    name="Sales" 
                    fill="#9370DB" 
                    radius={[4, 4, 0, 0]}
                  />
                </ComposedChart>
              </ResponsiveContainer>
            </div>

            {/* Semi-transparent overlay with message */}
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
              background: 'rgba(255, 255, 255, 0.85)',
              padding: '20px',
              textAlign: 'center',
              borderRadius: '8px'
            }}>
              <Title level={4}>No Sales Data Available</Title>
              <Paragraph>
                Connect your Square account to import your sales data and menu items.
                Get personalized insights and price recommendations based on your actual sales.
              </Paragraph>
              <Button 
                type="primary" 
                icon={<ShoppingOutlined />}
                onClick={handleSquareIntegration}
                size="large"
              >
                Connect Square Account
              </Button>
              <Paragraph style={{ marginTop: 12, fontSize: '12px', opacity: 0.7 }}>
                <Text type="secondary">After connecting, check your data in the <a href="/square-test">Square Test Page</a></Text>
              </Paragraph>
            </div>
          </div>
        ) : (
          <div style={{ width: '100%', height: 300 }}>
            <ResponsiveContainer>
              <ComposedChart
                data={salesData}
                margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                {/* Primary Y-axis for revenue */}
                <YAxis 
                  yAxisId="left"
                  tickFormatter={(tick) => `$${formatNumberWithCommas(tick)}`}
                />
                {/* Secondary Y-axis for profit margin percentage */}
                <YAxis 
                  yAxisId="right" 
                  orientation="right" 
                  domain={[-50, 100]}
                  tickFormatter={(tick) => `${tick}%`}
                />
                <RechartsTooltip 
                  formatter={(value: number, name: string) => {
                    if (name === 'Sales') {
                      return [`$${formatNumberWithCommas(value.toFixed(2))}`, name];
                    } else if (name === 'Profit Margin') {
                      return [`Profit Margin: ${value.toFixed(2)}%`, name];
                    }
                    return [value, name];
                  }}
                  labelFormatter={(label: string) => `Date: ${label}`}
                />
                <Legend />
                <Bar 
                  dataKey="revenue" 
                  name="Sales" 
                  fill="#9370DB" 
                  radius={[4, 4, 0, 0]}
                  yAxisId="left"
                />
                {/* Profit margin as a dashed line with MAXIMUM visibility */}
                <Line 
                  type="monotone" 
                  dataKey="profitMargin" 
                  name="Profit Margin" 
                  stroke="#00C853" 
                  strokeWidth={3}
                  strokeDasharray="5 5"
                  dot={false}
                  activeDot={{ r: 8 }}
                  yAxisId="right"
                  connectNulls={true} /* Connect points even if some are null - critical for continuous line */
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        )}
          </Card>
        </Col>
        
        {/* Action Items Card - Takes up less space */}
        <Col xs={24} sm={24} md={10} lg={10} xl={10}>
          <ActionItemsCard />
        </Col>

      </Row>
      
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
            ) : !isPosConnected ? (
              <div style={{ height: 400, position: 'relative' }}>
                {/* Blurred sample product data in background */}
                  <div style={{ opacity: 0.7 }}>
                    {/* Top Products Sample */}
                    <div>
                      <Title level={4} style={{ color: '#3f8600', display: 'flex', alignItems: 'center', marginTop: -5, marginBottom: 16 }}>
                        Best Selling Items
                      </Title>
                      <div style={{ marginBottom: 36 }}>
                        
                      </div>
                    </div>
                  </div>


              </div>
            ) : (
              <div>
                {/* Top Performers */}
                <div>
                  <Title level={4} style={{ color: '#3f8600', display: 'flex', alignItems: 'center', marginTop: -5, marginBottom: 16 }}>
                    Best Selling Items
                  </Title>
                  <div style={{ marginBottom: 36 }}>
                  {!error && topProducts && topProducts.map((product: any, index: number) => {
                    const color = barColors[index % barColors.length];
                    return (
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
                            </div>
                            <div style={{ marginTop: 4 }}>
                              <span>
                                ${formatNumberWithCommas(Number((product.currentPrice || 0).toFixed(2)))}
                              </span>
                            </div>
                          </div>
                          <div style={{ textAlign: 'right' }}>
                            <div>
                              <strong>${formatNumberWithCommas(Number((product.revenue || 0).toFixed(2)))}</strong>
                              <span style={{ fontSize: '0.85em', color: '#8c8c8c', marginLeft: 4 }}>revenue</span>
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', marginTop: 4 }}>
                              <div style={{ marginRight: 12 }}>
                                <Tooltip title="Units Sold">
                                  <span>{formatNumberWithCommas(product.quantitySold || 0)} units</span>
                                </Tooltip>
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
                    );
                  })}
                  </div>
                </div>
    
                {/* Bottom Performers */}
                <div>
                  <Title level={4} style={{ color: '#cf1322', display: 'flex', alignItems: 'center', marginBottom: 16, marginTop: 12 }}>
                    Worst Selling Items 
                  </Title>
                  <div>
                    {bottomProducts && bottomProducts.map((product: any, index: number) => (
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
                            </div>
                            <div style={{ marginTop: 4 }}>
                              <span>
                                ${formatNumberWithCommas(Number((product.currentPrice || 0).toFixed(2)))}
                              </span>
                            </div>
                          </div>
                          <div style={{ textAlign: 'right' }}>
                            <div>
                              <strong>${formatNumberWithCommas(Number((product.revenue || 0).toFixed(2)))}</strong>
                              <span style={{ fontSize: '0.85em', color: '#8c8c8c', marginLeft: 4 }}>revenue</span>
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', marginTop: 4 }}>
                              <div style={{ marginRight: 12 }}>
                                <Tooltip title="Units Sold">
                                  <span>{formatNumberWithCommas(product.quantitySold || 0)} units</span>
                                </Tooltip>
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
            {/* Competitor Analysis Card */}
            <Card 
              title={<span>
                Competitor Analysis
              </span>}
              extra={<Button type="link" onClick={() => navigate('/competitors')}>View Details</Button>}
              style={{ width: '100%' }}
              className="dashboard-card"
              bodyStyle={{ padding: '16px 20px', position: 'relative' }}
            >
              {/* Blur overlay with development message */}
              <div style={{ 
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                backdropFilter: 'blur(4px)',
                backgroundColor: 'rgba(255, 255, 255, 0.7)',
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                zIndex: 3,
                borderRadius: '0 0 8px 8px'
              }}>
                <div style={{ 
                  textAlign: 'center', 
                  fontWeight: 'bold',
                  fontSize: '16px',
                  color: '#a0a0a0'
                }}>
                  Competitor Comparison Feature in Development
                </div>
              </div>
              
              {!isPosConnected ? (
                <div style={{ position: 'relative' }}>
                  {/* Blurred sample data in background */}
                    <div style={{ marginTop: 16 }}>
                      <p>Competitors Tracked: 5</p>
                      <p>Price Differential: <span style={{ color: '#cf1322' }}><ArrowDownOutlined /> 5.3%</span></p>
                      <p>Feature Parity: 92%</p>
                      
                      {/* Sample top competitors */}
                      <div style={{ marginTop: 16 }}>
                        <h4 style={{ marginBottom: 12 }}>Top Competitors by Similarity</h4>
                        {[1, 2, 3].map((i) => (
                          <div 
                            key={i}
                            style={{ 
                              padding: '8px 6px', 
                              borderBottom: i < 3 ? '1px solid #f0f0f0' : 'none',
                              borderRadius: '4px'
                            }}
                          >
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                              <div style={{ fontWeight: 500 }}>Competitor {i}</div>
                              <div>
                                <Tag color="blue">{85 - (i * 5)}%</Tag>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                  </div>
                </div>
              ) : (
                <>
                  <div style={{ marginTop: 16 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-around', marginBottom: '16px' }}>
                      <div style={{ textAlign: 'center', padding: '0 5px' }}>
                        <div style={{ marginBottom: '4px' }}>
                          <ShopOutlined style={{ fontSize: '18px', color: '#1890ff', marginRight: '6px' }} />
                          <span style={{ fontWeight: 600, fontSize: '15px' }}>Competitors</span>
                        </div>
                        <div style={{ fontSize: '18px', fontWeight: 500 }}>
                          {competitors.length}
                        </div>
                      </div>
                      
                      <div style={{ textAlign: 'center', padding: '0 5px' }}>
                        <div style={{ marginBottom: '4px' }}>
                          <TagsOutlined style={{ fontSize: '18px', color: '#1890ff', marginRight: '6px' }} />
                          <span style={{ fontWeight: 600, fontSize: '15px' }}>Menu Items in Common</span>
                        </div>
                        <div style={{ fontSize: '18px', fontWeight: 500 }}>
                          {getTotalMenuItems()}
                        </div>
                      </div>
                    </div>
                    
                    {competitors.length > 0 && (
                      <> 
                        {/* Relative Price Comparison Line */}
                        <div style={{ margin: '24px 0 16px' }}>
                          <div style={{ marginBottom: '8px', display: 'flex', alignItems: 'center' }}>
                            <span style={{ fontWeight: 600 }}>Relative Price Comparison</span>
                            <Tooltip title="Lower values indicate lower prices, higher values indicate higher prices">
                              <QuestionCircleOutlined style={{ color: '#aaa', fontSize: '12px', marginLeft: '6px' }} />
                            </Tooltip>
                          </div>
                          
                          <div style={{ position: 'relative', height: '56px', marginTop: '12px' }}>
                            {/* Price labels */}
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                              <small style={{ color: '#888', fontWeight: 500 }}>Lower Prices</small>
                              <small style={{ color: '#888', fontWeight: 500 }}>Higher Prices</small>
                            </div>
                            
                            {/* Scale line */}
                            <div style={{ 
                              position: 'relative', 
                              marginTop: '16px',
                              marginBottom: '8px',
                              height: '16px',
                              display: 'flex',
                              alignItems: 'center'
                            }}>
                              {/* The actual line */}
                              <div style={{ 
                                height: '4px', 
                                background: 'linear-gradient(to right,rgba(83, 196, 26, 0.61), rgba(250, 173, 20, 0.61), rgba(245, 34, 45, 0.61))', 
                                width: '100%',
                                position: 'absolute',
                                left: 0,
                                right: 0
                              }}></div>
                              
                              {/* Price points for each competitor */}
                              {getNormalizedPrices().map((comp) => {
                                const leftPosition = `${comp.normalizedPrice * 10}%`;
                                
                                return (
                                  <Tooltip 
                                    key={comp.id} 
                                    title={
                                      <div>
                                        <div><strong>{comp.name}</strong></div>
                                        <div>Relative price: {comp.normalizedPrice.toFixed(1)}/10</div>
                                      </div>
                                    }
                                    color={comp.isUs ? '#1677ff' : '#333'}
                                  >
                                    <div
                                      style={{
                                        position: 'absolute',
                                        left: leftPosition,
                                        width: comp.isUs ? '16px' : '12px',
                                        height: comp.isUs ? '16px' : '12px',
                                        borderRadius: '50%',
                                        backgroundColor: comp.isUs ? '#1677ff' : '#555',
                                        border: comp.isUs ? '2px solid white' : '1px solid #f0f0f0',
                                        boxShadow: comp.isUs ? '0 0 0 2px rgba(24, 144, 255, 0.2)' : 'none',
                                        transform: 'translateX(-50%)',
                                        cursor: 'pointer',
                                        zIndex: comp.isUs ? 2 : 1,
                                        transition: 'all 0.3s ease'
                                      }}
                                    />
                                  </Tooltip>
                                );
                              })}
                            </div>
                          </div>
                        </div>
                      </>
                    )}
                    
                    {/* Top 3 Competitors Section */}
                    <div style={{ marginTop: 16 }}>
                      <h4 style={{ marginBottom: 12 }}>Top Competitors by Similarity</h4>
                      {competitorsLoading ? (
                        <div style={{ textAlign: 'center', padding: '10px 0' }}>
                          <Spin size="small" />
                        </div>
                      ) : (
                        <div>
                          {getTopCompetitors().map((competitor, index) => (
                            <div 
                              key={competitor.key}
                              onClick={() => navigate(`/competitor/${competitor.report_id || encodeURIComponent(competitor.name)}`)}
                              className="dashboard-competitor-item"
                              style={{ 
                                padding: '10px 8px', 
                                borderBottom: index < getTopCompetitors().length - 1 ? '1px solid #f0f0f0' : 'none',
                                cursor: 'pointer',
                                borderRadius: '4px',
                                transition: 'all 0.3s ease',
                                backgroundColor: 'rgba(250, 250, 250, 0.4)'
                              }}
                            >
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <div>
                                  <div style={{ fontWeight: 500 }}>{competitor.name}</div>
                                  <div style={{ fontSize: '12px', color: '#888' }}>
                                    {competitor.menuItemsCount} items in common
                                  </div>
                                </div>
                                <div>
                                  <Tag color={competitor.similarityScore > 70 ? 'blue' : competitor.similarityScore > 40 ? 'geekblue' : 'purple'}>
                                    {competitor.similarityScore}%
                                  </Tag>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </>
              )}
                </Card>
          </Space>
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard;
