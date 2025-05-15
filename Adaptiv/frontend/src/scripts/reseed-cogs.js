// Script to reseed COGS data from the terminal
const moment = require('moment');

// Mock user ID (testprofessional@test.com account)
const TEST_USER_ID = 'testprofessional123';

// Function to generate COGS data for a specific week
const generateCOGSDataForWeek = (userId, weekNumber) => {
  // If it's the current week (weekNumber = 0), use a more predictable amount
  if (weekNumber === 0) {
    const weekStart = moment().startOf('week');
    const weekEnd = moment().endOf('week');
    
    return {
      account_id: userId,
      week_start_date: weekStart.format('YYYY-MM-DD'),
      week_end_date: weekEnd.format('YYYY-MM-DD'),
      amount: 5000, // Reduced to $5,000 for current week
      created_at: new Date().toISOString()
    };
  }
  
  // For historical weeks
  const weekEnd = moment().subtract(weekNumber, 'weeks').endOf('week');
  const weekStart = moment(weekEnd).startOf('week');
  
  // Base COGS amount - dramatically reduced to $4,000
  let amount = 4000 + Math.random() * 1000;
  
  // Add seasonal variation
  const month = weekEnd.month();
  
  // Higher costs during holiday season (November, December) but still lower than before
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
    account_id: userId,
    week_start_date: weekStart.format('YYYY-MM-DD'),
    week_end_date: weekEnd.format('YYYY-MM-DD'),
    amount: Math.round(amount),
    created_at: new Date().toISOString()
  };
};

const getStorageKey = (userId, weekStart) => {
  return `adaptiv_cogs_${userId}_${weekStart}`;
};

const clearExistingCOGSData = (userId) => {
  // In a browser environment, we'd use localStorage
  // Here we'll use a hybrid approach that works in Node.js
  
  // Check if we have localStorage (browser) or need to use global.localStorage (Node)
  const storage = typeof localStorage !== 'undefined' ? localStorage : global.localStorage;
  
  if (!storage) {
    console.error('LocalStorage not available in this environment');
    return 0;
  }
  
  // Remove all existing COGS data for this user
  const keysToRemove = [];
  
  for (let i = 0; i < storage.length; i++) {
    const key = storage.key(i);
    if (key && key.startsWith(`adaptiv_cogs_${userId}`)) {
      keysToRemove.push(key);
    }
  }
  
  // Remove the keys
  keysToRemove.forEach(key => {
    storage.removeItem(key);
  });
  
  return keysToRemove.length;
};

const reseedCOGSData = async (userId = TEST_USER_ID) => {
  try {
    if (!userId.includes('test')) {
      console.error('COGS reseeding is only available for test accounts');
      return;
    }
    
    console.log(`Starting COGS data reseeding for user ${userId}`);
    
    // Clear existing COGS data
    const removedCount = clearExistingCOGSData(userId);
    console.log(`Cleared ${removedCount} existing COGS entries`);
    
    // Generate and store 55 weeks of data (including current week)
    const totalWeeks = 55;
    
    // Prepare localStorage if needed
    if (typeof localStorage === 'undefined') {
      // Mock localStorage for Node.js environment
      console.log('Setting up mock localStorage for Node.js environment');
      global.localStorage = {
        _data: {},
        setItem: function(id, val) { this._data[id] = val; },
        getItem: function(id) { return this._data[id] ? this._data[id] : null; },
        removeItem: function(id) { delete this._data[id]; },
        get length() { return Object.keys(this._data).length; },
        key: function(i) { return Object.keys(this._data)[i]; }
      };
    }
    
    // Access storage
    const storage = typeof localStorage !== 'undefined' ? localStorage : global.localStorage;
    
    for (let i = 0; i < totalWeeks; i++) {
      const weekData = generateCOGSDataForWeek(userId, i);
      const key = getStorageKey(userId, weekData.week_start_date);
      storage.setItem(key, JSON.stringify(weekData));
      
      // Log progress periodically
      if (i === 0) {
        console.log(`Added current week COGS data (${weekData.week_start_date} to ${weekData.week_end_date}): $${weekData.amount.toLocaleString()}`);
      } else if (i === totalWeeks - 1) {
        console.log(`Added oldest week COGS data (${weekData.week_start_date} to ${weekData.week_end_date}): $${weekData.amount.toLocaleString()}`);
      } else if (i % 10 === 0) {
        console.log(`Added week ${i} COGS data (${weekData.week_start_date}): $${weekData.amount.toLocaleString()}`);
      }
    }
    
    console.log(`Successfully reseeded 55 weeks of COGS data for ${userId}`);
    console.log('✅ Reseeding completed successfully');
    
  } catch (error) {
    console.error('Error reseeding COGS data:', error);
  }
};

// Execute the reseeding
reseedCOGSData();
