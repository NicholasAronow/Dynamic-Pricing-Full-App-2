import React, { useState, useEffect } from 'react';
import { Typography, Card, Row, Col, Statistic, Button, Radio, Spin, Table, Tag, Space, Tooltip as AntTooltip, Alert, Empty } from 'antd';
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
import { ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Legend, ResponsiveContainer } from 'recharts';
import { useAuth } from '../../context/AuthContext';
import moment from 'moment';

// Import components and services
import ActionItemsCard from './ActionItemsCard';
import cogsService from '../../services/cogsService';
import itemService, { Item } from '../../services/itemService';
import orderService, { Order } from '../../services/orderService';
import analyticsService, { SalesAnalytics } from '../../services/analyticsService';
import competitorService from '../../services/competitorService';

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
  // Use yesterday as the most recent date (end date) for all time frames
  const endDate = moment().subtract(1, 'day').endOf('day');
  
  let numPoints: number;
  let format: string;
  let dateFormat: string;
  let step: number;
  let unit: any;
  
  switch (timeFrame) {
    case '1d':
      // For 1-day, show 24 hours from midnight to midnight of yesterday
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
      numPoints = 6; // Show just 6 months
      format = 'MMM'; // Just show month name
      dateFormat = 'YYYY-MM';
      step = 1;
      unit = 'months';
      break;
    case '1yr':
      numPoints = 12;
      format = 'MMM'; // Just show month name without year
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
  for (let i = 0; i < numPoints; i++) {
    let date;
    if (timeFrame === '1d') {
      // For 1d view, use hours of yesterday from midnight to 11 PM
      date = moment(endDate).startOf('day').add(i, 'hours');
    } else if (timeFrame === '7d') {
      // For 7d view, start 6 days before yesterday and include yesterday
      date = moment(endDate).subtract(6, 'days').add(i, 'days');
    } else if (timeFrame === '6m' || timeFrame === '1yr') {
      // For 6m and 1yr, ensure we're using the first day of each month
      // Start from the appropriate month and add months
      const startMonth = moment(endDate).subtract(numPoints - 1, 'months').startOf('month');
      date = moment(startMonth).add(i, 'months').startOf('month');
    } else {
      // For other views, work backwards from yesterday
      date = moment(endDate).subtract(numPoints - 1, unit).add(i * step, unit);
    }
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
      if (day === 0 || day === 6) { // Weekend days (Saturday = 6, Sunday = 0)
        modifier = 1.3; // Higher sales on weekends
      } else {
        modifier = 0.9 + (Math.random() * 0.3); // Weekday variation
      }
    } else if (timeFrame === '6m' || timeFrame === '1yr') {
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
      profitMargin: parseFloat(profitMargin.toFixed(2))
    });
  }
  
  return data;
};

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
  const [hasCompetitorsData, setHasCompetitorsData] = useState(false);
  const [hasAdaptivData, setHasAdaptivData] = useState(false);
  const [showCOGSPrompt, setShowCOGSPrompt] = useState(false);
  
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

  // Function to process and aggregate monthly data with consistent calculations
  const processMonthlyData = (salesData: any[], cogsData: Record<string, number>, startDate: string, endDate: string): Record<string, { revenue: number; orders: number; cogs: number; profitMargin: number | null }> => {
    const startMoment = moment(startDate);
    const endMoment = moment(endDate);
    
    // Build look-up map for daily sales
    const salesMap: Record<string, { revenue: number; orders: number }> = {};
    salesData.forEach(day => {
      salesMap[day.date] = { revenue: day.revenue, orders: day.orders };
    });

    // Process data month by month
    const monthlyData: Record<string, { revenue: number; orders: number; cogs: number; profitMargin: number | null }> = {};
    
    let cursor = startMoment.clone();
    while (cursor.isSameOrBefore(endMoment, 'day')) {
      const dateStr = cursor.format('YYYY-MM-DD');
      const monthKey = cursor.format('YYYY-MM');
      
      if (!monthlyData[monthKey]) {
        monthlyData[monthKey] = { revenue: 0, orders: 0, cogs: 0, profitMargin: null };
      }

      const dailySales = salesMap[dateStr] || { revenue: 0, orders: 0 };
      monthlyData[monthKey].revenue += dailySales.revenue;
      monthlyData[monthKey].orders += dailySales.orders;
      monthlyData[monthKey].cogs += cogsData[dateStr] || 0;

      cursor.add(1, 'day');
    }
    
    // Calculate profit margins for each month using EXACTLY the same formula
    Object.entries(monthlyData).forEach(([monthKey, data]) => {
      if (data.revenue > 0 && data.cogs > 0) {
        // Always use this exact formula to ensure consistency
        data.profitMargin = parseFloat(((data.revenue - data.cogs) / data.revenue * 100).toFixed(2));
      } else {
        data.profitMargin = null;
      }
    });
    
    return monthlyData;
  };
  
  useEffect(() => {
    const fetchSalesData = async () => {
      try {
        setLoading(true);
        setError(null);
        
        // Always fetch a full year of data for 6m and 1yr views to ensure consistency
        let fetchStartDate, fetchEndDate;
        if (timeFrame === '6m' || timeFrame === '1yr') {
          // Always fetch a full year for both views to ensure consistency
          fetchStartDate = moment().startOf('month').subtract(11, 'months').format('YYYY-MM-DD');
          fetchEndDate = moment().endOf('day').format('YYYY-MM-DD');
          console.log(`${timeFrame} view: Fetching full year data from ${fetchStartDate} to ${fetchEndDate}`);
        } else {
          // For other timeframes, fetch the specific date range
          const dateRange = getDateRangeFromTimeFrame(timeFrame);
          fetchStartDate = dateRange.startDate;
          fetchEndDate = dateRange.endDate;
        }
        
        // Fetch COGS data for this period
        let currentProcessedCogsData: Record<string, number> = {};
        try {
          const fetchedCogsData = await cogsService.getCOGSData(fetchStartDate, fetchEndDate);
          console.log('Fetched COGS data, length:', fetchedCogsData.length);
          
          // Process COGS data immediately and store locally
          if (fetchedCogsData && fetchedCogsData.length > 0) {
            currentProcessedCogsData = processCogsDataToDaily(fetchedCogsData);
          }
          
          // Update state for other components
          setCogsData(fetchedCogsData);
          setProcessedCogsData(currentProcessedCogsData);
        } catch (cogsError) {
          console.error('Error fetching COGS data:', cogsError);
          // Continue with sales data even if COGS fetch fails
        }
        
        // Fetch analytics data if available
        try {
          const analytics = await analyticsService.getSalesAnalytics(fetchStartDate, fetchEndDate);
          setAnalyticsData(analytics);
          
          // If we have daily sales data, use it for the chart
          // Set global flag that we have data, even if not for the current time frame
          setHasAnySalesData(true);
          
          if (analytics.salesByDay && analytics.salesByDay.length > 0) {
            // Data processing for chart display
            let formattedData;
            
            // For 6m and 1yr views, use our shared data processing function
            // to ensure complete consistency in calculations
            if (timeFrame === '6m' || timeFrame === '1yr') {
              // Use the shared processing function to get consistent monthly data
              const allMonthlyData = processMonthlyData(
                analytics.salesByDay,
                currentProcessedCogsData,
                fetchStartDate,
                fetchEndDate
              );
              
              // Track this data processing in our app state
              const dataSetKey = `${fetchStartDate}_${fetchEndDate}`;
              const updatedAggregatedData = {...monthlyAggregatedData};
              updatedAggregatedData[dataSetKey] = allMonthlyData;
              setMonthlyAggregatedData(updatedAggregatedData);
              
              // Format data for the chart display
              const allMonths = Object.entries(allMonthlyData)
                .map(([monthKey, data]) => ({
                  name: moment(monthKey, 'YYYY-MM').format('MMM'),
                  monthKey: monthKey,
                  revenue: data.revenue,
                  orders: data.orders,
                  profitMargin: data.profitMargin
                }))
                .sort((a, b) => a.monthKey.localeCompare(b.monthKey));
              
              // For 6m view, only use last 6 months of data
              if (timeFrame === '6m') {
                formattedData = allMonths.slice(-6);
                console.log(`6m view: Using last ${formattedData.length} months of full-year data`);
              } else {
                formattedData = allMonths;
                console.log(`1yr view: Using all ${formattedData.length} months of data`);
              }
              
              // Detailed logging for verification
              console.log(`${timeFrame} view first month: ${formattedData[0]?.monthKey}, last month: ${formattedData[formattedData.length-1]?.monthKey}`);
              formattedData.forEach(month => {
                const originalData = allMonthlyData[month.monthKey];
                console.log(`Month ${month.monthKey}: Revenue: ${originalData.revenue}, COGS: ${originalData.cogs}, Profit: ${originalData.profitMargin?.toFixed(2)}%`);
              });
            } else if (timeFrame === '1d') {
              // For 1d, ensure we show all 24 hours even if there's no data
              const yesterday = moment().subtract(1, 'day').startOf('day');
              formattedData = [];
              
              for (let i = 0; i < 24; i++) {
                const hourTime = moment(yesterday).add(i, 'hours');
                const hourStr = hourTime.format('HH:00');
                
                // Find if we have data for this hour
                const hourData = analytics.salesByDay.find(day => 
                  moment(day.date).format('HH:00') === hourStr
                );
                
                // Get the COGS for yesterday
                const yesterdayStr = yesterday.format('YYYY-MM-DD');
                const daysCogs = currentProcessedCogsData[yesterdayStr] || 0;
                
                // Hourly COGS (dividing daily COGS by 24 hours)
                const hourlyCogs = daysCogs / 24;
                
                // Calculate revenue and profit margin
                const revenue = hourData ? hourData.revenue : 0;
                const margin = revenue > 0 && hourlyCogs > 0 ? ((revenue - hourlyCogs) / revenue) * 100 : null;
                
                formattedData.push({
                  name: hourStr,
                  revenue: revenue,
                  orders: hourData ? hourData.orders : 0,
                  profitMargin: margin
                });
              }
            } else if (timeFrame === '6m' || timeFrame === '1yr') {
              // CRITICAL FIX: Completely reprocess the data for both 1yr and 6m views
              // First, we'll create a consistent 12-month dataset, then filter for display
              
              // Always process a full year of data for consistency
              const yearStartMoment = moment().startOf('month').subtract(11, 'months');
              const endMoment = moment().endOf('day');
              
              // Get the key for the current data processing session to ensure same source data
              const dataSetKey = `${yearStartMoment.format('YYYY-MM-DD')}_${endMoment.format('YYYY-MM-DD')}`;
              console.log(`Processing data for set key: ${dataSetKey}`);

              // Process the monthly data if not already in cache
              if (!monthlyAggregatedData[dataSetKey]) {
                console.log('Building monthly data from scratch');
                
                // Build look-up map for daily sales
                const salesMap: Record<string, { revenue: number; orders: number }> = {};
                analytics.salesByDay.forEach(day => {
                  salesMap[day.date] = { revenue: day.revenue, orders: day.orders };
                });

                // Process data month by month
                const processedMonthlyData: Record<string, { revenue: number; orders: number; cogs: number; profitMargin: number | null }> = {};
                
                let cursor = yearStartMoment.clone();
                while (cursor.isSameOrBefore(endMoment, 'day')) {
                  const dateStr = cursor.format('YYYY-MM-DD');
                  const monthKey = cursor.format('YYYY-MM');
                  
                  if (!processedMonthlyData[monthKey]) {
                    processedMonthlyData[monthKey] = { revenue: 0, orders: 0, cogs: 0, profitMargin: null };
                  }

                  const dailySales = salesMap[dateStr] || { revenue: 0, orders: 0 };
                  processedMonthlyData[monthKey].revenue += dailySales.revenue;
                  processedMonthlyData[monthKey].orders += dailySales.orders;
                  processedMonthlyData[monthKey].cogs += currentProcessedCogsData[dateStr] || 0;

                  cursor.add(1, 'day');
                }
                
                // Calculate profit margins for each month
                Object.entries(processedMonthlyData).forEach(([monthKey, data]) => {
                  data.profitMargin = data.revenue > 0 && data.cogs > 0
                    ? parseFloat(((data.revenue - data.cogs) / data.revenue * 100).toFixed(2))
                    : null;
                });
                
                // Store in the cache for reuse
                monthlyAggregatedData[dataSetKey] = processedMonthlyData;
                setMonthlyAggregatedData({...monthlyAggregatedData});
                
                console.log('Monthly data processed and cached', processedMonthlyData);
              } else {
                console.log('Using previously cached monthly data');
              }
              
              // Get months in chronological order
              const allMonths = Object.entries(monthlyAggregatedData[dataSetKey])
                .map(([monthKey, data]) => ({
                  monthKey,
                  name: moment(monthKey, 'YYYY-MM').format('MMM'),
                  revenue: data.revenue,
                  orders: data.orders,
                  profitMargin: data.profitMargin
                }))
                .sort((a, b) => a.monthKey.localeCompare(b.monthKey));
              
              // Filter months based on the timeframe
              if (timeFrame === '6m') {
                // Take only the last 6 months
                formattedData = allMonths.slice(-6);
                console.log('6-month view: filtered to last 6 months of data');
              } else {
                // Use the full year
                formattedData = allMonths;
                console.log('1-year view: using full year of data');
              }
              
              // Final detailed logging for verification
              console.log(`${timeFrame} view showing ${formattedData.length} months:`);
              console.log(`From ${formattedData[0]?.monthKey} to ${formattedData[formattedData.length-1]?.monthKey}`);
              formattedData.forEach(month => {
                console.log(`Month: ${month.monthKey}, Revenue: ${month.revenue}, COGS: ${monthlyAggregatedData[dataSetKey][month.monthKey].cogs}, Profit Margin: ${month.profitMargin?.toFixed(2)}%`);
              });
              
            } else if (timeFrame === '7d' || timeFrame === '7d_refresh') {
              // For 7d, ensure we show all 7 days regardless of data availability
              formattedData = [];
              const endDate = moment().endOf('day');
              const startDate = moment().subtract(6, 'days').startOf('day');
              
              // Build a map of existing sales data by date for fast lookups
              const salesDataByDate: Record<string, any> = {};
              analytics.salesByDay.forEach(day => {
                const dateStr = moment(day.date).format('YYYY-MM-DD');
                salesDataByDate[dateStr] = day;
              });
              
              // For the 7d view, we need a simple, direct approach to ensure profit margins
              // appear consistently across all days
              console.log('7d view: Simplified approach for COGS data from', startDate.format('YYYY-MM-DD'), 'to', endDate.format('YYYY-MM-DD'));
              
              // Find the latest COGS entry as our reference
              let mostRecentCOGS = null;
              let mostRecentDate = null;
              
              if (cogsData && cogsData.length > 0) {
                // Sort COGS data by start date, most recent first
                const sortedCOGS = [...cogsData].sort((a, b) => 
                  moment(b.week_start_date).valueOf() - moment(a.week_start_date).valueOf()
                );
                
                mostRecentCOGS = sortedCOGS[0];
                mostRecentDate = moment(mostRecentCOGS.week_start_date).format('YYYY-MM-DD');
                console.log(`7d view: Found most recent COGS data from ${mostRecentDate}, amount: ${mostRecentCOGS.amount}`);
              } else {
                console.log('7d view: No COGS data available');
              }
              
              // Generate data for all 7 days
              for (let i = 0; i < 7; i++) {
                const currentDate = moment(startDate).add(i, 'days');
                const dateStr = currentDate.format('YYYY-MM-DD');
                const formattedDate = currentDate.format('MMM DD'); 
                const isToday = currentDate.isSame(moment(), 'day');
                
                // Check if we have sales data for this day
                const dayData = salesDataByDate[dateStr];
                const revenue = dayData ? dayData.revenue : 0;
                const orders = dayData ? dayData.orders : 0;
                
                // SIMPLIFIED APPROACH: Use the same COGS value across all days
                // This ensures a consistent profit margin line across the week
                let dayCogs = 0;
                
                // First check if we have specific daily COGS data
                dayCogs = currentProcessedCogsData[dateStr] || processedCogsData[dateStr] || 0;
                
                // If no specific daily data, but we have a weekly value, use that
                if (dayCogs === 0 && mostRecentCOGS) {
                  // Distribute the weekly COGS evenly across all 7 days
                  dayCogs = mostRecentCOGS.amount / 7;
                  console.log(`7d view: Applied weekly COGS to ${dateStr}: $${dayCogs.toFixed(2)}`);
                }
                
                // If we have revenue data but no COGS, add a fallback estimate
                // so we always have margin data (critical for a continuous line)
                if (revenue > 0 && dayCogs === 0) {
                  // Use a simple estimate based on reasonable margins
                  dayCogs = revenue * 0.7; // Assume 30% margin
                  console.log(`7d view: Using estimated COGS for ${dateStr}: $${dayCogs.toFixed(2)}`);
                }
                
                // Calculate profit margin if we have COGS and revenue data
                let profitMargin = null;
                if (revenue > 0 && dayCogs > 0) {
                  profitMargin = parseFloat(((revenue - dayCogs) / revenue * 100).toFixed(2));
                  console.log(`7d view: Calculated margin for ${dateStr}: ${profitMargin.toFixed(2)}% (Rev: $${revenue.toFixed(2)}, COGS: $${dayCogs.toFixed(2)})`);
                }
                
                formattedData.push({
                  name: formattedDate,
                  revenue: revenue,
                  orders: orders,
                  profitMargin: profitMargin,
                  // Add date for debugging
                  date: dateStr
                });
              }
              
              // Log what we're showing
              console.log(`7d view: Showing data from ${startDate.format('YYYY-MM-DD')} to ${endDate.format('YYYY-MM-DD')}`);
              console.log(`7d view: Found data for ${Object.keys(salesDataByDate).length} days`);
            } else if (timeFrame === '1m') {
              // For 1m, ensure we show all 30 days regardless of data availability
              formattedData = [];
              const endDate = moment().endOf('day');
              const startDate = moment().subtract(29, 'days').startOf('day'); // 30 days including today
              
              // Build a map of existing sales data by date for fast lookups
              const salesDataByDate: Record<string, any> = {};
              analytics.salesByDay.forEach(day => {
                const dateStr = moment(day.date).format('YYYY-MM-DD');
                salesDataByDate[dateStr] = day;
              });
              
              // Log available COGS data dates for the 1m view for debugging
              console.log('1m view: Checking for complete COGS data from', startDate.format('YYYY-MM-DD'), 'to', endDate.format('YYYY-MM-DD'));
              
              // Log all available COGS data dates for debugging
              const availableDates = Object.keys(currentProcessedCogsData).sort();
              const availableProcessedDates = Object.keys(processedCogsData).sort();
              console.log('1m available COGS dates (current):', availableDates);
              console.log('1m available COGS dates (processed):', availableProcessedDates);
              
              // Generate data for all 30 days
              for (let i = 0; i < 30; i++) {
                const currentDate = moment(startDate).add(i, 'days');
                const dateStr = currentDate.format('YYYY-MM-DD');
                const formattedDate = currentDate.format('MMM DD');
                const isToday = currentDate.isSame(moment(), 'day');
                const isCurrentWeek = currentDate.isSame(moment(), 'week');
                
                // Check if we have sales data for this day
                const dayData = salesDataByDate[dateStr];
                const revenue = dayData ? dayData.revenue : 0;
                const orders = dayData ? dayData.orders : 0;
                
                // Get COGS data for this day if available - try multiple sources with fallbacks
                // This ensures we don't miss data for today or recent days
                // First attempt to get COGS for the specific day
                let dayCogs = currentProcessedCogsData[dateStr] || processedCogsData[dateStr] || 0;
                
                // If no COGS found for this specific day, check if it belongs to a week with COGS data
                if (dayCogs === 0) {
                  // Try to find COGS data for the week this date belongs to
                  const weekStart = currentDate.clone().startOf('week').format('YYYY-MM-DD');
                  const weekEnd = currentDate.clone().endOf('week').format('YYYY-MM-DD');
                  
                  // Check if we have any COGS entry for this week
                  const weekCOGS = cogsData.find(entry => 
                    moment(entry.week_start_date).format('YYYY-MM-DD') === weekStart ||
                    moment(entry.week_start_date).isSame(moment(weekStart), 'week')
                  );
                  
                  if (weekCOGS) {
                    // We found COGS data for this week, calculate the daily value
                    const daysInWeek = 7; // Standard week
                    dayCogs = weekCOGS.amount / daysInWeek;
                    console.log(`1m view: Found weekly COGS data for ${dateStr}: $${dayCogs.toFixed(2)} (from week starting ${weekStart})`);
                  }
                  // If still no COGS data, and it's today or current week, use the most recent
                  else if (isToday || isCurrentWeek) {
                    // Find the most recent available COGS data
                    const allDates = [...availableDates, ...availableProcessedDates].sort();
                    if (allDates.length > 0) {
                      const mostRecentDate = allDates[allDates.length - 1];
                      dayCogs = currentProcessedCogsData[mostRecentDate] || processedCogsData[mostRecentDate] || 0;
                      console.log(`1m view: Using proxy COGS data for ${dateStr}: $${dayCogs.toFixed(2)} (from ${mostRecentDate})`);
                    }
                  }
                }
                
                // Calculate profit margin if we have COGS and revenue data
                let profitMargin = null;
                if (revenue > 0 && dayCogs > 0) {
                  profitMargin = parseFloat(((revenue - dayCogs) / revenue * 100).toFixed(2));
                  console.log(`1m view: Calculated margin for ${dateStr}: ${profitMargin.toFixed(2)}% (Rev: $${revenue.toFixed(2)}, COGS: $${dayCogs.toFixed(2)})`);
                }
                
                formattedData.push({
                  name: formattedDate,
                  revenue: revenue,
                  orders: orders,
                  profitMargin: profitMargin,
                  // Add date for debugging
                  date: dateStr
                });
              }
              
              // Log what we're showing
              console.log(`1m view: Showing data from ${startDate.format('YYYY-MM-DD')} to ${endDate.format('YYYY-MM-DD')}`);
              console.log(`1m view: Found data for ${Object.keys(salesDataByDate).length} days`);
            } else {
              // Default case to handle any other timeFrame values that might be added in the future
              // This ensures formattedData is always defined before being used
              formattedData = [];
              console.log(`Unhandled timeFrame: ${timeFrame}, using empty data array`);
            }
            
            // Now formattedData is guaranteed to be defined
            setSalesData(formattedData);
            setHasSalesData(true);
          } else if (hasAnySalesData && timeFrame === '1d') {
            // Special case: if we have any sales data but none for yesterday,
            // show empty hourly bars instead of the "Connect POS" message
            const yesterday = moment().subtract(1, 'day').startOf('day');
            const formattedData = [];
            
            for (let i = 0; i < 24; i++) {
              formattedData.push({
                name: moment(yesterday).add(i, 'hours').format('HH:00'),
                revenue: 0,
                orders: 0
              });
            }
            
            setSalesData(formattedData);
            setHasSalesData(true); // We're treating this as having data
          } else {
            // Fallback to mock data if API doesn't provide what we need
            console.log("API Did not provide data")
            //setSalesData(generateMockData(timeFrame));
            setHasSalesData(false);
          }
        } catch (err) {
          console.error('Failed to fetch analytics data:', err);
          
          // If we have any sales data but error on 1d view, show empty day
          if (hasAnySalesData && timeFrame === '1d') {
            const yesterday = moment().subtract(1, 'day').startOf('day');
            const formattedData = [];
            
            for (let i = 0; i < 24; i++) {
              formattedData.push({
                name: moment(yesterday).add(i, 'hours').format('HH:00'),
                revenue: 0,
                orders: 0
              });
            }
            
            setSalesData(formattedData);
            setHasSalesData(true);
          } else {
            // Fallback to mock data
            console.log("API Did not provide data")
            //setSalesData(generateMockData(timeFrame));
          }
        }
        
        setLoading(false);
      } catch (err) {
        console.error('Error fetching sales data:', err);
        setError('Failed to load sales data. Using mock data as fallback.');
        console.log("API Did not provide data")
        //setSalesData(generateMockData(timeFrame));
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
          // Fallback to mock data
          const mockData = generateProductPerformanceData(itemsTimeFrame);
          setProductPerformance(mockData);
          setHasProductsData(false);
        }
        
        setProductsLoading(false);
      } catch (err) {
        console.error('Error fetching product performance:', err);
        // Use mock data as fallback
        const data = generateProductPerformanceData(itemsTimeFrame);
        setProductPerformance(data);
        setProductsLoading(false);
      }
    };
    
    fetchProductPerformance();
  }, [itemsTimeFrame]);
  
  // Fetch competitor data
  useEffect(() => {
    const fetchCompetitorData = async () => {
      try {
        setCompetitorsLoading(true);
        
        // Try to fetch competitor data
        try {
          // Get all competitor names
          const competitorNames = await competitorService.getCompetitors();
          
          // Process each competitor
          const competitorData = [];
          
          for (let i = 0; i < competitorNames.length; i++) {
            const name = competitorNames[i];
            
            try {
              // Calculate similarity score for each competitor
              const similarityData = await competitorService.calculateSimilarityScore(name);
              
              competitorData.push({
                key: String(i + 1),
                name: name,
                similarityScore: similarityData.similarityScore,
                priceSimScore: similarityData.priceSimScore,
                menuSimScore: similarityData.menuSimScore,
                distanceScore: similarityData.distanceScore
              });
            } catch (err) {
              console.error(`Error calculating similarity for ${name}:`, err);
            }
          }
          
          setCompetitors(competitorData);
        } catch (err) {
          console.error('Failed to fetch competitor data:', err);
          // Fallback to empty array
          setCompetitors([]);
        }
        
        setCompetitorsLoading(false);
      } catch (err) {
        console.error('Error fetching competitor data:', err);
        setCompetitors([]);
        setCompetitorsLoading(false);
      }
    };
    
    fetchCompetitorData();
  }, []);  // Empty dependency array means this runs once on component mount
  
  // Add a dedicated useEffect for processing COGS data whenever it changes
  useEffect(() => {
    if (cogsData && cogsData.length > 0) {
      console.log('Processing COGS data, length:', cogsData.length);
      const dailyCogs = processCogsDataToDaily();
      setProcessedCogsData(dailyCogs);
    }
  }, [cogsData]);
  
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
  
  const topProducts = getTopProducts();
  const bottomProducts = getBottomProducts();
  
  return (
    <div>
      <Title level={2}>Dashboard</Title>
      <Title level={5} type="secondary" style={{ marginTop: 0, marginBottom: 24 }}>
        Welcome back, {formattedName}! Here's your dynamic pricing overview
      </Title>
      
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
        ) : !hasSalesData ? (
          <div style={{ width: '100%', height: 300, position: 'relative' }}>
            {/* Blurred sample data in background */}
            <div style={{ width: '100%', height: '100%', filter: 'blur(5px)', opacity: 0.6 }}>
              <ResponsiveContainer>
                <ComposedChart
                  data={generateMockData(timeFrame)}
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
              backgroundColor: 'rgba(255, 255, 255, 0.85)' 
            }}>
              <div style={{ 
                padding: '20px', 
                borderRadius: '8px', 
                textAlign: 'center',
                maxWidth: '80%' 
              }}>
                <p style={{ fontSize: '16px', fontWeight: 500, marginBottom: '8px' }}>No sales data available</p>
                <p style={{ color: '#666', marginBottom: '20px' }}>To see your actual sales data, please connect your POS provider</p>
                <Button type="primary" size="large">
                  Connect POS Provider
                </Button>
              </div>
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
            ) : !hasProductsData ? (
              <div style={{ height: 400, position: 'relative' }}>
                {/* Blurred sample product data in background */}
                <div style={{ width: '100%', height: '100%', filter: 'blur(5px)', opacity: 0.4 }}>
                  <div style={{ opacity: 0.7 }}>
                    {/* Top Products Sample */}
                    <div>
                      <Title level={4} style={{ color: '#3f8600', display: 'flex', alignItems: 'center', marginTop: -5, marginBottom: 16 }}>
                        Best Selling Items
                      </Title>
                      <div style={{ marginBottom: 36 }}>
                        {generateProductPerformanceData(itemsTimeFrame).slice(0, 3).map((product, index) => (
                          <Card
                            key={product.id}
                            style={{ marginBottom: 8, borderRadius: 0, border: 'none'}}
                            size="small"
                            className="dashboard-card-item"
                          >
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                              {/* Product details (simplified) */}
                              <div>
                                <div style={{ display: 'flex', alignItems: 'center' }}>
                                  <strong>{product.name}</strong>
                                </div>
                              </div>
                            </div>
                              </Card>
                        ))}
                      </div>
                    </div>
                  </div>
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
                  backgroundColor: 'rgba(255, 255, 255, 0.85)' 
                }}>
                  <div style={{ 
                    padding: '20px', 
                    borderRadius: '8px', 
                    textAlign: 'center',
                    maxWidth: '80%' 
                  }}>
                    <p style={{ fontSize: '16px', fontWeight: 500, marginBottom: '8px' }}>No menu items available</p>
                    <p style={{ color: '#666', marginBottom: '20px' }}>To view your item performance, please connect your POS provider</p>
                    <Button type="primary" size="large">
                      Connect POS Provider
                    </Button>
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
                                <AntTooltip title="Units Sold">
                                  <span>{formatNumberWithCommas(product.quantitySold || 0)} units</span>
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
                                <AntTooltip title="Units Sold">
                                  <span>{formatNumberWithCommas(product.quantitySold || 0)} units</span>
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
              {!hasProductsData ? (
                <div style={{ position: 'relative' }}>
                  {/* Blurred sample data in background */}
                  <div style={{ filter: 'blur(4px)', opacity: 0.5 }}>
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
                    padding: '20px 0',
                    minHeight: '150px'
                  }}>
                    <div style={{ 
                      padding: '15px', 
                      borderRadius: '8px', 
                      textAlign: 'center',
                      maxWidth: '90%' 
                    }}>
                      <p style={{ fontSize: '16px', fontWeight: 500, marginBottom: '8px' }}>No Adaptiv data available</p>
                      <p style={{ color: '#666', marginBottom: '15px', fontSize: '14px' }}>To view your optimization metrics, please connect your POS provider</p>
                      <Button type="primary">
                        Connect POS Provider
                      </Button>
                    </div>
                  </div>
                </div>
              ) : (
                <>
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
                </>
              )}
                </Card>
            
            {/* Competitor Analysis Card */}
            <Card 
              title="Competitor Analysis" 
              extra={<Button type="link" onClick={() => navigate('/competitor-analysis')}>View All</Button>}
              style={{ width: '100%' }}
            >
              {!hasProductsData ? (
                <div style={{ position: 'relative' }}>
                  {/* Blurred sample data in background */}
                  <div style={{ filter: 'blur(4px)', opacity: 0.5 }}>
                    <Statistic
                      title="Market Position"
                      value="Top 15%"
                      valueStyle={{ color: '#9370DB' }}
                      prefix={<TeamOutlined />}
                    />
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
                    padding: '30px 0',
                    minHeight: '220px'
                  }}>
                    <div style={{ 
                      padding: '15px', 
                      borderRadius: '8px', 
                      textAlign: 'center',
                      maxWidth: '90%' 
                    }}>
                      <p style={{ fontSize: '16px', fontWeight: 500, marginBottom: '8px' }}>No competitor data available</p>
                      <p style={{ color: '#666', marginBottom: '15px', fontSize: '14px' }}>To view competitor analysis, please connect your POS provider</p>
                      <Button type="primary">
                        Connect POS Provider
                      </Button>
                    </div>
                  </div>
                </div>
              ) : (
                <>
                  <Statistic
                    title="Market Position"
                    value="Top 15%"
                    valueStyle={{ color: '#9370DB' }}
                    prefix={<TeamOutlined />}
                  />
                  <div style={{ marginTop: 16 }}>
                    <p>Competitors Tracked: {competitors.length || 'Loading...'}</p>
                    <p>Price Differential: <span style={{ color: '#cf1322' }}><ArrowDownOutlined /> 5.3%</span></p>
                    <p>Feature Parity: 92%</p>
                    
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
                              onClick={() => navigate(`/competitor/${encodeURIComponent(competitor.name)}`)}
                              className="dashboard-competitor-item"
                              style={{ 
                                padding: '8px 6px', 
                                borderBottom: index < getTopCompetitors().length - 1 ? '1px solid #f0f0f0' : 'none',
                                cursor: 'pointer',
                                borderRadius: '4px',
                                transition: 'all 0.3s ease'
                              }}
                            >
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <div style={{ fontWeight: 500 }}>{competitor.name}</div>
                                <div>
                                  <Tag color="blue">{competitor.similarityScore}%</Tag>
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
