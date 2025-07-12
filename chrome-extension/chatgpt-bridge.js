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
        return window.location.hostname === 'chat.openai.com';
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
            const conversations = [];
            
            // Try to get conversations from localStorage first
            const localStorageData = this.extractFromLocalStorage();
            if (localStorageData.length > 0) {
                conversations.push(...localStorageData);
            }

            // Try to extract from DOM
            const domData = this.extractFromDOM();
            if (domData.length > 0) {
                conversations.push(...domData);
            }

            console.log(`Extracted ${conversations.length} conversations from ChatGPT`);
            return conversations;
        } catch (error) {
            console.error('Error extracting conversations:', error);
            return [];
        }
    }

    extractFromLocalStorage() {
        try {
            const conversations = [];
            
            // Check for conversation data in localStorage
            for (let i = 0; i < localStorage.length; i++) {
                const key = localStorage.key(i);
                if (key && key.includes('conversation')) {
                    try {
                        const data = JSON.parse(localStorage.getItem(key));
                        if (data && this.isValidConversationData(data)) {
                            conversations.push(this.formatConversationData(data));
                        }
                    } catch (e) {
                        // Skip invalid JSON
                    }
                }
            }

            return conversations;
        } catch (error) {
            console.error('Error extracting from localStorage:', error);
            return [];
        }
    }

    extractFromDOM() {
        try {
            const conversations = [];
            
            // Try to find conversation elements in the DOM
            const conversationElements = document.querySelectorAll('[data-testid*="conversation"], .conversation-item, .chat-item');
            
            conversationElements.forEach((element, index) => {
                try {
                    const conversationData = this.parseConversationElement(element, index);
                    if (conversationData) {
                        conversations.push(conversationData);
                    }
                } catch (e) {
                    console.warn('Error parsing conversation element:', e);
                }
            });

            return conversations;
        } catch (error) {
            console.error('Error extracting from DOM:', error);
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
                console.log('Successfully sent ChatGPT conversations to MCP server:', result);
            } else {
                console.error('Failed to send conversations to MCP server:', response.status, response.statusText);
            }
        } catch (error) {
            console.error('Error sending conversations to MCP server:', error);
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
        console.log('Manual ChatGPT conversation extraction triggered');
        await this.extractAndSendConversations();
    }
}

// Initialize ChatGPT bridge when the script loads
const chatgptBridge = new ChatGPTBridge();

// Auto-initialize if we're on ChatGPT
if (chatgptBridge.isChatGPTPage()) {
    chatgptBridge.initialize();
}

// Make bridge available globally for testing
window.chatgptBridge = chatgptBridge;

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