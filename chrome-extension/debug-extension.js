// Extension Debug Script - Run this in ChatGPT page console
console.log('🔧 Extension Debug Script Starting...');

// 1. Check extension installation
console.log('=== EXTENSION INSTALLATION CHECK ===');
console.log('Chrome API available:', typeof chrome !== 'undefined');
console.log('Runtime available:', typeof chrome !== 'undefined' && !!chrome.runtime);
console.log('Extension ID:', chrome?.runtime?.id || 'Not available');

// 2. Check manifest and content scripts
if (chrome?.runtime?.getManifest) {
    try {
        const manifest = chrome.runtime.getManifest();
        console.log('Extension name:', manifest.name);
        console.log('Version:', manifest.version);
        console.log('Content scripts:', manifest.content_scripts?.length || 0);
        
        // Check if current page matches content script patterns
        const currentUrl = window.location.href;
        console.log('Current URL:', currentUrl);
        
        manifest.content_scripts?.forEach((script, index) => {
            console.log(`Content script ${index}:`, {
                matches: script.matches,
                js: script.js,
                run_at: script.run_at
            });
            
            // Check if current URL matches
            const matches = script.matches.some(pattern => {
                const regex = new RegExp(pattern.replace(/\*/g, '.*'));
                return regex.test(currentUrl);
            });
            console.log(`  Matches current URL: ${matches}`);
        });
    } catch (error) {
        console.error('Failed to get manifest:', error);
    }
}

// 3. Check if ChatGPT bridge is injected
console.log('=== CHATGPT BRIDGE CHECK ===');
console.log('window.chatgptBridge exists:', !!window.chatgptBridge);
if (window.chatgptBridge) {
    console.log('Bridge type:', typeof window.chatgptBridge);
    console.log('Bridge properties:', Object.keys(window.chatgptBridge));
    console.log('Is available:', window.chatgptBridge.isAvailable);
    console.log('Version:', window.chatgptBridge.version);
}

// 4. Check for content script injection
console.log('=== CONTENT SCRIPT CHECK ===');
const scripts = Array.from(document.querySelectorAll('script'));
const extensionScripts = scripts.filter(script => 
    script.src && script.src.includes('chrome-extension')
);
console.log('Extension scripts found:', extensionScripts.length);
extensionScripts.forEach((script, index) => {
    console.log(`Script ${index}:`, script.src);
});

// 5. Check console for extension messages
console.log('=== CONSOLE MESSAGE CHECK ===');
console.log('Look for messages starting with:');
console.log('- 🚀 Injecting ChatGPT Bridge');
console.log('- ✅ ChatGPT Bridge injected');
console.log('- 🔄 Auto-extracting');

// 6. Manual bridge injection test
console.log('=== MANUAL INJECTION TEST ===');
if (!window.chatgptBridge) {
    console.log('⚠️ Bridge not found, attempting manual injection...');
    
    // Create a simple test bridge
    window.testChatGPTBridge = {
        test: true,
        version: 'manual_1.0',
        extractNow: function() {
            console.log('🧪 Manual extraction test');
            const testData = {
                id: 'manual_test_' + Date.now(),
                title: 'Manual Console Test',
                create_time: Date.now() / 1000,
                mapping: {
                    'test': {
                        message: {
                            content: { parts: ['Manual test from console'] },
                            role: 'user'
                        }
                    }
                }
            };
            
            // Try to send to extension
            if (chrome?.runtime?.sendMessage) {
                chrome.runtime.sendMessage({
                    type: 'SEND_CHATGPT_CONVERSATIONS',
                    data: {
                        conversation_items: [testData],
                        client_id: 'manual_console',
                        timestamp: Date.now()
                    }
                }, (response) => {
                    if (chrome.runtime.lastError) {
                        console.error('❌ Extension messaging failed:', chrome.runtime.lastError);
                    } else {
                        console.log('✅ Extension messaging success:', response);
                    }
                });
            } else {
                console.error('❌ chrome.runtime.sendMessage not available');
            }
            
            return testData;
        }
    };
    
    console.log('✅ Test bridge created: window.testChatGPTBridge');
    console.log('Run: window.testChatGPTBridge.extractNow()');
}

// 7. Extension permissions check
console.log('=== PERMISSIONS CHECK ===');
if (chrome?.permissions?.getAll) {
    chrome.permissions.getAll((permissions) => {
        console.log('Extension permissions:', permissions);
    });
} else {
    console.log('⚠️ Cannot check permissions - API not available');
}

// 8. Troubleshooting steps
console.log('=== TROUBLESHOOTING STEPS ===');
console.log('If bridge is not working:');
console.log('1. Go to chrome://extensions/');
console.log('2. Find "Extend Your Memory" extension');
console.log('3. Click the reload button (🔄)');
console.log('4. Refresh this ChatGPT page');
console.log('5. Check for errors in extension background script:');
console.log('   - Go to chrome://extensions/');
console.log('   - Click "Details" on the extension');
console.log('   - Click "Inspect views: background page"');

console.log('🔧 Extension debug completed');