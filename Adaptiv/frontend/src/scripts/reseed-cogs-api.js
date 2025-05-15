// Script to reseed COGS data from the terminal using the API
const axios = require('axios');
const moment = require('moment');

// Base API URL - adjust if your API is on a different port
const API_BASE_URL = 'http://localhost:8000/api';

// Test user ID - adjust to match your test account
const TEST_USER_ID = 'testprofessional123';

// Function to generate COGS data for a specific week with lower values
const generateCOGSDataForWeek = (userId, weekNumber) => {
  // If it's the current week (weekNumber = 0), use a more predictable amount
  if (weekNumber === 0) {
    const weekStart = moment().startOf('week');
    const weekEnd = moment().endOf('week');
    
    return {
      user_id: userId,
      week_start_date: weekStart.toISOString(),
      week_end_date: weekEnd.toISOString(),
      amount: 5000, // Reduced to $5,000 for current week
    };
  }
  
  // For historical weeks
  const weekEnd = moment().subtract(weekNumber, 'weeks').endOf('week');
  const weekStart = moment(weekEnd).startOf('week');
  
  // Base COGS amount - dramatically reduced to $4,000
  let amount = 4000 + Math.random() * 1000;
  
  // Add seasonal variation
  const month = weekEnd.month();
  
  // Higher costs during holiday season (November, December)
  if (month === 10 || month === 11) {
    amount *= 1.25; // 25% increase
  } 
  // Higher costs during summer (June, July, August)
  else if (month >= 5 && month <= 7) {
    amount *= 1.15; // 15% increase
  }
  // Slightly lower in slow months (January, February)
  else if (month === 0 || month === 1) {
    amount *= 0.9; // 10% decrease
  }
  
  // Random variation
  amount *= 0.95 + Math.random() * 0.1;
  
  return {
    user_id: userId,
    week_start_date: weekStart.toISOString(),
    week_end_date: weekEnd.toISOString(),
    amount: Math.round(amount),
  };
};

// First we need to get a token to authenticate our API requests
const getAuthToken = async () => {
  try {
    // This is just for demo purposes - in a real app, you'd use a proper login endpoint
    // We're using the session token in browser localStorage directly
    if (typeof localStorage !== 'undefined') {
      const userJsonString = localStorage.getItem('adaptiv_user');
      if (userJsonString) {
        const user = JSON.parse(userJsonString);
        return user.token;
      }
    }
    
    // If we're running from Node.js and can't access localStorage, 
    // display how to get the token from the browser
    console.log('Running from Node.js - please copy your auth token from browser localStorage');
    console.log('In browser console, run: JSON.parse(localStorage.getItem("adaptiv_user")).token');
    
    // Using a fake token for demonstration
    // In production, this would be a proper JWT token
    return 'sample_token_for_demo';
  } catch (error) {
    console.error('Error getting auth token:', error.message);
    return null;
  }
};

// Function to delete all existing COGS data for a user
const clearExistingCOGSData = async (userId, token) => {
  try {
    // We can't actually bulk delete with the current API, so we'll list and delete individually
    const response = await axios.get(`${API_BASE_URL}/cogs?account_id=${userId}`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    
    // Get all COGS entries for this user
    const entries = response.data || [];
    console.log(`Found ${entries.length} existing COGS entries to delete`);
    
    // Delete each entry individually
    let deletedCount = 0;
    for (const entry of entries) {
      try {
        await axios.delete(`${API_BASE_URL}/cogs/${entry.id}`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        deletedCount++;
      } catch (err) {
        console.error(`Error deleting COGS entry ${entry.id}:`, err.message);
      }
    }
    
    console.log(`Successfully deleted ${deletedCount} entries`);
    return deletedCount;
  } catch (error) {
    console.error('Error clearing COGS data:', error.message);
    return 0;
  }
};

// Function to submit COGS data for a specific week
const submitCOGSData = async (data, token) => {
  try {
    await axios.post(`${API_BASE_URL}/cogs`, data, {
      headers: { 
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });
    return true;
  } catch (error) {
    console.error(`Error submitting COGS data: ${error.message}`);
    if (error.response) {
      console.error('Response status:', error.response.status);
      console.error('Response data:', error.response.data);
    }
    return false;
  }
};

// Main function to reseed COGS data
const reseedCOGSData = async (userId = TEST_USER_ID) => {
  try {
    console.log(`Starting COGS data reseeding for user ${userId}`);
    
    // Get auth token first
    const token = await getAuthToken();
    if (!token) {
      console.error('Failed to get authentication token. Cannot proceed.');
      return;
    }
    console.log('Successfully obtained authentication token.');
    
    // Clear existing COGS data
    console.log('Deleting existing COGS entries from database...');
    await clearExistingCOGSData(userId, token);
    
    // Generate and store 55 weeks of data (including current week)
    const totalWeeks = 55;
    let successCount = 0;
    
    for (let i = 0; i < totalWeeks; i++) {
      const weekData = generateCOGSDataForWeek(userId, i);
      
      // Send to API
      const success = await submitCOGSData(weekData, token);
      if (success) {
        successCount++;
        
        // Format dates for display
        const startDisplay = moment(weekData.week_start_date).format('YYYY-MM-DD');
        const endDisplay = moment(weekData.week_end_date).format('YYYY-MM-DD');
        
        if (i === 0) {
          console.log(`Added current week COGS data (${startDisplay} to ${endDisplay}): $${weekData.amount.toLocaleString()}`);
        } else if (i === totalWeeks - 1) {
          console.log(`Added oldest week COGS data (${startDisplay} to ${endDisplay}): $${weekData.amount.toLocaleString()}`);
        } else if (i % 10 === 0) {
          console.log(`Added week ${i} COGS data (${startDisplay}): $${weekData.amount.toLocaleString()}`);
        }
      }
      
      // Progress indicator
      process.stdout.write(`Progress: ${Math.round(((i + 1) / totalWeeks) * 100)}%\r`);
      
      // Small delay to avoid overwhelming the API
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    
    console.log(`\n✅ Reseeding completed successfully! (${successCount}/${totalWeeks} weeks)`);
    
  } catch (error) {
    console.error('Error reseeding COGS data:', error);
  }
};

// Execute the reseeding
reseedCOGSData()
  .then(() => {
    console.log('Done.');
  })
  .catch(err => {
    console.error('Script execution failed:', err);
  });
