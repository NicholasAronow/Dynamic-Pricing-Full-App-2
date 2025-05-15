// Run this entire script in the browser console to load COGS data
// Make sure you're logged in as testprofessional@test.com

function loadCOGSData() {
  const currentUser = JSON.parse(localStorage.getItem('adaptiv_current_user'));
  if (!currentUser || !currentUser.id || !String(currentUser.id).includes('test')) {
    console.error('Please log in as testprofessional@test.com first');
    return false;
  }

  const userId = String(currentUser.id);
  console.log(`Loading COGS data for user ID: ${userId}`);

  // Clear existing COGS data
  const keysToRemove = [];
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i);
    if (key && key.startsWith(`adaptiv_cogs_${userId}`)) {
      keysToRemove.push(key);
    }
  }

  keysToRemove.forEach(key => {
    localStorage.removeItem(key);
  });
  console.log(`Cleared ${keysToRemove.length} existing COGS entries`);

  // COGS data to load
  const cogsData = [
  {
    "account_id": "testprofessional",
    "week_start_date": "2025-05-11",
    "week_end_date": "2025-05-17",
    "amount": 20000,
    "created_at": "2025-05-13T22:56:59.389Z"
  },
  {
    "account_id": "testprofessional",
    "week_start_date": "2025-05-04",
    "week_end_date": "2025-05-10",
    "amount": 15896,
    "created_at": "2025-05-08T03:59:59.999Z"
  },
  {
    "account_id": "testprofessional",
    "week_start_date": "2025-04-27",
    "week_end_date": "2025-05-03",
    "amount": 15620,
    "created_at": "2025-04-29T03:59:59.999Z"
  },
  {
    "account_id": "testprofessional",
    "week_start_date": "2025-04-20",
    "week_end_date": "2025-04-26",
    "amount": 15372,
    "created_at": "2025-04-22T03:59:59.999Z"
  },
  {
    "account_id": "testprofessional",
    "week_start_date": "2025-04-13",
    "week_end_date": "2025-04-19",
    "amount": 14457,
    "created_at": "2025-04-14T03:59:59.999Z"
  },
  {
    "account_id": "testprofessional",
    "week_start_date": "2025-04-06",
    "week_end_date": "2025-04-12",
    "amount": 16384,
    "created_at": "2025-04-08T03:59:59.999Z"
  },
  {
    "account_id": "testprofessional",
    "week_start_date": "2025-03-30",
    "week_end_date": "2025-04-05",
    "amount": 16160,
    "created_at": "2025-04-06T03:59:59.999Z"
  },
  {
    "account_id": "testprofessional",
    "week_start_date": "2025-03-23",
    "week_end_date": "2025-03-29",
    "amount": 16065,
    "created_at": "2025-03-26T03:59:59.999Z"
  },
  {
    "account_id": "testprofessional",
    "week_start_date": "2025-03-16",
    "week_end_date": "2025-03-22",
    "amount": 16808,
    "created_at": "2025-03-19T03:59:59.999Z"
  },
  {
    "account_id": "testprofessional",
    "week_start_date": "2025-03-09",
    "week_end_date": "2025-03-15",
    "amount": 16757,
    "created_at": "2025-03-14T03:59:59.999Z"
  },
  {
    "account_id": "testprofessional",
    "week_start_date": "2025-03-02",
    "week_end_date": "2025-03-08",
    "amount": 15674,
    "created_at": "2025-03-07T04:59:59.999Z"
  },
  {
    "account_id": "testprofessional",
    "week_start_date": "2025-02-23",
    "week_end_date": "2025-03-01",
    "amount": 16471,
    "created_at": "2025-02-25T04:59:59.999Z"
  },
  {
    "account_id": "testprofessional",
    "week_start_date": "2025-02-16",
    "week_end_date": "2025-02-22",
    "amount": 15493,
    "created_at": "2025-02-18T04:59:59.999Z"
  },
  {
    "account_id": "testprofessional",
    "week_start_date": "2025-02-09",
    "week_end_date": "2025-02-15",
    "amount": 14988,
    "created_at": "2025-02-12T04:59:59.999Z"
  },
  {
    "account_id": "testprofessional",
    "week_start_date": "2025-02-02",
    "week_end_date": "2025-02-08",
    "amount": 13441,
    "created_at": "2025-02-09T04:59:59.999Z"
  },
  {
    "account_id": "testprofessional",
    "week_start_date": "2025-01-26",
    "week_end_date": "2025-02-01",
    "amount": 14550,
    "created_at": "2025-01-31T04:59:59.999Z"
  },
  {
    "account_id": "testprofessional",
    "week_start_date": "2025-01-19",
    "week_end_date": "2025-01-25",
    "amount": 14425,
    "created_at": "2025-01-22T04:59:59.999Z"
  },
  {
    "account_id": "testprofessional",
    "week_start_date": "2025-01-12",
    "week_end_date": "2025-01-18",
    "amount": 14318,
    "created_at": "2025-01-15T04:59:59.999Z"
  },
  {
    "account_id": "testprofessional",
    "week_start_date": "2025-01-05",
    "week_end_date": "2025-01-11",
    "amount": 13358,
    "created_at": "2025-01-06T04:59:59.999Z"
  },
  {
    "account_id": "testprofessional",
    "week_start_date": "2024-12-29",
    "week_end_date": "2025-01-04",
    "amount": 14583,
    "created_at": "2025-01-01T04:59:59.999Z"
  },
  {
    "account_id": "testprofessional",
    "week_start_date": "2024-12-22",
    "week_end_date": "2024-12-28",
    "amount": 21939,
    "created_at": "2024-12-25T04:59:59.999Z"
  },
  {
    "account_id": "testprofessional",
    "week_start_date": "2024-12-15",
    "week_end_date": "2024-12-21",
    "amount": 21344,
    "created_at": "2024-12-17T04:59:59.999Z"
  },
  {
    "account_id": "testprofessional",
    "week_start_date": "2024-12-08",
    "week_end_date": "2024-12-14",
    "amount": 23009,
    "created_at": "2024-12-09T04:59:59.999Z"
  },
  {
    "account_id": "testprofessional",
    "week_start_date": "2024-12-01",
    "week_end_date": "2024-12-07",
    "amount": 21553,
    "created_at": "2024-12-04T04:59:59.999Z"
  },
  {
    "account_id": "testprofessional",
    "week_start_date": "2024-11-24",
    "week_end_date": "2024-11-30",
    "amount": 23850,
    "created_at": "2024-11-27T04:59:59.999Z"
  },
  {
    "account_id": "testprofessional",
    "week_start_date": "2024-11-17",
    "week_end_date": "2024-11-23",
    "amount": 22112,
    "created_at": "2024-11-20T04:59:59.999Z"
  },
  {
    "account_id": "testprofessional",
    "week_start_date": "2024-11-10",
    "week_end_date": "2024-11-16",
    "amount": 23481,
    "created_at": "2024-11-17T04:59:59.999Z"
  },
  {
    "account_id": "testprofessional",
    "week_start_date": "2024-11-03",
    "week_end_date": "2024-11-09",
    "amount": 22043,
    "created_at": "2024-11-07T04:59:59.999Z"
  },
  {
    "account_id": "testprofessional",
    "week_start_date": "2024-10-27",
    "week_end_date": "2024-11-02",
    "amount": 22395,
    "created_at": "2024-10-31T03:59:59.999Z"
  },
  {
    "account_id": "testprofessional",
    "week_start_date": "2024-10-20",
    "week_end_date": "2024-10-26",
    "amount": 15910,
    "created_at": "2024-10-24T03:59:59.999Z"
  },
  {
    "account_id": "testprofessional",
    "week_start_date": "2024-10-13",
    "week_end_date": "2024-10-19",
    "amount": 15255,
    "created_at": "2024-10-14T03:59:59.999Z"
  },
  {
    "account_id": "testprofessional",
    "week_start_date": "2024-10-06",
    "week_end_date": "2024-10-12",
    "amount": 16728,
    "created_at": "2024-10-11T03:59:59.999Z"
  },
  {
    "account_id": "testprofessional",
    "week_start_date": "2024-09-29",
    "week_end_date": "2024-10-05",
    "amount": 15709,
    "created_at": "2024-10-06T03:59:59.999Z"
  },
  {
    "account_id": "testprofessional",
    "week_start_date": "2024-09-22",
    "week_end_date": "2024-09-28",
    "amount": 15706,
    "created_at": "2024-09-29T03:59:59.999Z"
  },
  {
    "account_id": "testprofessional",
    "week_start_date": "2024-09-15",
    "week_end_date": "2024-09-21",
    "amount": 17128,
    "created_at": "2024-09-17T03:59:59.999Z"
  },
  {
    "account_id": "testprofessional",
    "week_start_date": "2024-09-08",
    "week_end_date": "2024-09-14",
    "amount": 14358,
    "created_at": "2024-09-12T03:59:59.999Z"
  },
  {
    "account_id": "testprofessional",
    "week_start_date": "2024-09-01",
    "week_end_date": "2024-09-07",
    "amount": 15120,
    "created_at": "2024-09-04T03:59:59.999Z"
  },
  {
    "account_id": "testprofessional",
    "week_start_date": "2024-08-25",
    "week_end_date": "2024-08-31",
    "amount": 19827,
    "created_at": "2024-08-27T03:59:59.999Z"
  },
  {
    "account_id": "testprofessional",
    "week_start_date": "2024-08-18",
    "week_end_date": "2024-08-24",
    "amount": 20945,
    "created_at": "2024-08-25T03:59:59.999Z"
  },
  {
    "account_id": "testprofessional",
    "week_start_date": "2024-08-11",
    "week_end_date": "2024-08-17",
    "amount": 18251,
    "created_at": "2024-08-17T03:59:59.999Z"
  },
  {
    "account_id": "testprofessional",
    "week_start_date": "2024-08-04",
    "week_end_date": "2024-08-10",
    "amount": 18436,
    "created_at": "2024-08-06T03:59:59.999Z"
  },
  {
    "account_id": "testprofessional",
    "week_start_date": "2024-07-28",
    "week_end_date": "2024-08-03",
    "amount": 19243,
    "created_at": "2024-08-01T03:59:59.999Z"
  },
  {
    "account_id": "testprofessional",
    "week_start_date": "2024-07-21",
    "week_end_date": "2024-07-27",
    "amount": 18976,
    "created_at": "2024-07-22T03:59:59.999Z"
  },
  {
    "account_id": "testprofessional",
    "week_start_date": "2024-07-14",
    "week_end_date": "2024-07-20",
    "amount": 20127,
    "created_at": "2024-07-16T03:59:59.999Z"
  },
  {
    "account_id": "testprofessional",
    "week_start_date": "2024-07-07",
    "week_end_date": "2024-07-13",
    "amount": 19373,
    "created_at": "2024-07-09T03:59:59.999Z"
  },
  {
    "account_id": "testprofessional",
    "week_start_date": "2024-06-30",
    "week_end_date": "2024-07-06",
    "amount": 19400,
    "created_at": "2024-07-04T03:59:59.999Z"
  },
  {
    "account_id": "testprofessional",
    "week_start_date": "2024-06-23",
    "week_end_date": "2024-06-29",
    "amount": 19357,
    "created_at": "2024-06-25T03:59:59.999Z"
  },
  {
    "account_id": "testprofessional",
    "week_start_date": "2024-06-16",
    "week_end_date": "2024-06-22",
    "amount": 20104,
    "created_at": "2024-06-21T03:59:59.999Z"
  },
  {
    "account_id": "testprofessional",
    "week_start_date": "2024-06-09",
    "week_end_date": "2024-06-15",
    "amount": 18687,
    "created_at": "2024-06-15T03:59:59.999Z"
  },
  {
    "account_id": "testprofessional",
    "week_start_date": "2024-06-02",
    "week_end_date": "2024-06-08",
    "amount": 18590,
    "created_at": "2024-06-03T03:59:59.999Z"
  },
  {
    "account_id": "testprofessional",
    "week_start_date": "2024-05-26",
    "week_end_date": "2024-06-01",
    "amount": 19212,
    "created_at": "2024-05-29T03:59:59.999Z"
  },
  {
    "account_id": "testprofessional",
    "week_start_date": "2024-05-19",
    "week_end_date": "2024-05-25",
    "amount": 17526,
    "created_at": "2024-05-20T03:59:59.999Z"
  },
  {
    "account_id": "testprofessional",
    "week_start_date": "2024-05-12",
    "week_end_date": "2024-05-18",
    "amount": 16903,
    "created_at": "2024-05-13T03:59:59.999Z"
  },
  {
    "account_id": "testprofessional",
    "week_start_date": "2024-05-05",
    "week_end_date": "2024-05-11",
    "amount": 16992,
    "created_at": "2024-05-08T03:59:59.999Z"
  },
  {
    "account_id": "testprofessional",
    "week_start_date": "2024-04-28",
    "week_end_date": "2024-05-04",
    "amount": 17091,
    "created_at": "2024-05-02T03:59:59.999Z"
  }
];

  // Load the data into localStorage
  let loadedCount = 0;
  cogsData.forEach(entry => {
    const key = `adaptiv_cogs_${userId}_${entry.week_start_date}`;
    localStorage.setItem(key, JSON.stringify(entry));
    loadedCount++;
  });

  console.log(`✅ Successfully loaded ${loadedCount} weeks of COGS data for user ${userId}`);
  console.log('✅ Refresh the page to see the updated data');
  return true;
}

// Execute the function
loadCOGSData();