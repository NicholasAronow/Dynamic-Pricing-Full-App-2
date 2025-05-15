import api from './api';
import authService from './authService';
import moment from 'moment';

export interface COGSEntry {
  id?: number;
  account_id: string;
  week_start_date: string;
  week_end_date: string;
  amount: number;
  created_at?: string;
  updated_at?: string;
}

// Generate realistic COGS data for testing purposes
const generateHistoricalCOGSData = (userId: string): COGSEntry[] => {
  // Only generate test data for test accounts
  if (!userId.includes('test')) {
    return [];
  }

  const data: COGSEntry[] = [];
  
  // Generate 51 weeks of data (approximately a year)
  for (let i = 0; i < 51; i++) {
    const weekEnd = moment().subtract(i + 1, 'weeks').endOf('week');
    const weekStart = moment(weekEnd).startOf('week');
    
    // Base COGS amount
    let amount = 15000 + Math.random() * 2000;
    
    // Add seasonal variation
    const month = weekEnd.month();
    
    // Higher costs during holiday season (November, December)
    if (month === 10 || month === 11) {
      amount *= 1.4; // 40% increase
    } 
    // Higher costs during summer (June, July, August)
    else if (month >= 5 && month <= 7) {
      amount *= 1.2; // 20% increase
    }
    // Slightly lower in slow months (January, February)
    else if (month === 0 || month === 1) {
      amount *= 0.9; // 10% decrease
    }
    
    // Random variation
    amount *= 0.95 + Math.random() * 0.1;

    data.push({
      account_id: userId,
      week_start_date: weekStart.format('YYYY-MM-DD'),
      week_end_date: weekEnd.format('YYYY-MM-DD'),
      amount: Math.round(amount),
    });
  }
  
  return data;
};

const cogsService = {
  // Get current week's COGS data specifically (for dashboard display)
  getCurrentWeekCOGSData: async (): Promise<COGSEntry[]> => {
    try {
      const user = authService.getCurrentUser();
      if (!user) {
        console.error('User not authenticated');
        return [];
      }
      
      // Define the current week's date range
      const today = moment();
      const startOfWeek = today.clone().startOf('week').format('YYYY-MM-DD');
      const endOfWeek = today.clone().endOf('week').format('YYYY-MM-DD');
      
      console.log(`Fetching current week's COGS data: ${startOfWeek} to ${endOfWeek}`);
      
      // Make API request specifically for current week's data
      const response = await api.get(
        `cogs?account_id=${user.id}&start_date=${startOfWeek}&end_date=${endOfWeek}`
      );
      
      if (response.data && response.data.length > 0) {
        console.log('Found current week COGS data:', response.data);
        return response.data;
      } else {
        console.log('No current week COGS data found');
        return [];
      }
    } catch (error) {
      console.error('Error fetching current week COGS data:', error);
      return [];
    }
  },
  
  // Check if COGS has been entered for the current week
  hasCurrentWeekCOGS: async (): Promise<boolean> => {
    try {
      const currentUser = authService.getCurrentUser();
      if (!currentUser) {
        console.error('User not authenticated');
        return false;
      }
      
      const currentWeekStart = moment().startOf('week');
      const currentWeekEnd = moment().endOf('week');
      
      // Format the dates in ISO format for FastAPI to parse properly
      const formattedStartDate = encodeURIComponent(currentWeekStart.toISOString());
      const formattedEndDate = encodeURIComponent(currentWeekEnd.toISOString());
      
      // Check the database for all users, including test users
      try {
        const response = await api.get(`cogs?account_id=${currentUser.id}&week_start_date=${formattedStartDate}&week_end_date=${formattedEndDate}`);
        return response.data && response.data.length > 0;
      } catch (apiError) {
        console.error('API error checking current week COGS:', apiError);
        return false;
      }
    } catch (error) {
      console.error('Error checking current week COGS:', error);
      return false;
    }
  },
  
  // Get COGS data for a specific time period
  getCOGSData: async (startDate: string, endDate: string): Promise<COGSEntry[]> => {
    console.log(`Fetching COGS data from ${startDate} to ${endDate}`);
    try {
      const currentUser = authService.getCurrentUser();
      if (!currentUser) {
        console.error('User not authenticated');
        return [];
      }
      
      // Use a more inclusive date range for the API query to ensure we get all weeks that overlap
      // with our requested range - this is especially important for weekly COGS data that might
      // span across our exact date range boundaries
      const rangeStart = moment(startDate).subtract(6, 'days'); // Add buffer to ensure we catch any overlapping weeks
      const rangeEnd = moment(endDate).add(6, 'days'); // Add buffer to ensure we catch any overlapping weeks
      
      // Convert string dates to ISO format for the API
      const formattedStartDate = encodeURIComponent(rangeStart.toISOString());
      const formattedEndDate = encodeURIComponent(rangeEnd.toISOString());
      
      console.log(`Using expanded date range for API: ${rangeStart.format('YYYY-MM-DD')} to ${rangeEnd.format('YYYY-MM-DD')}`);
      const response = await api.get(`cogs?account_id=${currentUser.id}&start_date=${formattedStartDate}&end_date=${formattedEndDate}`);
      
      // Log the response data
      console.log(`API returned ${response.data.length} COGS entries`);
      if (response.data.length > 0) {
        console.log('First entry:', response.data[0]);
        if (response.data.length > 1) {
          console.log('Last entry:', response.data[response.data.length-1]);
        }
        
        // Filter to only include entries that overlap with our original date range
        const filteredData = response.data.filter((entry: COGSEntry) => {
          const entryStart = moment(entry.week_start_date);
          const entryEnd = moment(entry.week_end_date);
          const requestStart = moment(startDate);
          const requestEnd = moment(endDate);
          
          return entryStart.isSameOrBefore(requestEnd) && entryEnd.isSameOrAfter(requestStart);
        });
        
        console.log(`After filtering API response: ${filteredData.length} COGS entries match the requested range`);
        return filteredData;
      }
      
      return response.data;
    } catch (error) {
      console.error('Error fetching COGS data:', error);
      return [];
    }
  },
  
  // Submit COGS data for a specific week
  submitCOGS: async (amount: number): Promise<boolean> => {
    try {
      const currentUser = authService.getCurrentUser();
      if (!currentUser) {
        console.error('User not authenticated');
        return false;
      }
      
      const weekStart = moment().startOf('week');
      const weekEnd = moment().endOf('week');
      
      // Send data to API for all users, including test users
      try {
        const payload = {
          user_id: currentUser.id,
          week_start_date: weekStart.toISOString(),
          week_end_date: weekEnd.toISOString(),
          amount: amount
        };
        
        await api.post('cogs', payload);
        console.log('COGS data sent to API successfully');
        return true;
      } catch (apiError) {
        console.error('API error submitting COGS data:', apiError);
        return false;
      }
    } catch (error) {
      console.error('Error submitting COGS data:', error);
      return false;
    }
  },
  
  // Get all historical COGS data
  getAllCOGSData: async (): Promise<COGSEntry[]> => {
    try {
      const currentUser = authService.getCurrentUser();
      if (!currentUser) {
        console.error('User not authenticated');
        return [];
      }
      
      try {
        const response = await api.get(`cogs?account_id=${currentUser.id}`);
        return response.data;
      } catch (apiError) {
        console.error('API error fetching all COGS data:', apiError);
        return [];
      }
    } catch (error) {
      console.error('Error getting all COGS data:', error);
      return [];
    }
  }
};

export default cogsService;
