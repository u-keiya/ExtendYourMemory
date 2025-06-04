/**
 * Extend Your Memory - Chrome Extension Background Script
 * Provides secure Chrome history access via Chrome Extension API
 */

// Native messaging connection for secure communication
let nativePort = null;

// Initialize extension
chrome.runtime.onInstalled.addListener(() => {
  console.log('Extend Your Memory extension installed');
});

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

/**
 * Get detailed visit information for a specific URL
 */
async function getVisitDetails(url) {
  try {
    const visits = await chrome.history.getVisits({url: url});
    return visits;
  } catch (error) {
    console.error('Error getting visit details:', error);
    return [];
  }
}

// Handle extension icon click
chrome.action.onClicked.addListener((tab) => {
  // Open options page or send message to content script
  chrome.tabs.sendMessage(tab.id, {
    action: 'showExtensionStatus'
  });
});

// Listen for history changes to potentially update our data
chrome.history.onVisited.addListener((historyItem) => {
  console.log('New page visited:', historyItem.url);
  // Could potentially notify our MCP server about new visits
});

chrome.history.onVisitRemoved.addListener((removed) => {
  console.log('History removed:', removed);
  // Could potentially update our cached data
});