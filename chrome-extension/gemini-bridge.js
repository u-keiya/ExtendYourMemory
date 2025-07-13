// Gemini Bridge Script - Injected into gemini.google.com pages
console.log('📱 Gemini Bridge: Loading...');

class GeminiBridge {
    constructor() {
        this.conversationCache = [];
        this.isInitialized = false;
        this.mcpServerUrl = 'http://localhost:8501';
    }

    async initialize() {
        if (this.isInitialized) return;
        
        console.log('🔧 Initializing Gemini Bridge...');
        this.isInitialized = true;
        
        // Auto-extract conversations after page loads
        setTimeout(() => {
            this.extractConversations();
        }, 3000);
        
        // Periodic extraction disabled to avoid excessive requests
        // setInterval(() => {
        //     console.log('🔄 Periodic Gemini conversation check...');
        //     this.extractConversations();
        // }, 30000); // Check every 30 seconds
        
        // Listen for navigation changes
        this.setupNavigationListener();
    }

    setupNavigationListener() {
        // Watch for URL changes in SPA
        let currentUrl = window.location.href;
        setInterval(() => {
            if (window.location.href !== currentUrl) {
                currentUrl = window.location.href;
                console.log('🔄 Navigation detected, re-extracting conversations...');
                setTimeout(() => {
                    this.extractConversations();
                }, 2000);
            }
        }, 1000);
        
        // Listen for DOM changes that might indicate new conversations
        const observer = new MutationObserver((mutations) => {
            let shouldReextract = false;
            
            mutations.forEach((mutation) => {
                if (mutation.addedNodes.length > 0) {
                    mutation.addedNodes.forEach((node) => {
                        if (node.nodeType === Node.ELEMENT_NODE) {
                            // Check if new conversation-related elements were added
                            const hasConversationElements = node.querySelector && (
                                node.querySelector('[class*="conversation"]') ||
                                node.querySelector('a[href*="/app/"]') ||
                                node.querySelector('[data-message-author-role]')
                            );
                            
                            if (hasConversationElements) {
                                shouldReextract = true;
                            }
                        }
                    });
                }
            });
            
            if (shouldReextract) {
                console.log('🔄 New conversation elements detected, re-extracting...');
                setTimeout(() => {
                    this.extractConversations();
                }, 1000);
            }
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }

    async extractConversations() {
        console.log('🔍 Extracting Gemini conversations...');
        
        const conversations = [];
        
        // Method 1: Try to extract from conversation history first
        await this.extractFromHistory(conversations);
        
        // Method 2: Extract from current page if no history found
        if (conversations.length === 0) {
            await this.extractFromCurrentPage(conversations);
        }
        
        console.log('📦 Total Gemini conversations extracted:', conversations.length);
        
        // Send to content script
        window.postMessage({
            type: 'GEMINI_CONVERSATIONS_EXTRACTED',
            conversations: conversations,
            timestamp: Date.now()
        }, '*');
        
        return conversations;
    }

    async extractFromHistory(conversations) {
        console.log('🔍 Attempting to extract from Gemini history...');
        
        // Look for conversation history elements with more comprehensive selectors
        const historySelectors = [
            // Specific data attributes
            '[data-conversation-id]',
            '[data-chat-id]',
            '[data-thread-id]',
            
            // Class-based selectors
            '.conversation-item',
            '.chat-item', 
            '.history-item',
            '[class*="conversation"]',
            '[class*="history"]',
            '[class*="chat"]',
            '[class*="thread"]',
            
            // Role-based selectors
            'li[role="option"]',
            'li[role="menuitem"]',
            'div[role="button"]',
            'button[role="menuitem"]',
            
            // Link-based selectors (most inclusive)
            'a[href*="/app/"]',
            'a[href*="chat"]',
            'a[href*="conversation"]',
            
            // Generic navigation elements
            'nav li',
            'aside li',
            '[class*="sidebar"] li',
            '[class*="nav"] li',
            
            // Clickable elements that might be conversations
            'li:has(a)',
            'div[tabindex="0"]',
            'div[role="listitem"]',
            'li[tabindex]'
        ];
        
        let historyItems = [];
        
        // First, let's debug what elements are actually available
        console.log('🔧 Debugging available elements...');
        
        // Check for common sidebar/navigation containers
        const containers = document.querySelectorAll('nav, aside, [class*="sidebar"], [class*="nav"], [class*="menu"]');
        console.log(`Found ${containers.length} potential containers:`, 
            Array.from(containers).map(c => c.className || c.tagName));
        
        // Check for lists within those containers
        containers.forEach((container, index) => {
            const lists = container.querySelectorAll('ul, ol, div[role="list"]');
            const items = container.querySelectorAll('li, div[role="listitem"], a, button');
            console.log(`Container ${index} has ${lists.length} lists and ${items.length} items`);
        });
        
        for (const selector of historySelectors) {
            const elements = document.querySelectorAll(selector);
            
            if (elements.length > 0) {
                console.log(`✅ Found ${elements.length} elements with selector "${selector}"`);
                // Log some details about what we found
                Array.from(elements).slice(0, 3).forEach((el, i) => {
                    console.log(`  Item ${i}: "${el.textContent?.trim().substring(0, 50)}" | href: ${el.href || 'none'} | class: ${el.className}`);
                });
                
                if (elements.length > historyItems.length) {
                    historyItems = Array.from(elements);
                }
            } else {
                console.log(`❌ No elements found for selector "${selector}"`);
            }
        }
        
        // If we found multiple selectors, use the one with the most elements
        console.log(`📊 Best match: ${historyItems.length} elements`);
        
        if (historyItems.length === 0) {
            console.log('⚠️ No conversation history found, will extract from current page');
            return;
        }
        
        console.log(`📚 Found ${historyItems.length} potential conversation history items`);
        
        // Extract conversation data from history items
        historyItems.forEach((item, index) => {
            try {
                let title = 'Gemini Conversation';
                let conversationId = null;
                let url = window.location.href;
                
                // Try to extract title
                const titleElement = item.querySelector('[class*="title"], .conversation-title, h3, h4, span[title]');
                if (titleElement) {
                    title = titleElement.textContent?.trim() || title;
                } else {
                    title = item.textContent?.trim().substring(0, 50) || title;
                }
                
                // Try to extract conversation ID
                conversationId = item.getAttribute('data-conversation-id') || 
                               item.getAttribute('data-id') ||
                               item.id ||
                               this.extractIdFromElement(item);
                
                if (!conversationId) {
                    conversationId = 'gemini_history_' + index + '_' + Date.now();
                }
                
                // Try to extract URL or generate conversation URL
                const linkElement = item.querySelector('a[href]') || (item.tagName === 'A' ? item : null);
                if (linkElement && linkElement.href) {
                    url = linkElement.href;
                } else {
                    // If no direct link, try to find parent container with conversation context
                    const parentWithClick = item.closest('[onclick], [data-href]');
                    if (parentWithClick) {
                        const onclick = parentWithClick.getAttribute('onclick') || '';
                        const dataHref = parentWithClick.getAttribute('data-href') || '';
                        const idMatch = onclick.match(/[a-f0-9]{16,}/) || dataHref.match(/[a-f0-9]{16,}/);
                        if (idMatch) {
                            conversationId = idMatch[0];
                            url = `https://gemini.google.com/app/${conversationId}`;
                        }
                    }
                    
                    // If still no URL, generate one based on the title hash
                    if (!conversationId || conversationId.startsWith('gemini_history_')) {
                        // Create a more consistent ID based on title content
                        const titleHash = this.generateIdFromTitle(title);
                        conversationId = `gemini_${titleHash}`;
                        url = `https://gemini.google.com/app/${conversationId}`;
                    }
                }
                
                // Try to extract more detailed content if available
                let detailedContent = title;
                let messageCount = 1;
                
                // Look for conversation preview or snippet text
                const contentElements = item.querySelectorAll('*');
                for (const el of contentElements) {
                    const text = el.textContent?.trim();
                    if (text && text.length > title.length && text.length < 500) {
                        // This might be a conversation snippet
                        detailedContent = text;
                        // Estimate message count based on content length and typical patterns
                        messageCount = Math.max(1, Math.floor(text.length / 100));
                        break;
                    }
                }
                
                // Create conversation object with available content
                const conversation = {
                    id: conversationId,
                    title: title,
                    create_time: Date.now() / 1000,
                    update_time: Date.now() / 1000,
                    mapping: {
                        'extracted_content': {
                            message: {
                                content: {
                                    parts: [detailedContent]
                                },
                                role: 'assistant',
                                create_time: Date.now() / 1000
                            }
                        }
                    },
                    metadata: {
                        source: 'gemini_history_extraction',
                        url: url,
                        extracted_at: Date.now() / 1000,
                        message_count: messageCount,
                        extraction_method: 'history_with_content',
                        content_length: detailedContent.length
                    }
                };
                
                conversations.push(conversation);
                console.log(`✅ Extracted history item ${index + 1}: "${title}"`);
                
            } catch (error) {
                console.warn(`Failed to extract history item ${index}:`, error);
            }
        });
    }

    async extractFromCurrentPage(conversations) {
        console.log('🔍 Extracting from current Gemini page...');
        
        let messages = [];
        
        // Method 1: Extract from Gemini's conversation UI
        const conversationMethods = [
            // Method A: Look for Gemini message containers
            () => {
                const messageContainers = document.querySelectorAll('[data-message-author-role], [role="presentation"], article, .conversation-turn');
                console.log('Method A: Found ' + messageContainers.length + ' message containers');
                
                messageContainers.forEach((container, index) => {
                    const content = container.textContent?.trim();
                    if (content && content.length > 20) {
                        let role = 'assistant'; // Default to Gemini
                        
                        // Try to detect user messages
                        const authorRole = container.getAttribute('data-message-author-role');
                        if (authorRole === 'user' || content.match(/^(You|ユーザー):/i)) {
                            role = 'user';
                        }
                        
                        messages.push({
                            id: 'msg_container_' + index,
                            role: role,
                            content: content,
                            timestamp: Date.now() / 1000
                        });
                    }
                });
            },
            
            // Method B: Look for specific Gemini UI elements
            () => {
                const geminiElements = document.querySelectorAll('.conversation-content, .message-content, .chat-message, .response-container');
                console.log('Method B: Found ' + geminiElements.length + ' Gemini elements');
                
                geminiElements.forEach((element, index) => {
                    const content = element.textContent?.trim();
                    if (content && content.length > 20) {
                        // Check context for role determination
                        let role = 'assistant';
                        const parentElement = element.closest('[data-role], [class*="user"]');
                        if (parentElement && (parentElement.dataset.role === 'user' || parentElement.className.includes('user'))) {
                            role = 'user';
                        }
                        
                        messages.push({
                            id: 'msg_gemini_' + index,
                            role: role,
                            content: content,
                            timestamp: Date.now() / 1000
                        });
                    }
                });
            },
            
            // Method C: General text content extraction
            () => {
                const textElements = document.querySelectorAll('p, div[class*="text"], .markdown, .prose');
                console.log('Method C: Found ' + textElements.length + ' text elements');
                
                let currentRole = 'user';
                textElements.forEach((element, index) => {
                    const content = element.textContent?.trim();
                    if (content && content.length > 30 && !content.includes('Gemini') && !content.includes('Google')) {
                        // Alternate between user and assistant
                        currentRole = currentRole === 'user' ? 'assistant' : 'user';
                        
                        messages.push({
                            id: 'msg_text_' + index,
                            role: currentRole,
                            content: content,
                            timestamp: Date.now() / 1000
                        });
                    }
                });
            }
        ];
        
        // Try each extraction method
        for (let i = 0; i < conversationMethods.length; i++) {
            try {
                conversationMethods[i]();
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
        
        // Create conversation object
        if (uniqueMessages.length > 0) {
            const pageTitle = document.title?.replace(' - Gemini', '').replace(' - Bard', '').trim() || 'Gemini Conversation';
            const conversationId = this.extractConversationIdFromUrl() || 'gemini_session_' + Date.now();
            
            const conversation = {
                id: conversationId,
                title: pageTitle,
                create_time: Date.now() / 1000,
                update_time: Date.now() / 1000,
                mapping: {},
                metadata: {
                    source: 'gemini_page_injection',
                    url: window.location.href,
                    extracted_at: Date.now() / 1000,
                    message_count: uniqueMessages.length
                }
            };
            
            // Add messages to mapping
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
            console.log('✅ Created Gemini conversation with ' + uniqueMessages.length + ' messages');
        } else {
            // Fallback: create conversation from page content
            console.log('⚠️ No structured messages found, using page content fallback');
            const pageText = document.body ? document.body.textContent : '';
            if (pageText.length > 100) {
                const pageTitle = document.title?.replace(' - Gemini', '').trim() || 'Gemini Session';
                
                const fallbackConversation = {
                    id: 'gemini_page_' + Date.now(),
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
                        source: 'gemini_page_injection_fallback',
                        url: window.location.href,
                        extracted_at: Date.now() / 1000,
                        message_count: 1
                    }
                };
                conversations.push(fallbackConversation);
            }
        }
        
        console.log('📦 Extracted Gemini conversations:', conversations.length);
        
        // Send to content script
        window.postMessage({
            type: 'GEMINI_CONVERSATIONS_EXTRACTED',
            conversations: conversations,
            timestamp: Date.now()
        }, '*');
        
        return conversations;
    }

    extractConversationIdFromUrl() {
        // Extract conversation ID from Gemini URL
        const url = window.location.href;
        const matches = url.match(/\/app\/([a-f0-9-]+)/);
        return matches ? matches[1] : null;
    }

    extractIdFromElement(element) {
        // Try to extract ID from various attributes or URL patterns
        const href = element.getAttribute('href') || '';
        const onclick = element.getAttribute('onclick') || '';
        
        // Look for Gemini conversation ID patterns
        const patterns = [
            /\/app\/([a-f0-9-]+)/,
            /conversation[_-]?id[=:]?([a-f0-9-]+)/i,
            /id[=:]?([a-f0-9-]+)/i
        ];
        
        for (const pattern of patterns) {
            const match = href.match(pattern) || onclick.match(pattern);
            if (match && match[1]) {
                return match[1];
            }
        }
        
        return null;
    }

    generateIdFromTitle(title) {
        // Generate a consistent hash-like ID from title
        let hash = 0;
        const cleanTitle = title.replace(/[^\w\s]/g, '').trim();
        
        for (let i = 0; i < cleanTitle.length; i++) {
            const char = cleanTitle.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash; // Convert to 32-bit integer
        }
        
        // Convert to positive hex and pad to ensure consistent length
        const hexHash = Math.abs(hash).toString(16).padStart(8, '0');
        return hexHash + Date.now().toString(16).slice(-8);
    }

    async sendToMCPServer(conversations) {
        if (!conversations || conversations.length === 0) {
            console.log('⚠️ No conversations to send to MCP server');
            return;
        }

        try {
            console.log('📤 Sending ' + conversations.length + ' conversations to MCP server...');
            
            const response = await fetch(this.mcpServerUrl + '/api/gemini/conversations', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    conversation_items: conversations,
                    source: 'gemini_extension',
                    timestamp: Date.now()
                })
            });

            if (response.ok) {
                const result = await response.json();
                console.log('✅ Successfully sent Gemini conversations to MCP server:', result);
                return result;
            } else {
                console.error('❌ Failed to send conversations:', response.status, response.statusText);
            }
        } catch (error) {
            console.error('❌ Error sending conversations to MCP server:', error);
        }
    }
}

// Content script bridge functions
const geminiBridge = {
    version: '1.0.0',
    
    async sendToMCPServer(conversations) {
        try {
            console.log('📤 Forwarding Gemini conversations to MCP server...');
            
            const response = await fetch('http://localhost:8501/api/gemini/conversations', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    conversation_items: conversations,
                    source: 'gemini_extension',
                    timestamp: Date.now()
                })
            });

            if (response.ok) {
                const result = await response.json();
                console.log('✅ Gemini conversations sent successfully:', result);
                return result;
            } else {
                console.error('❌ Failed to send Gemini conversations:', response.status);
                return null;
            }
        } catch (error) {
            console.error('❌ Error sending Gemini conversations:', error);
            return null;
        }
    }
};

// Auto-initialize bridge on page load
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Gemini Bridge: Page loaded, initializing...');
    const bridge = new GeminiBridge();
    bridge.initialize();
});

// Also initialize if DOM is already loaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        const bridge = new GeminiBridge();
        bridge.initialize();
    });
} else {
    const bridge = new GeminiBridge();
    bridge.initialize();
}

// Listen for messages from injected script
window.addEventListener('message', async (event) => {
    if (event.source !== window) return;
    
    if (event.data.type === 'GEMINI_CONVERSATIONS_EXTRACTED') {
        console.log('📨 Received Gemini conversations from page script:', event.data.conversations.length);
        
        try {
            await geminiBridge.sendToMCPServer(event.data.conversations);
            console.log('✅ Successfully forwarded Gemini conversations to MCP server');
        } catch (error) {
            console.error('❌ Failed to forward Gemini conversations:', error);
        }
    }
});

console.log('✅ Gemini Bridge loaded successfully');

// Add manual debug function for immediate testing
window.debugGeminiHistory = function() {
    console.log('🔍 Manual Gemini history debug...');
    
    // Check all possible conversation elements
    const allLinks = document.querySelectorAll('a');
    const conversationLinks = Array.from(allLinks).filter(a => 
        a.href && a.href.includes('/app/') && a.textContent.trim().length > 0
    );
    
    console.log(`Found ${allLinks.length} total links, ${conversationLinks.length} conversation links:`);
    conversationLinks.forEach((link, i) => {
        console.log(`  ${i}: "${link.textContent.trim()}" -> ${link.href}`);
    });
    
    // Check all list items
    const allListItems = document.querySelectorAll('li');
    console.log(`Found ${allListItems.length} list items`);
    
    // Check elements with conversation-like text
    const allElements = document.querySelectorAll('*');
    const conversationElements = Array.from(allElements).filter(el => {
        const text = el.textContent?.trim() || '';
        return text.length > 10 && text.length < 100 && 
               !el.querySelector('*') && // No child elements
               (text.match(/\?|問|質問|how|what|why/i) || text.includes('...'));
    });
    
    console.log(`Found ${conversationElements.length} potential conversation title elements:`);
    conversationElements.slice(0, 10).forEach((el, i) => {
        console.log(`  ${i}: "${el.textContent.trim()}" (${el.tagName}.${el.className})`);
    });
    
    return {
        totalLinks: allLinks.length,
        conversationLinks: conversationLinks.length,
        listItems: allListItems.length,
        potentialTitles: conversationElements.length
    };
};

console.log('💡 Run window.debugGeminiHistory() in console to debug conversation detection');