/**
 * Extend Your Memory - Chrome Extension Popup Script
 */

document.addEventListener('DOMContentLoaded', function() {
  // Initialize popup
  initializePopup();
  
  // Check service status
  checkServiceStatus();
  
  // Set up event listeners
  setupEventListeners();
});

function initializePopup() {
  console.log('Popup initialized');
}

async function checkServiceStatus() {
  // Check MCP Server
  try {
    const mcpResponse = await fetch('http://localhost:8501/health', {
      method: 'GET',
      mode: 'cors'
    });
    
    const mcpStatus = document.getElementById('mcp-status');
    if (mcpResponse.ok) {
      mcpStatus.textContent = 'Connected';
      mcpStatus.className = 'status-value connected';
    } else {
      mcpStatus.textContent = 'Error';
      mcpStatus.className = 'status-value disconnected';
    }
  } catch (error) {
    const mcpStatus = document.getElementById('mcp-status');
    mcpStatus.textContent = 'Offline';
    mcpStatus.className = 'status-value disconnected';
  }
  
  // Check Backend API
  try {
    const backendResponse = await fetch('http://localhost:8000/health', {
      method: 'GET',
      mode: 'cors'
    });
    
    const backendStatus = document.getElementById('backend-status');
    if (backendResponse.ok) {
      backendStatus.textContent = 'Connected';
      backendStatus.className = 'status-value connected';
    } else {
      backendStatus.textContent = 'Error';
      backendStatus.className = 'status-value disconnected';
    }
  } catch (error) {
    const backendStatus = document.getElementById('backend-status');
    backendStatus.textContent = 'Offline';
    backendStatus.className = 'status-value disconnected';
  }
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