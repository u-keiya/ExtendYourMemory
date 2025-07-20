#!/bin/bash

# Chrome Extension Remote Configuration Script
# リモートサーバー向けのChrome拡張機能設定スクリプト

set -e

echo "🚀 Chrome Extension Remote Configuration"
echo "========================================"

# デフォルト値の設定
DEFAULT_DOMAIN="localhost"
DEFAULT_MCP_PORT="8501"
DEFAULT_BACKEND_PORT="8000"
DEFAULT_FRONTEND_PORT="3000"

# .env.chrome ファイルから設定を読み込み
if [[ -f ".env.chrome" ]]; then
    echo "📄 .env.chrome ファイルから設定を読み込み中..."
    source .env.chrome
    echo "  ✅ 設定ファイルから値を読み込みました"
elif [[ -f ".env.chrome.template" ]]; then
    echo "📄 .env.chrome.template が見つかりました"
    echo "  💡 .env.chrome.template を .env.chrome にコピーして編集してください"
    echo "  📝 または対話モードで設定を入力してください"
fi

# ユーザー入力または環境変数から値を取得
if [[ -z "$REMOTE_DOMAIN" ]]; then
    read -p "リモートサーバーのドメインまたはIPアドレス [$DEFAULT_DOMAIN]: " REMOTE_DOMAIN
    REMOTE_DOMAIN=${REMOTE_DOMAIN:-$DEFAULT_DOMAIN}
fi

if [[ -z "$MCP_PORT" ]]; then
    read -p "MCP Server ポート番号 [$DEFAULT_MCP_PORT]: " MCP_PORT
    MCP_PORT=${MCP_PORT:-$DEFAULT_MCP_PORT}
fi

if [[ -z "$BACKEND_PORT" ]]; then
    read -p "Backend API ポート番号 [$DEFAULT_BACKEND_PORT]: " BACKEND_PORT
    BACKEND_PORT=${BACKEND_PORT:-$DEFAULT_BACKEND_PORT}
fi

if [[ -z "$FRONTEND_PORT" ]]; then
    read -p "Frontend ポート番号 [$DEFAULT_FRONTEND_PORT]: " FRONTEND_PORT
    FRONTEND_PORT=${FRONTEND_PORT:-$DEFAULT_FRONTEND_PORT}
fi

# HTTPS設定
USE_HTTPS=${USE_HTTPS:-false}
if [[ "$USE_HTTPS" == "true" ]]; then
    PROTOCOL="https"
    HTTPS_PORT=${HTTPS_PORT:-443}
else
    PROTOCOL="http"
fi

# URLs構築
if [[ "$USE_HTTPS" == "true" ]]; then
    if [[ "$HTTPS_PORT" == "443" ]]; then
        MCP_URL="https://${REMOTE_DOMAIN}:${MCP_PORT}"
        BACKEND_URL="https://${REMOTE_DOMAIN}:${BACKEND_PORT}" 
        FRONTEND_URL="https://${REMOTE_DOMAIN}"
    else
        MCP_URL="https://${REMOTE_DOMAIN}:${MCP_PORT}"
        BACKEND_URL="https://${REMOTE_DOMAIN}:${BACKEND_PORT}"
        FRONTEND_URL="https://${REMOTE_DOMAIN}:${HTTPS_PORT}"
    fi
else
    MCP_URL="http://${REMOTE_DOMAIN}:${MCP_PORT}"
    BACKEND_URL="http://${REMOTE_DOMAIN}:${BACKEND_PORT}"
    FRONTEND_URL="http://${REMOTE_DOMAIN}:${FRONTEND_PORT}"
fi

echo ""
echo "📋 設定情報:"
echo "  ドメイン: $REMOTE_DOMAIN"
echo "  MCP Server: $MCP_URL"
echo "  Backend API: $BACKEND_URL"
echo "  Frontend: $FRONTEND_URL"
echo ""

# 確認
read -p "この設定で続行しますか？ (y/N): " confirm
if [[ $confirm != [yY] ]]; then
    echo "❌ キャンセルされました"
    exit 1
fi

echo "🔧 Chrome拡張機能ファイルを設定中..."

# 1. manifest.json の設定
echo "  📝 manifest.json を生成中..."
cat > manifest.json << EOF
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
    "http://${REMOTE_DOMAIN}:${MCP_PORT}/*",
    "http://${REMOTE_DOMAIN}:${BACKEND_PORT}/*",
    "http://${REMOTE_DOMAIN}:${FRONTEND_PORT}/*",
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

# 2. popup.js の設定
echo "  📝 popup.js を生成中..."
cat > popup.js << EOF
/**
 * Extend Your Memory - Chrome Extension Popup Script (Remote Configured)
 */

// Remote URLs configured by setup script
const REMOTE_URLS = {
  mcpServer: '${MCP_URL}',
  backend: '${BACKEND_URL}',
  frontend: '${FRONTEND_URL}'
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
        mcpServer: result.mcpServerUrl || REMOTE_URLS.mcpServer,
        backend: result.backendUrl || REMOTE_URLS.backend,
        frontend: result.frontendUrl || REMOTE_URLS.frontend
      });
    });
  });
}

async function checkServiceStatus() {
  const urls = await getStoredUrls();
  const services = [
    { id: 'mcp-status', url: \`\${urls.mcpServer}/health\` },
    { id: 'backend-status', url: \`\${urls.backend}/health\` }
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
  element.className = \`status-value \${status.toLowerCase() === 'connected' ? 'connected' : 'disconnected'}\`;
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
      showNotification(\`✅ Success! Found \${response1.total} history items (30 days)\`, 'success');
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
      showNotification(\`✅ Success! Found \${response2.total} history items (90 days)\`, 'success');
      return;
    }
    
    // Test 3: Check permissions and broad search
    const permissions = await chrome.permissions.getAll();
    console.log('Extension permissions:', permissions);
    
    if (response1.success || response2.success) {
      if (response1.total === 0 && response2.total === 0) {
        showNotification(\`⚠️ Extension works but no history found. Visit some websites first.\`, 'info');
      } else {
        showNotification(\`❌ Error: \${response1.error || response2.error}\`, 'error');
      }
    } else {
      showNotification(\`❌ Extension error: Check console for details\`, 'error');
    }
    
  } catch (error) {
    console.error('History test error:', error);
    showNotification(\`❌ Test failed: \${error.message}\`, 'error');
  } finally {
    button.textContent = originalText;
    button.disabled = false;
  }
}

function showNotification(message, type = 'info') {
  // Create notification element
  const notification = document.createElement('div');
  notification.style.cssText = \`
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
    \${type === 'success' ? 'background: #4caf50; color: white;' : 
      type === 'error' ? 'background: #f44336; color: white;' : 
      'background: #2196f3; color: white;'}
  \`;
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

# 3. options.js の設定（デフォルト値を更新）
echo "  📝 options.js を生成中..."
sed "s|http://localhost:8501|${MCP_URL}|g; s|http://localhost:8000|${BACKEND_URL}|g; s|http://localhost:3000|${FRONTEND_URL}|g" options.js > options.js.tmp && mv options.js.tmp options.js

# 4. options.html の設定（プレースホルダーを更新）
echo "  📝 options.html を生成中..."
sed "s|http://localhost:8501|${MCP_URL}|g; s|http://localhost:8000|${BACKEND_URL}|g; s|http://localhost:3000|${FRONTEND_URL}|g" options.html > options.html.tmp && mv options.html.tmp options.html

echo ""
echo "✅ Chrome拡張機能の設定が完了しました！"
echo ""
echo "📋 次の手順:"
echo "  1. Chrome拡張機能管理画面 (chrome://extensions/) を開く"
echo "  2. 「デベロッパーモード」を有効化"
echo "  3. 「パッケージ化されていない拡張機能を読み込む」をクリック"
echo "  4. このフォルダを選択: $(pwd)"
echo ""
echo "🎯 設定されたURL:"
echo "  MCP Server: $MCP_URL"
echo "  Backend API: $BACKEND_URL"  
echo "  Frontend: $FRONTEND_URL"
echo ""
echo "⚙️  拡張機能の設定画面で追加の調整が可能です"