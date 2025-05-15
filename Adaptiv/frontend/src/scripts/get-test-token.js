// A simple script to help extract a user token from localStorage
const fs = require('fs');

console.log(`
=========================================
HOW TO GET YOUR AUTHENTICATION TOKEN
=========================================

This script can't directly access your browser's localStorage.
To get your auth token, follow these steps:

1. Open the Adaptiv app in your browser
2. Open the browser developer tools (F12 or right-click > Inspect)
3. Go to the Console tab
4. Run this command:
   
   copy(JSON.parse(localStorage.getItem("adaptiv_user")).token)
   
5. Your token has been copied to clipboard
6. Create a file named 'auth-token.txt' with just this token
7. Run the reseed script with:
   
   node src/scripts/reseed-cogs-auth.js

=========================================
`);

// Check if token file exists
if (fs.existsSync('./auth-token.txt')) {
  console.log('Found auth-token.txt file!');
  const token = fs.readFileSync('./auth-token.txt', 'utf8').trim();
  console.log(`Token starts with: ${token.substring(0, 15)}...`);
  console.log('You can now run the reseeding script.');
} else {
  console.log('No auth-token.txt file found. Please create one with your token.');
}
