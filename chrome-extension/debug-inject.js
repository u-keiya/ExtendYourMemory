// Debug script to manually inject and test ChatGPT bridge
console.log('🔧 DEBUG: Manual ChatGPT bridge injection');

// Check if we're on ChatGPT
if (window.location.hostname === 'chat.openai.com') {
    console.log('✅ On ChatGPT domain');
    
    // Try to manually create and test the bridge
    try {
        // Simple test bridge
        window.testChatGPTBridge = {
            test: true,
            extractData: function() {
                console.log('🧪 Test extraction running...');
                
                // Get page content
                const pageContent = document.body.textContent || '';
                console.log('📄 Page content length:', pageContent.length);
                
                // Create test conversation
                const testConversation = {
                    id: 'test_' + Date.now(),
                    title: 'Manual Test Conversation',
                    create_time: Date.now() / 1000,
                    update_time: Date.now() / 1000,
                    mapping: {
                        'test_msg': {
                            message: {
                                content: {
                                    parts: ['This is a manually injected test conversation from ChatGPT.']
                                },
                                role: 'assistant',
                                create_time: Date.now() / 1000
                            }
                        }
                    },
                    metadata: {
                        source: 'manual_test',
                        url: window.location.href,
                        extracted_at: Date.now() / 1000
                    }
                };
                
                console.log('🧪 Test conversation created:', testConversation);
                
                // Send to server
                this.sendToServer([testConversation]);
                
                return testConversation;
            },
            
            async sendToServer(conversations) {
                try {
                    console.log('📤 Sending test data to server...');
                    
                    const response = await fetch('http://localhost:8501/api/chatgpt/conversations', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            conversation_items: conversations,
                            client_id: 'manual_test_client',
                            timestamp: Date.now()
                        })
                    });
                    
                    if (response.ok) {
                        const result = await response.json();
                        console.log('✅ Successfully sent to server:', result);
                    } else {
                        console.error('❌ Server error:', response.status, response.statusText);
                    }
                } catch (error) {
                    console.error('❌ Network error:', error);
                }
            }
        };
        
        console.log('✅ Test bridge created. Run: window.testChatGPTBridge.extractData()');
        
    } catch (error) {
        console.error('❌ Failed to create test bridge:', error);
    }
} else {
    console.log('❌ Not on ChatGPT domain. Current domain:', window.location.hostname);
}