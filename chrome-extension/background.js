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
  await registerWithServer();
  // Set up periodic sync
  chrome.alarms.create('periodicSync', { periodInMinutes: 15 });
}

// Handle messages from content scripts or popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'searchHistory') {
    handleHistorySearch(request.params, sendResponse);
    return true; // Keep message channel open for async response
  } else if (request.action === 'getRecentHistory') {
    handleRecentHistory(request.params, sendResponse);
    return true;
  }
});

// Server communication configuration
const SERVER_URL = 'http://localhost:8501';
let isRegistered = false;

// Register extension with server on startup
async function registerWithServer() {
  try {
    const response = await fetch(`${SERVER_URL}/api/chrome/register`, {
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
      console.error('Failed to register with server:', response.status);
    }
  } catch (error) {
    console.error('Error registering with server:', error);
  }
}

// Send history data to server
async function sendHistoryToServer(keywords = [], maxResults = 1000) {
  try {
    if (!isRegistered) {
      console.log('Not registered with server, skipping history sync');
      return;
    }
    
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
    const response = await fetch(`${SERVER_URL}/api/chrome/history`, {
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
  }
}

// Note: All keyword extraction and categorization is now handled by LLM on the server
// Chrome Extension only provides raw history data

// Handle external messages from MCP server
chrome.runtime.onMessageExternal.addListener((request, sender, sendResponse) => {
  // Verify sender is from our allowed origins
  const allowedOrigins = ['http://localhost:8501', 'http://localhost:8000'];
  
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
    
    // Calculate start time (days ago)
    const startTime = Date.now() - (days * 24 * 60 * 60 * 1000);
    
    let allResults = [];
    
    if (keywords.length === 0) {
      // If no keywords, get recent history
      const results = await chrome.history.search({
        text: '',
        startTime: startTime,
        maxResults: maxResults
      });
      allResults = results;
    } else {
      // Search for each keyword
      for (const keyword of keywords) {
        try {
          const results = await chrome.history.search({
            text: keyword,
            startTime: startTime,
            maxResults: Math.ceil(maxResults / keywords.length)
          });
          allResults = allResults.concat(results);
        } catch (error) {
          console.error(`Error searching for keyword "${keyword}":`, error);
        }
      }
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