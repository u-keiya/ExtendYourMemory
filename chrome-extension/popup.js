/**
 * Extend Your Memory - Chrome Extension Popup Script
 */

document.addEventListener('DOMContentLoaded', function() {
  // Check service status
  checkServiceStatus();
  
  // Set up event listeners
  setupEventListeners();
});

async function checkServiceStatus() {
  const services = [
    { id: 'mcp-status', url: 'http://localhost:8501/health' },
    { id: 'backend-status', url: 'http://localhost:8000/health' }
  ];
  
  for (const service of services) {
    try {
      const response = await fetch(service.url, { method: 'GET', mode: 'cors' });
      updateServiceStatus(service.id, response.ok ? 'Connected' : 'Error');
    } catch (error) {
      updateServiceStatus(service.id, 'Offline');
    }
  }
}

function updateServiceStatus(elementId, status) {
  const element = document.getElementById(elementId);
  element.textContent = status;
  element.className = `status-value ${status.toLowerCase() === 'connected' ? 'connected' : 'disconnected'}`;
}

function setupEventListeners() {
  // Test History Access button
  document.getElementById('test-history').addEventListener('click', testHistoryAccess);
  
  // Open Application button
  document.getElementById('open-app').addEventListener('click', () => {
    chrome.tabs.create({url: 'http://localhost:3000'});
  });
  
  // View Options button
  document.getElementById('view-options').addEventListener('click', () => {
    chrome.runtime.openOptionsPage();
  });
}

async function testHistoryAccess() {
  const button = document.getElementById('test-history');
  const originalText = button.textContent;
  
  button.textContent = 'Testing...';
  button.disabled = true;
  
  try {
    // Test history search
    const response = await new Promise((resolve, reject) => {
      chrome.runtime.sendMessage({
        action: 'searchHistory',
        params: {
          keywords: ['test'],
          days: 7,
          maxResults: 5
        }
      }, (response) => {
        if (chrome.runtime.lastError) {
          reject(new Error(chrome.runtime.lastError.message));
        } else {
          resolve(response);
        }
      });
    });
    
    if (response.success) {
      showNotification(`✅ Success! Found ${response.total} history items`, 'success');
    } else {
      showNotification(`❌ Error: ${response.error}`, 'error');
    }
    
  } catch (error) {
    console.error('History test error:', error);
    showNotification(`❌ Test failed: ${error.message}`, 'error');
  } finally {
    button.textContent = originalText;
    button.disabled = false;
  }
}

function showNotification(message, type = 'info') {
  // Create notification element
  const notification = document.createElement('div');
  notification.style.cssText = `
    position: fixed;
    top: 10px;
    left: 50%;
    transform: translateX(-50%);
    padding: 8px 16px;
    border-radius: 4px;
    font-size: 12px;
    z-index: 1000;
    max-width: 280px;
    text-align: center;
    ${type === 'success' ? 'background: #4caf50; color: white;' : 
      type === 'error' ? 'background: #f44336; color: white;' : 
      'background: #2196f3; color: white;'}
  `;
  notification.textContent = message;
  
  document.body.appendChild(notification);
  
  // Remove after 3 seconds
  setTimeout(() => {
    if (notification.parentNode) {
      notification.parentNode.removeChild(notification);
    }
  }, 3000);
}

// Listen for messages from background script
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === 'updateStatus') {
    // Update UI based on status changes
    checkServiceStatus();
  }
});