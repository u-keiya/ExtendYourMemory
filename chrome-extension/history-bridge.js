/**
 * Extend Your Memory - History Bridge Script
 * Injected into web pages to provide secure Chrome history access
 */

(function() {
  'use strict';
  
  let requestIdCounter = 0;
  const pendingRequests = new Map();
  
  // Track extension availability
  let extensionAvailable = false;
  let extensionChecked = false;
  // Consider expiring the cache or exposing a
  // `force` parameter to re-probe after N minutes:
  // const CACHE_TTL = 60_000; /* 1 min */
  // let lastCheck = 0;
  
  /**
   * Check if the extension is available
   */
  function isExtensionAvailable() {
    if (extensionChecked) {
      return extensionAvailable;
    }
    
    // Check if we're in the right context
    return typeof window.ExtendYourMemoryBridge !== 'undefined';
  }
  
  /**
   * Test if extension is actually working by sending a ping
   */
  function testExtensionConnection() {
    return new Promise((resolve) => {
      if (extensionChecked) {
        resolve(extensionAvailable);
        return;
      }
      
      const requestId = ++requestIdCounter;
      const timeout = 3000; // 3 second timeout for connectivity test
      
      // Store the request
      pendingRequests.set(requestId, { 
        resolve: (result) => {
          extensionAvailable = true;
          extensionChecked = true;
          resolve(true);
        }, 
        reject: () => {
          extensionAvailable = false;
          extensionChecked = true;
          resolve(false);
        }
      });
      
      // Set timeout
      setTimeout(() => {
        if (pendingRequests.has(requestId)) {
          pendingRequests.delete(requestId);
          extensionAvailable = false;
          extensionChecked = true;
          resolve(false);
        }
      }, timeout);
      
      // Send a test message
      window.postMessage({
        type: 'EXTEND_YOUR_MEMORY_REQUEST',
        requestId: requestId,
        payload: {
          action: 'getRecentHistory',
          params: {
            hours: 1,
            maxResults: 1
          }
        }
      }, '*');
    });
  }
  
  /**
   * Search Chrome history with keywords
   */
  function searchHistory(keywords, options = {}) {
    return new Promise((resolve, reject) => {
      if (!isExtensionAvailable()) {
        reject(new Error('Chrome extension not available'));
        return;
      }
      
      const requestId = ++requestIdCounter;
      const timeout = options.timeout || 10000;
      
      // Store the request
      pendingRequests.set(requestId, { resolve, reject });
      
      // Set timeout
      setTimeout(() => {
        if (pendingRequests.has(requestId)) {
          pendingRequests.delete(requestId);
          reject(new Error('Request timeout'));
        }
      }, timeout);
      
      // Send message to content script
      window.postMessage({
        type: 'EXTEND_YOUR_MEMORY_REQUEST',
        requestId: requestId,
        payload: {
          action: 'searchHistory',
          params: {
            keywords: Array.isArray(keywords) ? keywords : [keywords],
            days: options.days || 30,
            maxResults: options.maxResults || 50
          }
        }
      }, '*');
    });
  }
  
  /**
   * Get recent Chrome history
   */
  function getRecentHistory(options = {}) {
    return new Promise((resolve, reject) => {
      if (!isExtensionAvailable()) {
        reject(new Error('Chrome extension not available'));
        return;
      }
      
      const requestId = ++requestIdCounter;
      const timeout = options.timeout || 10000;
      
      // Store the request
      pendingRequests.set(requestId, { resolve, reject });
      
      // Set timeout
      setTimeout(() => {
        if (pendingRequests.has(requestId)) {
          pendingRequests.delete(requestId);
          reject(new Error('Request timeout'));
        }
      }, timeout);
      
      // Send message to content script
      window.postMessage({
        type: 'EXTEND_YOUR_MEMORY_REQUEST',
        requestId: requestId,
        payload: {
          action: 'getRecentHistory',
          params: {
            hours: options.hours || 24,
            maxResults: options.maxResults || 100
          }
        }
      }, '*');
    });
  }

  /**
   * Request the extension to send latest history to the server
   */
  function refreshHistory() {
    return new Promise((resolve, reject) => {
      if (!isExtensionAvailable()) {
        reject(new Error('Chrome extension not available'));
        return;
      }

      const requestId = ++requestIdCounter;
      const timeout = 10000;

      pendingRequests.set(requestId, { resolve, reject });

      setTimeout(() => {
        if (pendingRequests.has(requestId)) {
          pendingRequests.delete(requestId);
          reject(new Error('Request timeout'));
        }
      }, timeout);

      window.postMessage({
        type: 'EXTEND_YOUR_MEMORY_REQUEST',
        requestId: requestId,
        payload: {
          action: 'refreshHistory',
          params: {}
        }
      }, '*');
    });
  }
  
  // Listen for responses from content script
  window.addEventListener('message', function(event) {
    if (event.source !== window) return;
    
    if (event.data.type && event.data.type === 'EXTEND_YOUR_MEMORY_RESPONSE') {
      const { requestId, response } = event.data;
      
      if (pendingRequests.has(requestId)) {
        const { resolve, reject } = pendingRequests.get(requestId);
        pendingRequests.delete(requestId);
        
        if (response.success) {
          resolve(response.data);
        } else {
          reject(new Error(response.error || 'Unknown error'));
        }
      }
    }
  });
  
  // Create a global object for our API
  window.ExtendYourMemoryBridge = {
    searchHistory: searchHistory,
    getRecentHistory: getRecentHistory,
    refreshHistory: refreshHistory,
    isExtensionAvailable: isExtensionAvailable,
    testExtensionConnection: testExtensionConnection
  };

  // Dispatch event to notify that the bridge is ready
  window.dispatchEvent(new CustomEvent('ExtendYourMemoryBridgeReady', {
    detail: {
      version: '1.0.0',
      capabilities: ['searchHistory', 'getRecentHistory', 'refreshHistory', 'testExtensionConnection']
    }
  }));
  
  console.log('Extend Your Memory Bridge loaded');
})();