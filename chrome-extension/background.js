/**
 * Extend Your Memory - Chrome Extension Background Script
 * Provides secure Chrome history access via Chrome Extension API
 */

// Initialize extension
chrome.runtime.onInstalled.addListener(() => {
  console.log('Extend Your Memory extension installed');
  initializeExtension();
});

chrome.runtime.onStartup.addListener(() => {
  console.log('Extension started');
  initializeExtension();
});

async function initializeExtension() {
  console.log('Initializing Extend Your Memory extension...');
  
  try {
    await registerWithServer();
    
    // Set up periodic sync only if registration was successful
    if (isRegistered) {
      chrome.alarms.create('periodicSync', { periodInMinutes: 15 });
      console.log('✓ Extension initialized successfully');
    } else {
      console.log('⚠️ Extension initialized but server connection failed');
      console.log('   The extension will retry connecting when servers are available');
    }
  } catch (error) {
    console.error('Error during extension initialization:', error);
    console.log('⚠️ Extension will continue to work in offline mode');
  }
}

// Handle messages from content scripts or popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'searchHistory') {
    handleHistorySearch(request.params, sendResponse);
    return true; // Keep message channel open for async response
  } else if (request.action === 'getRecentHistory') {
    handleRecentHistory(request.params, sendResponse);
    return true;
  } else if (request.action === 'refreshHistory') {
    // Try to register with server if not already registered
    if (!isRegistered) {
      registerWithServer().then(() => {
        sendHistoryToServer().then(() => {
          sendResponse({success: true, message: 'History refreshed'});
        }).catch((error) => {
          sendResponse({success: false, error: error.message});
        });
      }).catch((error) => {
        sendResponse({success: false, error: 'Server connection failed: ' + error.message});
      });
    } else {
      sendHistoryToServer().then(() => {
        sendResponse({success: true, message: 'History refreshed'});
      }).catch((error) => {
        sendResponse({success: false, error: error.message});
      });
    }
    return true;
  }
});

// Server communication configuration
// Default URL can be overridden by environment variable or chrome.storage
const DEFAULT_SERVER_URL =
  typeof process !== 'undefined' && process.env && process.env.SERVER_URL
    ? process.env.SERVER_URL
    : 'http://localhost:8501';

let isRegistered = false;

async function getServerUrl() {
  return new Promise((resolve) => {
    chrome.storage.local.get(['serverUrl'], (result) => {
      if (result.serverUrl) {
        resolve(result.serverUrl);
      } else {
        resolve(DEFAULT_SERVER_URL);
      }
    });
  });
}

// Register extension with server on startup
async function registerWithServer() {
  try {
    const serverUrl = await getServerUrl();
    console.log('Attempting to register with server:', serverUrl);
    
    const response = await fetch(`${serverUrl}/api/chrome/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        extension_id: chrome.runtime.id,
        version: chrome.runtime.getManifest().version,
        capabilities: ['history_search', 'recent_history']
      })
    });
    
    if (response.ok) {
      const result = await response.json();
      console.log('Successfully registered with server:', result);
      isRegistered = true;
      
      // Send initial history data
      await sendHistoryToServer();
    } else {
      console.error('Failed to register with server:', response.status, response.statusText);
      console.error('Server response:', await response.text().catch(() => 'Unable to read response'));
    }
  } catch (error) {
    console.error('Error registering with server:', error);
    console.error('This is normal if the MCP server is not running.');
    console.error('Please start the server with: docker-compose up or npm run dev');
    
    // Don't throw the error - just log it and continue
    isRegistered = false;
  }
}

// Send history data to server
async function sendHistoryToServer(keywords = [], maxResults = 1000) {
  try {
    if (!isRegistered) {
      console.log('Not registered with server, skipping history sync');
      return;
    }
    
    console.log('Starting history sync to server...');
    
    // Get comprehensive history - last 30 days
    const historyItems = await chrome.history.search({
      text: '',
      maxResults: maxResults,
      startTime: Date.now() - (30 * 24 * 60 * 60 * 1000) // Last 30 days
    });
    
    console.log(`Fetched ${historyItems.length} history items from Chrome`);
    
    // Basic history items - all keyword generation will be done by LLM on server
    const enhancedItems = historyItems.map(item => ({
      url: item.url,
      title: item.title || 'Untitled',
      lastVisitTime: item.lastVisitTime,
      visitCount: item.visitCount || 1,
      typedCount: item.typedCount || 0,
      // Extract domain for basic metadata only
      domain: new URL(item.url).hostname
    }));
    
    // Send to server
    const serverUrl = await getServerUrl();
    const response = await fetch(`${serverUrl}/api/chrome/history`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        history_items: enhancedItems,
        client_id: chrome.runtime.id,
        timestamp: Date.now(),
        total_items: enhancedItems.length,
        sync_type: 'full_sync'
      })
    });
    
    if (response.ok) {
      const result = await response.json();
      console.log(`✓ History data sent to server: ${enhancedItems.length} items`);
      console.log('Server response:', result);
    } else {
      const errorText = await response.text();
      console.error(`✗ Failed to send history to server: ${response.status} - ${errorText}`);
    }
  } catch (error) {
    console.error('✗ Error sending history to server:', error);
    console.error('This error is expected if the MCP server is not running.');
    
    // Mark as not registered so we can retry later
    isRegistered = false;
  }
}

// Note: All keyword extraction and categorization is now handled by LLM on the server
// Chrome Extension only provides raw history data

// Handle external messages from MCP server
chrome.runtime.onMessageExternal.addListener(async (request, sender, sendResponse) => {
  const serverUrl = await getServerUrl();
  // Verify sender is from our allowed origins
  const allowedOrigins = [
    serverUrl,
    serverUrl.replace('http://', 'https://'),
    'http://localhost:8501',
    'http://localhost:8000'
  ];
  
  if (!allowedOrigins.includes(sender.origin)) {
    sendResponse({error: 'Unauthorized origin'});
    return;
  }
  
  if (request.action === 'searchHistory') {
    handleHistorySearch(request.params, sendResponse);
    return true;
  } else if (request.action === 'getRecentHistory') {
    handleRecentHistory(request.params, sendResponse);
    return true;
  } else if (request.action === 'refreshHistory') {
    sendHistoryToServer().then(() => {
      sendResponse({success: true, message: 'History refreshed'});
    });
    return true;
  }
});

/**
 * Search Chrome history based on keywords
 */
async function handleHistorySearch(params, sendResponse) {
  try {
    const {
      keywords = [],
      days = 30,
      maxResults = 50
    } = params;
    
    console.log(`History search request: keywords=${JSON.stringify(keywords)}, days=${days}, maxResults=${maxResults}`);
    
    // Calculate start time (days ago)
    const startTime = Date.now() - (days * 24 * 60 * 60 * 1000);
    console.log(`Search start time: ${new Date(startTime).toISOString()}`);
    
    let allResults = [];
    
    if (keywords.length === 0) {
      // If no keywords, get recent history
      console.log('Searching for recent history without keywords...');
      const results = await chrome.history.search({
        text: '',
        startTime: startTime,
        maxResults: maxResults
      });
      console.log(`Raw search results (no keywords): ${results.length} items`);
      allResults = results;
    } else {
      // Search for each keyword
      console.log(`Searching for keywords: ${keywords.join(', ')}`);
      for (const keyword of keywords) {
        try {
          const results = await chrome.history.search({
            text: keyword,
            startTime: startTime,
            maxResults: Math.ceil(maxResults / keywords.length)
          });
          console.log(`Raw search results for "${keyword}": ${results.length} items`);
          allResults = allResults.concat(results);
        } catch (error) {
          console.error(`Error searching for keyword "${keyword}":`, error);
        }
      }
    }
    
    console.log(`Total raw results before processing: ${allResults.length}`);
    
    // Debug: Log some sample results
    if (allResults.length > 0) {
      console.log('Sample history item:', {
        url: allResults[0].url,
        title: allResults[0].title,
        lastVisitTime: allResults[0].lastVisitTime,
        visitCount: allResults[0].visitCount
      });
    } else {
      console.warn('No history items found in Chrome history API');
      
      // Additional debugging: check permissions
      const permissions = await chrome.permissions.getAll();
      console.log('Extension permissions:', permissions);
      
      // Try a broader search
      console.log('Attempting broader search...');
      const broadResults = await chrome.history.search({
        text: '',
        maxResults: 10
      });
      console.log(`Broad search (no time limit): ${broadResults.length} items`);
    }
    
    // Remove duplicates based on URL
    const uniqueResults = [];
    const seenUrls = new Set();
    
    for (const item of allResults) {
      if (!seenUrls.has(item.url)) {
        seenUrls.add(item.url);
        uniqueResults.push(item);
      }
    }
    
    // Sort by last visit time (most recent first)
    uniqueResults.sort((a, b) => b.lastVisitTime - a.lastVisitTime);
    
    // Limit results
    const limitedResults = uniqueResults.slice(0, maxResults);
    
    // Transform to our expected format
    const transformedResults = limitedResults.map(item => ({
      url: item.url,
      title: item.title || 'No Title',
      visit_time: new Date(item.lastVisitTime).toISOString(),
      visit_count: item.visitCount || 0,
      content: `Title: ${item.title}\nURL: ${item.url}\nVisit Date: ${new Date(item.lastVisitTime).toLocaleString()}`,
      metadata: {
        source: 'chrome_history_extension',
        url: item.url,
        title: item.title,
        visit_time: new Date(item.lastVisitTime).toISOString(),
        visit_count: item.visitCount || 0,
        typed_count: item.typedCount || 0
      }
    }));
    
    console.log(`Found ${transformedResults.length} history items`);
    sendResponse({
      success: true,
      data: transformedResults,
      total: transformedResults.length
    });
    
  } catch (error) {
    console.error('Error searching history:', error);
    sendResponse({
      success: false,
      error: error.message
    });
  }
}

/**
 * Get recent Chrome history
 */
async function handleRecentHistory(params, sendResponse) {
  try {
    const {
      hours = 24,
      maxResults = 100
    } = params;
    
    const startTime = Date.now() - (hours * 60 * 60 * 1000);
    
    const results = await chrome.history.search({
      text: '',
      startTime: startTime,
      maxResults: maxResults
    });
    
    // Sort by last visit time
    results.sort((a, b) => b.lastVisitTime - a.lastVisitTime);
    
    const transformedResults = results.map(item => ({
      url: item.url,
      title: item.title || 'No Title',
      visit_time: new Date(item.lastVisitTime).toISOString(),
      visit_count: item.visitCount || 0,
      typed_count: item.typedCount || 0
    }));
    
    sendResponse({
      success: true,
      data: transformedResults,
      total: transformedResults.length
    });
    
  } catch (error) {
    console.error('Error getting recent history:', error);
    sendResponse({
      success: false,
      error: error.message
    });
  }
}


// Handle extension icon click
chrome.action.onClicked.addListener((tab) => {
  // Open options page or send message to content script
  chrome.tabs.sendMessage(tab.id, {
    action: 'showExtensionStatus'
  });
});

// Listen for history changes to update server data
chrome.history.onVisited.addListener((historyItem) => {
  console.log('New page visited:', historyItem.url);
  checkAndSync();
});

async function checkAndSync() {
  const result = await chrome.storage.local.get(['lastSyncTime']);
  const lastSync = result.lastSyncTime || 0;
  const now = Date.now();
  if (now - lastSync > 5 * 60 * 1000) { // 5 minutes
    sendHistoryToServer();
    chrome.storage.local.set({ lastSyncTime: now });
  }
}

chrome.history.onVisitRemoved.addListener((removed) => {
  console.log('History removed:', removed);
  // Trigger sync when history is removed to keep server updated
  if (isRegistered && removed.allHistory) {
    console.log('Full history cleared, triggering full sync');
    setTimeout(() => sendHistoryToServer(), 5000); // Wait 5 seconds then sync
  }
});

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === 'periodicSync') {
    console.log('Periodic sync triggered');
    sendHistoryToServer();
  }
});

// Sync when user becomes active after idle period
chrome.idle.onStateChanged.addListener((newState) => {
  if (newState === 'active' && isRegistered) {
    console.log('User became active, checking for history sync');
    // Only sync if we haven't synced in the last 10 minutes
    chrome.storage.local.get(['lastSyncTime'], (result) => {
      const lastSync = result.lastSyncTime || 0;
      const now = Date.now();
      if (now - lastSync > 10 * 60 * 1000) { // 10 minutes
        console.log('Triggering sync due to user activity');
        sendHistoryToServer();
        chrome.storage.local.set({ lastSyncTime: now });
      }
    });
  }
});