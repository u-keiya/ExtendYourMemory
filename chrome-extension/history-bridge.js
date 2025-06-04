/**
 * Extend Your Memory - History Bridge Script
 * Injected into web pages to provide secure Chrome history access
 */

(function() {
  'use strict';
  
  // Create a global object for our API
  window.ExtendYourMemoryBridge = {
    searchHistory: searchHistory,
    getRecentHistory: getRecentHistory,
    isExtensionAvailable: isExtensionAvailable
  };
  
  let requestIdCounter = 0;
  const pendingRequests = new Map();
  
  /**
   * Check if the extension is available
   */
  function isExtensionAvailable() {
    return typeof chrome !== 'undefined' && 
           chrome.runtime && 
           chrome.runtime.id;
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
  
  // Dispatch event to notify that the bridge is ready
  window.dispatchEvent(new CustomEvent('ExtendYourMemoryBridgeReady', {
    detail: {
      version: '1.0.0',
      capabilities: ['searchHistory', 'getRecentHistory']
    }
  }));
  
  console.log('Extend Your Memory Bridge loaded');
})();