// Simple ChatGPT Bridge Test (コピペで実行)
console.log('🧪 Simple ChatGPT Bridge Test Starting...');

// 1. 基本チェック
console.log('=== BASIC CHECKS ===');
console.log('Current URL:', window.location.href);
console.log('Is ChatGPT domain:', window.location.hostname === 'chat.openai.com');
console.log('Chrome API available:', typeof chrome !== 'undefined');
console.log('Extension ID:', chrome?.runtime?.id || 'Not available');

// 2. Bridge存在確認
console.log('=== BRIDGE CHECK ===');
console.log('window.chatgptBridge exists:', !!window.chatgptBridge);

if (window.chatgptBridge) {
    console.log('✅ Bridge found!');
    console.log('Bridge type:', typeof window.chatgptBridge);
    console.log('Bridge properties:', Object.keys(window.chatgptBridge));
    
    // 3. Bridge機能テスト
    console.log('=== FUNCTION TEST ===');
    try {
        const result = window.chatgptBridge.debugExtraction();
        console.log('✅ debugExtraction() result:', result);
    } catch (error) {
        console.error('❌ debugExtraction() failed:', error);
    }
} else {
    console.log('❌ Bridge not found');
    
    // 4. 拡張機能状態確認
    console.log('=== EXTENSION STATUS ===');
    
    if (typeof chrome === 'undefined') {
        console.log('❌ Chrome API not available - not in Chrome browser?');
    } else if (!chrome.runtime) {
        console.log('❌ chrome.runtime not available');
    } else if (!chrome.runtime.id) {
        console.log('❌ Extension not installed or not running');
    } else {
        console.log('✅ Extension API available');
        
        // 5. 手動メッセージ送信テスト
        console.log('=== MANUAL MESSAGE TEST ===');
        const testMessage = {
            type: 'SEND_CHATGPT_CONVERSATIONS',
            data: {
                conversation_items: [{
                    id: 'console_test_' + Date.now(),
                    title: 'Console Test Conversation',
                    create_time: Date.now() / 1000,
                    mapping: {
                        'test_msg': {
                            message: {
                                content: { parts: ['Test from browser console'] },
                                role: 'user',
                                create_time: Date.now() / 1000
                            }
                        }
                    },
                    metadata: {
                        source: 'console_test',
                        url: window.location.href
                    }
                }],
                client_id: 'console_test_client',
                timestamp: Date.now()
            }
        };
        
        chrome.runtime.sendMessage(testMessage, (response) => {
            if (chrome.runtime.lastError) {
                console.error('❌ Message failed:', chrome.runtime.lastError.message);
                
                if (chrome.runtime.lastError.message.includes('port closed')) {
                    console.log('💡 Fix: Reload extension at chrome://extensions/');
                }
            } else {
                console.log('✅ Message sent successfully:', response);
            }
        });
    }
}

// 6. DOM確認
console.log('=== DOM CHECK ===');
console.log('Document ready state:', document.readyState);
console.log('Page title:', document.title);
console.log('Body exists:', !!document.body);
console.log('Content length:', document.body ? document.body.textContent.length : 0);

// 7. コンソールメッセージ確認指示
console.log('=== NEXT STEPS ===');
console.log('Look for these messages in console:');
console.log('- 🚀 Injecting ChatGPT Bridge into page context...');
console.log('- ✅ ChatGPT Bridge injected successfully');
console.log('- 🔄 Auto-extracting after page load...');

if (!window.chatgptBridge) {
    console.log('');
    console.log('🔧 TROUBLESHOOTING:');
    console.log('1. Reload extension: chrome://extensions/ → find extension → reload button');
    console.log('2. Refresh this page');
    console.log('3. Wait 5 seconds and run this test again');
    console.log('4. If still not working, check extension background script errors');
}

console.log('🧪 Test completed');