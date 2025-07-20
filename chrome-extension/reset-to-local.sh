#!/bin/bash

# Chrome Extension Local Configuration Reset Script
# ローカル開発環境用のChrome拡張機能設定に戻すスクリプト

set -e

echo "🏠 Chrome Extension Local Configuration Reset"
echo "============================================"

echo "📋 ローカル開発環境の設定に戻します:"
echo "  MCP Server: http://localhost:8501"
echo "  Backend API: http://localhost:8000"
echo "  Frontend: http://localhost:3000"
echo ""

# 確認
read -p "ローカル設定にリセットしますか？ (y/N): " confirm
if [[ $confirm != [yY] ]]; then
    echo "❌ キャンセルされました"
    exit 1
fi

echo "🔧 Chrome拡張機能ファイルをローカル設定にリセット中..."

# 1. manifest.json をローカル用に戻す
echo "  📝 manifest.json をローカル設定に戻し中..."
if [[ -f "manifest.local.json" ]]; then
    cp manifest.local.json manifest.json
else
    # デフォルトのローカル設定を生成
    cat > manifest.json << 'EOF'
{
  "manifest_version": 3,
  "name": "Extend Your Memory - History, ChatGPT & Gemini Bridge",
  "version": "1.2.0",
  "description": "Bridge extension to provide secure Chrome history, ChatGPT and Gemini conversation access for Extend Your Memory",
  "permissions": [
    "history",
    "storage",
    "alarms",
    "idle"
  ],
  "background": {
    "service_worker": "background.js"
  },
  "content_scripts": [
    {
      "matches": ["<all_urls>"],
      "js": ["content.js"]
    },
    {
      "matches": ["https://chat.openai.com/*", "https://chatgpt.com/*"],
      "js": ["chatgpt-bridge.js"],
      "run_at": "document_start"
    },
    {
      "matches": ["https://gemini.google.com/*", "https://bard.google.com/*"],
      "js": ["gemini-bridge.js"],
      "run_at": "document_start"
    }
  ],
  "action": {
    "default_popup": "popup.html",
    "default_title": "Extend Your Memory"
  },
  "options_page": "options.html",
  "host_permissions": [
    "http://localhost:8501/*",
    "http://localhost:8000/*",
    "https://*.yourdomain.com/*",
    "https://chat.openai.com/*",
    "https://chatgpt.com/*",
    "https://gemini.google.com/*",
    "https://bard.google.com/*"
  ],
  "web_accessible_resources": [
    {
      "resources": ["history-bridge.js", "chatgpt-bridge.js", "gemini-bridge.js"],
      "matches": ["<all_urls>"]
    }
  ]
}
EOF
fi

# 2. popup.js をローカル用に戻す
echo "  📝 popup.js をローカル設定に戻し中..."
if [[ -f "popup.local.js" ]]; then
    cp popup.local.js popup.js
else
    # デフォルトのローカル設定を生成
    cat > popup.js << 'EOF'
/**
 * Extend Your Memory - Chrome Extension Popup Script (Local Development)
 */

// Local development URLs
const LOCAL_URLS = {
  mcpServer: 'http://localhost:8501',
  backend: 'http://localhost:8000',
  frontend: 'http://localhost:3000'
};

document.addEventListener('DOMContentLoaded', function() {
  // Check service status
  checkServiceStatus();
  
  // Set up event listeners
  setupEventListeners();
});

async function getStoredUrls() {
  return new Promise((resolve) => {
    chrome.storage.local.get(['mcpServerUrl', 'backendUrl', 'frontendUrl'], (result) => {
      resolve({
        mcpServer: result.mcpServerUrl || LOCAL_URLS.mcpServer,
        backend: result.backendUrl || LOCAL_URLS.backend,
        frontend: result.frontendUrl || LOCAL_URLS.frontend
      });
    });
  });
}

async function checkServiceStatus() {
  const urls = await getStoredUrls();
  const services = [
    { id: 'mcp-status', url: `${urls.mcpServer}/health` },
    { id: 'backend-status', url: `${urls.backend}/health` }
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

async function setupEventListeners() {
  // Test History Access button
  document.getElementById('test-history').addEventListener('click', testHistoryAccess);
  
  // Open Application button
  document.getElementById('open-app').addEventListener('click', async () => {
    const urls = await getStoredUrls();
    chrome.tabs.create({url: urls.frontend});
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
    // Test 1: Search without keywords (last 30 days)
    console.log('Testing history access without keywords...');
    const response1 = await new Promise((resolve, reject) => {
      chrome.runtime.sendMessage({
        action: 'searchHistory',
        params: {
          keywords: [],
          days: 30,
          maxResults: 10
        }
      }, (response) => {
        if (chrome.runtime.lastError) {
          reject(new Error(chrome.runtime.lastError.message));
        } else {
          resolve(response);
        }
      });
    });
    
    if (response1.success && response1.total > 0) {
      showNotification(`✅ Success! Found ${response1.total} history items (30 days)`, 'success');
      return;
    }
    
    // Test 2: Search with broader time range (90 days)
    console.log('Testing with broader time range...');
    const response2 = await new Promise((resolve, reject) => {
      chrome.runtime.sendMessage({
        action: 'searchHistory', 
        params: {
          keywords: [],
          days: 90,
          maxResults: 10
        }
      }, (response) => {
        if (chrome.runtime.lastError) {
          reject(new Error(chrome.runtime.lastError.message));
        } else {
          resolve(response);
        }
      });
    });
    
    if (response2.success && response2.total > 0) {
      showNotification(`✅ Success! Found ${response2.total} history items (90 days)`, 'success');
      return;
    }
    
    // Test 3: Check permissions and broad search
    const permissions = await chrome.permissions.getAll();
    console.log('Extension permissions:', permissions);
    
    if (response1.success || response2.success) {
      if (response1.total === 0 && response2.total === 0) {
        showNotification(`⚠️ Extension works but no history found. Visit some websites first.`, 'info');
      } else {
        showNotification(`❌ Error: ${response1.error || response2.error}`, 'error');
      }
    } else {
      showNotification(`❌ Extension error: Check console for details`, 'error');
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
EOF
fi

# Chrome拡張機能の設定をクリア（ローカル設定に戻す）
echo "  🗑️  拡張機能の保存済み設定をクリア中..."
cat > clear-extension-settings.js << 'EOF'
// Chrome拡張機能の設定をクリアしてローカル設定に戻す
chrome.storage.local.clear(() => {
  console.log('Extension settings cleared, reverted to local defaults');
});
EOF

echo ""
echo "✅ ローカル設定への復元が完了しました！"
echo ""
echo "📋 次の手順:"
echo "  1. Chrome拡張機能管理画面 (chrome://extensions/) を開く"
echo "  2. 「Extend Your Memory」拡張機能の「再読み込み」ボタンをクリック"
echo "  3. 拡張機能の設定画面で URL が localhost に戻っていることを確認"
echo ""
echo "🎯 ローカル設定:"
echo "  MCP Server: http://localhost:8501"
echo "  Backend API: http://localhost:8000"
echo "  Frontend: http://localhost:3000"
echo ""
echo "💡 再度リモート設定にする場合は ./configure-remote.sh を実行してください"

# 一時ファイルをクリア
rm -f clear-extension-settings.js