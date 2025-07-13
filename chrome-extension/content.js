/**
 * Extend Your Memory - Chrome Extension Content Script
 * Handles communication between web pages and the extension
 */

// Inject bridge script for secure communication
const script = document.createElement('script');
script.src = chrome.runtime.getURL('history-bridge.js');
script.onload = function() {
  this.remove();
};
(document.head || document.documentElement).appendChild(script);

// Listen for messages from the injected script
window.addEventListener('message', function(event) {
  // Only accept messages from the same origin
  if (event.source !== window) return;
  
  // Check if this is our message
  if (event.data.type && event.data.type === 'EXTEND_YOUR_MEMORY_REQUEST') {
    // Forward to background script with error handling
    try {
      chrome.runtime.sendMessage(event.data.payload, function(response) {
        // Check for runtime errors
        if (chrome.runtime.lastError) {
          console.error('Extension messaging error:', chrome.runtime.lastError.message);
          // Send error response back to the page
          window.postMessage({
            type: 'EXTEND_YOUR_MEMORY_RESPONSE',
            requestId: event.data.requestId,
            error: chrome.runtime.lastError.message,
            response: null
          }, '*');
        } else {
          // Send successful response back to the page
          window.postMessage({
            type: 'EXTEND_YOUR_MEMORY_RESPONSE',
            requestId: event.data.requestId,
            response: response
          }, '*');
        }
      });
    } catch (error) {
      console.error('Error sending message to background script:', error);
      // Send error response back to the page
      window.postMessage({
        type: 'EXTEND_YOUR_MEMORY_RESPONSE',
        requestId: event.data.requestId,
        error: error.message,
        response: null
      }, '*');
    }
  }
});

// Listen for messages from background script
chrome.runtime.onMessage.addListener(function(request) {
  if (request.action === 'showExtensionStatus') {
    showExtensionStatus();
  }
  
  return true;
});

function showExtensionStatus() {
  // Create a temporary notification to show extension is active
  const notification = document.createElement('div');
  notification.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    background: #1976d2;
    color: white;
    padding: 12px 16px;
    border-radius: 8px;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    font-size: 14px;
    z-index: 10000;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    max-width: 300px;
  `;
  notification.innerHTML = `
    <div style="font-weight: bold; margin-bottom: 4px;">🧠 Extend Your Memory</div>
    <div style="font-size: 12px; opacity: 0.9;">Extension is active and ready to provide Chrome history access.</div>
  `;
  
  document.body.appendChild(notification);
  
  // Remove after 3 seconds
  setTimeout(() => {
    if (notification.parentNode) {
      notification.parentNode.removeChild(notification);
    }
  }, 3000);
}

// Log that content script is loaded
console.log('Extend Your Memory content script loaded');