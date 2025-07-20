/**
 * Extend Your Memory - Options Page Script
 */

// Default Remote URLs (will be replaced by configure script)
const DEFAULT_URLS = {
  mcpServer: 'http://localhost:8501',
  backend: 'http://localhost:8000',
  frontend: 'http://localhost:3000'
};

// Local development URLs (fallback)
const LOCAL_URLS = {
  mcpServer: 'http://localhost:8501',
  backend: 'http://localhost:8000',
  frontend: 'http://localhost:3000'
};

document.addEventListener('DOMContentLoaded', function() {
  loadCurrentSettings();
  setupEventListeners();
});

function setupEventListeners() {
  document.getElementById('save-settings').addEventListener('click', saveSettings);
  document.getElementById('reset-defaults').addEventListener('click', resetToDefaults);
  document.getElementById('test-connection').addEventListener('click', testConnection);
}

async function loadCurrentSettings() {
  try {
    const result = await chrome.storage.local.get([
      'mcpServerUrl', 
      'backendUrl', 
      'frontendUrl'
    ]);
    
    const currentUrls = {
      mcpServer: result.mcpServerUrl || DEFAULT_URLS.mcpServer,
      backend: result.backendUrl || DEFAULT_URLS.backend,
      frontend: result.frontendUrl || DEFAULT_URLS.frontend
    };
    
    // Update current settings display
    document.getElementById('current-mcp').textContent = currentUrls.mcpServer;
    document.getElementById('current-backend').textContent = currentUrls.backend;
    document.getElementById('current-frontend').textContent = currentUrls.frontend;
    
    // Pre-fill form inputs
    document.getElementById('mcp-server-url').value = currentUrls.mcpServer;
    document.getElementById('backend-url').value = currentUrls.backend;
    document.getElementById('frontend-url').value = currentUrls.frontend;
    
  } catch (error) {
    console.error('Error loading settings:', error);
    showStatus('Error loading current settings', 'error');
  }
}

async function saveSettings() {
  try {
    const mcpServerUrl = document.getElementById('mcp-server-url').value.trim();
    const backendUrl = document.getElementById('backend-url').value.trim();
    const frontendUrl = document.getElementById('frontend-url').value.trim();
    
    // Validate URLs
    if (!isValidUrl(mcpServerUrl) || !isValidUrl(backendUrl) || !isValidUrl(frontendUrl)) {
      showStatus('Please enter valid URLs', 'error');
      return;
    }
    
    // Save to storage
    await chrome.storage.local.set({
      mcpServerUrl: mcpServerUrl,
      backendUrl: backendUrl,
      frontendUrl: frontendUrl
    });
    
    // Update current settings display
    document.getElementById('current-mcp').textContent = mcpServerUrl;
    document.getElementById('current-backend').textContent = backendUrl;
    document.getElementById('current-frontend').textContent = frontendUrl;
    
    showStatus('Settings saved successfully!', 'success');
    
    // Notify popup and background script of changes
    chrome.runtime.sendMessage({action: 'settingsUpdated'});
    
  } catch (error) {
    console.error('Error saving settings:', error);
    showStatus('Error saving settings', 'error');
  }
}

async function resetToDefaults() {
  try {
    // Set to Tailscale defaults
    document.getElementById('mcp-server-url').value = DEFAULT_URLS.mcpServer;
    document.getElementById('backend-url').value = DEFAULT_URLS.backend;
    document.getElementById('frontend-url').value = DEFAULT_URLS.frontend;
    
    // Auto-save the defaults
    await saveSettings();
    showStatus('Reset to Tailscale defaults', 'success');
    
  } catch (error) {
    console.error('Error resetting to defaults:', error);
    showStatus('Error resetting to defaults', 'error');
  }
}

async function testConnection() {
  const mcpServerUrl = document.getElementById('mcp-server-url').value.trim();
  const backendUrl = document.getElementById('backend-url').value.trim();
  
  if (!isValidUrl(mcpServerUrl) || !isValidUrl(backendUrl)) {
    showStatus('Please enter valid URLs before testing', 'error');
    return;
  }
  
  const button = document.getElementById('test-connection');
  const originalText = button.textContent;
  button.textContent = 'Testing...';
  button.disabled = true;
  
  try {
    // Test MCP Server
    const mcpTest = await testUrl(`${mcpServerUrl}/health`, 'MCP Server');
    
    // Test Backend API
    const backendTest = await testUrl(`${backendUrl}/health`, 'Backend API');
    
    if (mcpTest && backendTest) {
      showStatus('✅ All connections successful!', 'success');
    } else {
      showStatus('❌ Some connections failed. Check console for details.', 'error');
    }
    
  } catch (error) {
    console.error('Connection test error:', error);
    showStatus('❌ Connection test failed', 'error');
  } finally {
    button.textContent = originalText;
    button.disabled = false;
  }
}

async function testUrl(url, serviceName) {
  try {
    console.log(`Testing ${serviceName} at: ${url}`);
    const response = await fetch(url, { 
      method: 'GET', 
      mode: 'cors',
      timeout: 5000
    });
    
    if (response.ok) {
      console.log(`✅ ${serviceName} connection successful`);
      return true;
    } else {
      console.log(`❌ ${serviceName} returned status: ${response.status}`);
      return false;
    }
  } catch (error) {
    console.error(`❌ ${serviceName} connection failed:`, error);
    return false;
  }
}

function isValidUrl(string) {
  try {
    const url = new URL(string);
    return url.protocol === 'http:' || url.protocol === 'https:';
  } catch (_) {
    return false;
  }
}

function showStatus(message, type) {
  const statusElement = document.getElementById('status');
  statusElement.textContent = message;
  statusElement.className = `status ${type}`;
  statusElement.style.display = 'block';
  
  // Auto-hide after 5 seconds for success messages
  if (type === 'success') {
    setTimeout(() => {
      statusElement.style.display = 'none';
    }, 5000);
  }
}

// Listen for messages from other parts of the extension
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === 'reloadSettings') {
    loadCurrentSettings();
  }
});