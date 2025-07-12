// Test script to manually trigger ChatGPT conversation extraction
// Paste this in ChatGPT page console to test the bridge

console.log('🧪 Starting ChatGPT Bridge Test...');

// Test data
const testConversation = {
    id: 'test_' + Date.now(),
    title: 'Manual Test Conversation - ' + new Date().toLocaleString(),
    create_time: Date.now() / 1000,
    update_time: Date.now() / 1000,
    mapping: {
        'test_msg_1': {
            message: {
                content: {
                    parts: ['Hello! This is a test message from the ChatGPT Extension Bridge.']
                },
                role: 'user',
                create_time: Date.now() / 1000
            }
        },
        'test_msg_2': {
            message: {
                content: {
                    parts: ['This is a response from the assistant. The extension is working correctly and can extract conversation data.']
                },
                role: 'assistant',
                create_time: Date.now() / 1000
            }
        }
    },
    metadata: {
        source: 'manual_test_console',
        url: window.location.href,
        extracted_at: Date.now() / 1000,
        test: true
    }
};

console.log('🧪 Test conversation created:', testConversation);

// Test function to send data via extension messaging
async function testExtensionMessaging() {
    console.log('🧪 Testing extension messaging...');
    
    // Check extension availability first
    if (typeof chrome === 'undefined') {
        console.error('❌ Chrome API not available (not in Chrome browser?)');
        return false;
    }
    
    if (!chrome.runtime) {
        console.error('❌ chrome.runtime not available');
        return false;
    }
    
    if (!chrome.runtime.id) {
        console.error('❌ chrome.runtime.id not available (extension not installed?)');
        return false;
    }
    
    console.log('✅ Chrome extension API available, ID:', chrome.runtime.id);
    
    const messageData = {
        type: 'SEND_CHATGPT_CONVERSATIONS',
        data: {
            conversation_items: [testConversation],
            client_id: 'manual_test_' + Date.now(),
            timestamp: Date.now()
        }
    };
    
    try {
        const response = await new Promise((resolve, reject) => {
            // Set timeout to prevent hanging
            const timeout = setTimeout(() => {
                reject(new Error('Extension messaging timeout after 10 seconds'));
            }, 10000);
            
            chrome.runtime.sendMessage(messageData, (response) => {
                clearTimeout(timeout);
                
                if (chrome.runtime.lastError) {
                    reject(new Error(chrome.runtime.lastError.message));
                } else {
                    resolve(response);
                }
            });
        });
        
        console.log('✅ Extension messaging successful:', response);
        return true;
    } catch (error) {
        console.error('❌ Extension messaging failed:', error.message);
        
        // Log common error scenarios
        if (error.message.includes('port closed')) {
            console.log('💡 This error usually means:');
            console.log('   - Extension background script crashed');
            console.log('   - Extension was reloaded/updated');
            console.log('   - Try reloading the extension in chrome://extensions/');
        }
        
        return false;
    }
}

// Test function to send data via direct fetch
async function testDirectFetch() {
    console.log('🧪 Testing direct fetch...');
    
    try {
        const response = await fetch('http://localhost:8501/api/chatgpt/conversations', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                conversation_items: [testConversation],
                client_id: 'manual_test_direct',
                timestamp: Date.now()
            })
        });
        
        if (response.ok) {
            const result = await response.json();
            console.log('✅ Direct fetch successful:', result);
            return true;
        } else {
            console.error('❌ Direct fetch failed:', response.status, response.statusText);
            return false;
        }
    } catch (error) {
        console.error('❌ Direct fetch error:', error);
        return false;
    }
}

// Run tests
async function runTests() {
    console.log('🧪 Running ChatGPT Bridge Tests...');
    
    // Test 1: Extension messaging
    const extensionResult = await testExtensionMessaging();
    
    // Test 2: Direct fetch (fallback)
    if (!extensionResult) {
        console.log('🧪 Extension messaging failed, trying direct fetch...');
        const directResult = await testDirectFetch();
        
        if (!directResult) {
            console.error('❌ Both extension messaging and direct fetch failed');
            console.log('💡 Troubleshooting steps:');
            console.log('   1. Ensure Chrome extension is installed and enabled');
            console.log('   2. Check that MCP server is running on localhost:8501');
            console.log('   3. Check browser console for CORS errors');
        }
    }
    
    // Test 3: Check if bridge exists
    if (window.chatgptBridge) {
        console.log('🧪 Testing chatgptBridge.manualExtract()...');
        try {
            await window.chatgptBridge.manualExtract();
            console.log('✅ chatgptBridge.manualExtract() completed');
        } catch (error) {
            console.error('❌ chatgptBridge.manualExtract() failed:', error);
        }
    } else {
        console.log('⚠️ window.chatgptBridge not available');
        console.log('   This usually means the extension content script is not loaded');
    }
    
    console.log('🧪 Test completed. Check server status with:');
    console.log('   curl -s http://localhost:8501/tools/check_tools_status | grep chatgpt');
}

// Run the tests
runTests();