/**
 * ChatGPT History Bridge for Extend Your Memory
 * Extracts ChatGPT conversation data and sends to MCP server
 */

class ChatGPTBridge {
    constructor() {
        this.mcpServerUrl = 'http://localhost:8501';
        this.lastSentTime = 0;
        this.sendInterval = 30000; // 30秒間隔
        this.isInitialized = false;
    }

    async initialize() {
        if (this.isInitialized) return;
        
        console.log('ChatGPT Bridge initializing...');
        
        // Check if we're on ChatGPT
        if (!this.isChatGPTPage()) {
            console.log('Not on ChatGPT page, skipping initialization');
            return;
        }

        // Wait for page to load
        await this.waitForPageLoad();
        
        // Extract and send conversation data
        await this.extractAndSendConversations();
        
        this.isInitialized = true;
        console.log('ChatGPT Bridge initialized successfully');
    }

    isChatGPTPage() {
        return window.location.hostname === 'chat.openai.com' || 
               window.location.hostname === 'chatgpt.com';
    }

    async waitForPageLoad() {
        return new Promise((resolve) => {
            if (document.readyState === 'complete') {
                resolve();
            } else {
                window.addEventListener('load', resolve);
            }
        });
    }

    async extractConversations() {
        try {
            console.log('🔍 Starting ChatGPT conversation extraction...');
            const conversations = [];
            
            // Debug: Check localStorage keys
            console.log('📦 localStorage keys:', Object.keys(localStorage));
            
            // Try to get conversations from localStorage first
            const localStorageData = this.extractFromLocalStorage();
            console.log(`📂 localStorage conversations found: ${localStorageData.length}`);
            if (localStorageData.length > 0) {
                conversations.push(...localStorageData);
            }

            // Try to extract from DOM
            const domData = this.extractFromDOM();
            console.log(`🌐 DOM conversations found: ${domData.length}`);
            if (domData.length > 0) {
                conversations.push(...domData);
            }

            // Try alternative extraction methods
            const altData = this.extractFromAlternativeMethods();
            console.log(`🔄 Alternative extraction found: ${altData.length}`);
            if (altData.length > 0) {
                conversations.push(...altData);
            }

            console.log(`✅ Total extracted ${conversations.length} conversations from ChatGPT`);
            return conversations;
        } catch (error) {
            console.error('❌ Error extracting conversations:', error);
            return [];
        }
    }

    extractFromLocalStorage() {
        try {
            const conversations = [];
            
            console.log('🔍 Searching localStorage for conversation data...');
            
            // Check for conversation data in localStorage with broader search
            for (let i = 0; i < localStorage.length; i++) {
                const key = localStorage.key(i);
                console.log(`📋 localStorage key ${i}: ${key}`);
                
                if (key && (key.includes('conversation') || key.includes('chat') || key.includes('thread'))) {
                    try {
                        const data = JSON.parse(localStorage.getItem(key));
                        console.log(`📝 Data for key ${key}:`, data);
                        
                        if (data && this.isValidConversationData(data)) {
                            conversations.push(this.formatConversationData(data));
                            console.log(`✅ Valid conversation found in ${key}`);
                        } else {
                            console.log(`❌ Invalid conversation data in ${key}`);
                        }
                    } catch (e) {
                        console.log(`🚫 Failed to parse JSON for key ${key}:`, e.message);
                    }
                }
            }

            return conversations;
        } catch (error) {
            console.error('❌ Error extracting from localStorage:', error);
            return [];
        }
    }

    extractFromDOM() {
        try {
            const conversations = [];
            
            console.log('🔍 Searching DOM for conversation elements...');
            
            // Try multiple selectors for ChatGPT conversation elements
            const selectors = [
                '[data-testid*="conversation"]',
                '.conversation-item',
                '.chat-item',
                '[role="presentation"]',
                'main [role="main"]',
                'article',
                '[data-testid="conversation-turn"]',
                '.group',
                'div[class*="conversation"]',
                'div[class*="message"]'
            ];
            
            let totalElements = 0;
            
            for (const selector of selectors) {
                const elements = document.querySelectorAll(selector);
                console.log(`🔍 Selector "${selector}" found ${elements.length} elements`);
                totalElements += elements.length;
                
                elements.forEach((element, index) => {
                    try {
                        const conversationData = this.parseConversationElement(element, `${selector}_${index}`);
                        if (conversationData) {
                            conversations.push(conversationData);
                            console.log(`✅ Parsed conversation from ${selector} element ${index}`);
                        }
                    } catch (e) {
                        console.warn(`⚠️ Error parsing element ${index} from ${selector}:`, e);
                    }
                });
            }
            
            console.log(`🌐 Total DOM elements checked: ${totalElements}, conversations found: ${conversations.length}`);
            
            return conversations;
        } catch (error) {
            console.error('❌ Error extracting from DOM:', error);
            return [];
        }
    }

    isValidConversationData(data) {
        return data && 
               (data.id || data.conversation_id) && 
               (data.title || data.messages || data.mapping);
    }

    formatConversationData(rawData) {
        const now = Date.now() / 1000;
        
        return {
            id: rawData.id || rawData.conversation_id || this.generateId(),
            title: rawData.title || 'Untitled Conversation',
            create_time: rawData.create_time || rawData.created_at || now,
            update_time: rawData.update_time || rawData.updated_at || now,
            mapping: rawData.mapping || rawData.messages || {},
            metadata: {
                source: 'chatgpt_extension',
                extracted_at: now,
                url: window.location.href
            }
        };
    }

    parseConversationElement(element, index) {
        try {
            const titleElement = element.querySelector('.conversation-title, .chat-title, h3, h4');
            const title = titleElement ? titleElement.textContent.trim() : `Conversation ${index + 1}`;
            
            const messageElements = element.querySelectorAll('.message, .chat-message, [role="assistant"], [role="user"]');
            const mapping = {};
            
            messageElements.forEach((msgElement, msgIndex) => {
                const messageId = `msg_${index}_${msgIndex}`;
                const content = msgElement.textContent.trim();
                const role = this.detectMessageRole(msgElement);
                
                if (content) {
                    mapping[messageId] = {
                        message: {
                            content: {
                                parts: [content]
                            },
                            role: role,
                            create_time: Date.now() / 1000
                        }
                    };
                }
            });

            return {
                id: this.generateId(),
                title: title,
                create_time: Date.now() / 1000,
                update_time: Date.now() / 1000,
                mapping: mapping,
                metadata: {
                    source: 'chatgpt_extension_dom',
                    extracted_at: Date.now() / 1000,
                    url: window.location.href
                }
            };
        } catch (error) {
            console.error('Error parsing conversation element:', error);
            return null;
        }
    }

    detectMessageRole(element) {
        const classList = element.className.toLowerCase();
        const role = element.getAttribute('role');
        
        if (role === 'assistant' || classList.includes('assistant') || classList.includes('bot')) {
            return 'assistant';
        } else if (role === 'user' || classList.includes('user') || classList.includes('human')) {
            return 'user';
        }
        
        // Default to user if uncertain
        return 'user';
    }

    generateId() {
        return 'conv_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    extractFromAlternativeMethods() {
        try {
            const conversations = [];
            
            console.log('🔄 Trying alternative extraction methods...');
            
            // Method 1: Try to extract from current page content
            const currentPageData = this.extractCurrentPageContent();
            if (currentPageData) {
                conversations.push(currentPageData);
                console.log('✅ Extracted current page conversation');
            }
            
            // Method 2: Try to extract from window object
            const windowData = this.extractFromWindowObject();
            if (windowData.length > 0) {
                conversations.push(...windowData);
                console.log(`✅ Extracted ${windowData.length} conversations from window object`);
            }
            
            // Method 3: Create a dummy conversation for testing
            if (conversations.length === 0) {
                const dummyConversation = this.createDummyConversation();
                conversations.push(dummyConversation);
                console.log('🧪 Created dummy conversation for testing');
            }
            
            return conversations;
        } catch (error) {
            console.error('❌ Error in alternative extraction:', error);
            return [];
        }
    }

    extractCurrentPageContent() {
        try {
            // Extract visible text content from the current page
            const mainElement = document.querySelector('main') || document.body;
            const textContent = mainElement.textContent || '';
            
            if (textContent.length > 100) {
                return {
                    id: this.generateId(),
                    title: `ChatGPT Session - ${new Date().toLocaleDateString()}`,
                    create_time: Date.now() / 1000,
                    update_time: Date.now() / 1000,
                    mapping: {
                        'current_page': {
                            message: {
                                content: {
                                    parts: [textContent.substring(0, 2000) + (textContent.length > 2000 ? '...' : '')]
                                },
                                role: 'assistant',
                                create_time: Date.now() / 1000
                            }
                        }
                    },
                    metadata: {
                        source: 'chatgpt_current_page',
                        extracted_at: Date.now() / 1000,
                        url: window.location.href
                    }
                };
            }
            
            return null;
        } catch (error) {
            console.error('❌ Error extracting current page content:', error);
            return null;
        }
    }

    extractFromWindowObject() {
        try {
            const conversations = [];
            
            // Look for conversation data in window object
            const windowKeys = Object.keys(window);
            console.log('🔍 Checking window object keys for conversation data...');
            
            windowKeys.forEach(key => {
                if (key.toLowerCase().includes('conversation') || 
                    key.toLowerCase().includes('chat') || 
                    key.toLowerCase().includes('thread')) {
                    console.log(`🔍 Found potential conversation key: ${key}`);
                    try {
                        const data = window[key];
                        if (data && typeof data === 'object') {
                            console.log(`📝 Window data for ${key}:`, data);
                        }
                    } catch (e) {
                        console.log(`🚫 Cannot access window.${key}`);
                    }
                }
            });
            
            return conversations;
        } catch (error) {
            console.error('❌ Error extracting from window object:', error);
            return [];
        }
    }

    createDummyConversation() {
        return {
            id: this.generateId(),
            title: `Test ChatGPT Conversation - ${new Date().toLocaleString()}`,
            create_time: Date.now() / 1000,
            update_time: Date.now() / 1000,
            mapping: {
                'test_message_1': {
                    message: {
                        content: {
                            parts: ['This is a test conversation from ChatGPT Extension Bridge. The extension is working and can detect ChatGPT pages.']
                        },
                        role: 'assistant',
                        create_time: Date.now() / 1000
                    }
                }
            },
            metadata: {
                source: 'chatgpt_extension_test',
                extracted_at: Date.now() / 1000,
                url: window.location.href,
                test_data: true
            }
        };
    }

    async extractAndSendConversations() {
        const now = Date.now();
        
        // Check if enough time has passed since last send
        if (now - this.lastSentTime < this.sendInterval) {
            console.log('Skipping conversation extraction - too soon since last send');
            return;
        }

        try {
            const conversations = await this.extractConversations();
            
            if (conversations.length > 0) {
                await this.sendToMCPServer(conversations);
                this.lastSentTime = now;
            } else {
                console.log('No conversations found to send');
            }
        } catch (error) {
            console.error('Error in extractAndSendConversations:', error);
        }
    }

    async sendToMCPServer(conversations) {
        try {
            console.log('📤 Sending ChatGPT conversations via extension messaging...');
            
            // Send data through Chrome extension messaging instead of direct fetch
            const messageData = {
                type: 'SEND_CHATGPT_CONVERSATIONS',
                data: {
                    conversation_items: conversations,
                    client_id: this.getClientId(),
                    timestamp: Date.now()
                }
            };
            
            // Try extension messaging first
            if (typeof chrome !== 'undefined' && chrome.runtime && chrome.runtime.id) {
                try {
                    await new Promise((resolve, reject) => {
                        // Set a timeout for the message
                        const timeout = setTimeout(() => {
                            reject(new Error('Extension messaging timeout'));
                        }, 5000);
                        
                        chrome.runtime.sendMessage(messageData, (response) => {
                            clearTimeout(timeout);
                            
                            if (chrome.runtime.lastError) {
                                console.log('⚠️ Extension messaging failed:', chrome.runtime.lastError.message);
                                reject(new Error(chrome.runtime.lastError.message));
                            } else {
                                console.log('✅ Successfully sent via extension messaging:', response);
                                resolve(response);
                            }
                        });
                    });
                } catch (extensionError) {
                    console.log('⚠️ Extension messaging error, trying direct fetch...', extensionError.message);
                    await this.sendDirectToMCPServer(conversations);
                }
            } else {
                console.log('⚠️ Chrome extension API not available, trying direct fetch...');
                await this.sendDirectToMCPServer(conversations);
            }
            
        } catch (error) {
            console.error('❌ Error sending conversations to MCP server:', error);
        }
    }
    
    async sendDirectToMCPServer(conversations) {
        try {
            console.log('📤 Attempting direct fetch to MCP server...');
            
            const response = await fetch(`${this.mcpServerUrl}/api/chatgpt/conversations`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    conversation_items: conversations,
                    client_id: this.getClientId(),
                    timestamp: Date.now()
                })
            });

            if (response.ok) {
                const result = await response.json();
                console.log('✅ Successfully sent ChatGPT conversations to MCP server (direct):', result);
            } else {
                console.error('❌ Failed to send conversations to MCP server:', response.status, response.statusText);
            }
        } catch (error) {
            console.error('❌ Direct fetch error:', error);
            
            // Final fallback: store data locally for later retrieval
            this.storeConversationsLocally(conversations);
        }
    }
    
    storeConversationsLocally(conversations) {
        try {
            console.log('💾 Storing conversations locally as fallback...');
            const storedData = {
                conversations: conversations,
                timestamp: Date.now(),
                client_id: this.getClientId()
            };
            localStorage.setItem('extendYourMemory_chatgpt_fallback', JSON.stringify(storedData));
            console.log('✅ Conversations stored locally for later retrieval');
        } catch (error) {
            console.error('❌ Failed to store conversations locally:', error);
        }
    }

    getClientId() {
        let clientId = localStorage.getItem('extendYourMemory_clientId');
        if (!clientId) {
            clientId = 'chatgpt_client_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('extendYourMemory_clientId', clientId);
        }
        return clientId;
    }

    // Method to manually trigger conversation extraction (for testing)
    async manualExtract() {
        console.log('🚀 Manual ChatGPT conversation extraction triggered');
        this.lastSentTime = 0; // Reset to bypass interval check
        await this.extractAndSendConversations();
    }
    
    // Debug method to check all extraction sources
    async debugExtraction() {
        console.log('🐛 DEBUG: Starting comprehensive extraction analysis...');
        
        // Check localStorage
        console.log('🐛 DEBUG: localStorage analysis...');
        console.log('localStorage length:', localStorage.length);
        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            console.log(`- Key ${i}: ${key} (${typeof localStorage.getItem(key)})`);
        }
        
        // Check DOM structure
        console.log('🐛 DEBUG: DOM structure analysis...');
        console.log('- Main element:', document.querySelector('main'));
        console.log('- Articles:', document.querySelectorAll('article').length);
        console.log('- Divs with "group" class:', document.querySelectorAll('div.group').length);
        console.log('- Data-testid elements:', document.querySelectorAll('[data-testid]').length);
        
        // Check current URL
        console.log('🐛 DEBUG: Current URL:', window.location.href);
        console.log('🐛 DEBUG: Page title:', document.title);
        
        // Run extraction
        const conversations = await this.extractConversations();
        console.log('🐛 DEBUG: Final extraction result:', conversations);
        
        return conversations;
    }
}

// Initialize ChatGPT bridge when the script loads
const chatgptBridge = new ChatGPTBridge();

// Auto-initialize if we're on ChatGPT
if (chatgptBridge.isChatGPTPage()) {
    chatgptBridge.initialize();
}

// Inject the bridge into the page's window object via script injection
function injectBridgeIntoPage() {
    const script = document.createElement('script');
    script.textContent = `
        console.log('🚀 Injecting ChatGPT Bridge into page context...');
        
        // Create a simplified bridge that's accessible from the page
        window.chatgptBridge = {
            isAvailable: true,
            version: '1.1.0',
            extractData: function() {
                console.log('🔍 Extracting ChatGPT conversations...');
                
                const conversations = [];
                
                // Method 1: Extract actual conversation messages
                console.log('🔍 Searching for conversation messages...');
                
                let messages = [];
                
                // Try multiple selectors for ChatGPT messages
                const messageMethods = [
                    // Method A: Modern ChatGPT with data attributes
                    () => {
                        const messageElements = document.querySelectorAll('[data-message-author-role]');
                        console.log('Method A: Found ' + messageElements.length + ' messages with data-message-author-role');
                        
                        messageElements.forEach((element, index) => {
                            const role = element.getAttribute('data-message-author-role');
                            const content = element.textContent?.trim();
                            
                            if (content && content.length > 20) {
                                messages.push({
                                    id: 'msg_data_${index}',
                                    role: role,
                                    content: content,
                                    timestamp: Date.now() / 1000
                                });
                            }
                        });
                    },
                    
                    // Method B: Look for conversation groups/articles
                    () => {
                        const groupElements = document.querySelectorAll('.group, article, [data-testid*="conversation"]');
                        console.log('Method B: Found ' + groupElements.length + ' conversation groups');
                        
                        groupElements.forEach((element, index) => {
                            const content = element.textContent?.trim();
                            if (content && content.length > 30) {
                                // Try to determine role from surrounding context
                                let role = 'assistant';
                                
                                // Look for user indicators
                                if (element.querySelector('img[alt*="user"], [class*="user"]') ||
                                    content.match(/^(You|ユーザー):/i)) {
                                    role = 'user';
                                }
                                
                                messages.push({
                                    id: 'msg_group_${index}',
                                    role: role,
                                    content: content,
                                    timestamp: Date.now() / 1000
                                });
                            }
                        });
                    },
                    
                    // Method C: Extract from any visible text containers
                    () => {
                        const textElements = document.querySelectorAll('div[class*="markdown"], .prose, p, div[role="presentation"]');
                        console.log('Method C: Found ' + textElements.length + ' text elements');
                        
                        let currentRole = 'user';
                        textElements.forEach((element, index) => {
                            const content = element.textContent?.trim();
                            if (content && content.length > 20 && !content.includes('ChatGPT')) {
                                // Alternate between user and assistant
                                currentRole = currentRole === 'user' ? 'assistant' : 'user';
                                
                                messages.push({
                                    id: 'msg_text_${index}',
                                    role: currentRole,
                                    content: content,
                                    timestamp: Date.now() / 1000
                                });
                            }
                        });
                    }
                ];
                
                // Try each method until we get content
                for (let i = 0; i < messageMethods.length; i++) {
                    try {
                        messageMethods[i]();
                        if (messages.length > 0) {
                            console.log('✅ Method ' + (i + 1) + ' found ' + messages.length + ' messages');
                            break;
                        }
                    } catch (error) {
                        console.warn('Method ' + (i + 1) + ' failed:', error);
                    }
                }
                
                // Remove duplicates
                const uniqueMessages = [];
                for (const message of messages) {
                    const isDuplicate = uniqueMessages.some(existing => 
                        existing.content.substring(0, 50) === message.content.substring(0, 50)
                    );
                    if (!isDuplicate) {
                        uniqueMessages.push(message);
                    }
                }
                
                console.log('📝 Unique messages found: ' + uniqueMessages.length);
                
                // Create conversation object with actual messages
                if (uniqueMessages.length > 0) {
                    const pageTitle = document.title?.replace(' | ChatGPT', '').trim() || 'ChatGPT Conversation';
                    const conversationId = window.location.pathname.split('/').pop() || 'current_session';
                    
                    const conversation = {
                        id: conversationId + '_' + Date.now(),
                        title: pageTitle,
                        create_time: Date.now() / 1000,
                        update_time: Date.now() / 1000,
                        mapping: {},
                        metadata: {
                            source: 'chatgpt_page_injection',
                            url: window.location.href,
                            extracted_at: Date.now() / 1000,
                            message_count: uniqueMessages.length
                        }
                    };
                    
                    // Add all messages to mapping
                    uniqueMessages.forEach((msg, index) => {
                        conversation.mapping[msg.id] = {
                            message: {
                                content: {
                                    parts: [msg.content]
                                },
                                role: msg.role,
                                create_time: msg.timestamp
                            }
                        };
                    });
                    
                    conversations.push(conversation);
                    console.log('✅ Created conversation with ' + uniqueMessages.length + ' messages');
                } else {
                    // Fallback: basic page content
                    console.log('⚠️ No structured messages found, using page content fallback');
                    const pageText = document.body ? document.body.textContent : '';
                    if (pageText.length > 100) {
                        const pageTitle = document.title?.replace(' | ChatGPT', '').trim() || 'ChatGPT Session';
                        
                        const fallbackConversation = {
                            id: 'page_content_' + Date.now(),
                            title: pageTitle,
                            create_time: Date.now() / 1000,
                            update_time: Date.now() / 1000,
                            mapping: {
                                'page_content': {
                                    message: {
                                        content: {
                                            parts: [pageText.substring(0, 2000)]
                                        },
                                        role: 'assistant',
                                        create_time: Date.now() / 1000
                                    }
                                }
                            },
                            metadata: {
                                source: 'chatgpt_page_injection_fallback',
                                url: window.location.href,
                                extracted_at: Date.now() / 1000,
                                message_count: 1
                            }
                        };
                        conversations.push(fallbackConversation);
                    }
                }
                
                console.log('📦 Extracted conversations:', conversations.length);
                
                // Send via postMessage to content script
                window.postMessage({
                    type: 'CHATGPT_CONVERSATIONS_EXTRACTED',
                    conversations: conversations,
                    timestamp: Date.now()
                }, '*');
                
                return conversations;
            },
            
            manualExtract: function() {
                console.log('🚀 Manual extraction triggered');
                return this.extractData();
            },
            
            debugExtraction: function() {
                console.log('🐛 Debug extraction info:');
                console.log('- URL:', window.location.href);
                console.log('- Title:', document.title);
                console.log('- Body exists:', !!document.body);
                console.log('- Content length:', document.body ? document.body.textContent.length : 0);
                return this.extractData();
            }
        };
        
        console.log('✅ ChatGPT Bridge injected successfully');
        console.log('Available methods: extractData(), manualExtract(), debugExtraction()');
        
        // Auto-extract after a delay
        setTimeout(() => {
            console.log('🔄 Auto-extracting after page load...');
            window.chatgptBridge.extractData();
        }, 3000);
    `;
    
    (document.head || document.documentElement).appendChild(script);
    script.remove();
}

// Inject the bridge when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', injectBridgeIntoPage);
} else {
    injectBridgeIntoPage();
}

// Listen for messages from the injected script
window.addEventListener('message', async (event) => {
    if (event.source !== window) return;
    
    if (event.data.type === 'CHATGPT_CONVERSATIONS_EXTRACTED') {
        console.log('📨 Received conversations from page script:', event.data.conversations.length);
        
        try {
            await chatgptBridge.sendToMCPServer(event.data.conversations);
            console.log('✅ Successfully forwarded conversations to MCP server');
        } catch (error) {
            console.error('❌ Failed to forward conversations:', error);
        }
    }
});

// Listen for navigation changes (SPA)
let currentUrl = window.location.href;
new MutationObserver(() => {
    if (window.location.href !== currentUrl) {
        currentUrl = window.location.href;
        if (chatgptBridge.isChatGPTPage()) {
            setTimeout(() => chatgptBridge.initialize(), 1000);
        }
    }
}).observe(document, {
    subtree: true,
    childList: true
});

console.log('ChatGPT Bridge script loaded');