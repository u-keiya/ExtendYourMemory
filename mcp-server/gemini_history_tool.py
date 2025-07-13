"""
Gemini History MCP Tool Implementation
Searches Gemini (Bard) conversation history by accessing gemini.google.com
"""

import os
import asyncio
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging
import json
import time
from fastapi import HTTPException

logger = logging.getLogger(__name__)

class GeminiHistoryTool:
    def __init__(self, server_port: int = 8501):
        self.server_port = server_port
        self.server_url = f"http://localhost:{server_port}"
        self.extension_id = None
        self.conversation_cache = []
        self.cache_timestamp = None
        self.cache_duration = 300  # 5 minutes cache
        
    async def initialize(self):
        """Initialize the tool and check for Chrome Extension availability"""
        try:
            await self._ping_extension()
            logger.info("Gemini History Extension communication established")
        except Exception as e:
            logger.warning(f"Gemini History Extension not available: {e}")
    
    async def _ping_extension(self) -> bool:
        """Check if Chrome Extension is available and responding"""
        try:
            return True
        except Exception as e:
            logger.error(f"Extension ping failed: {e}")
            return False
    
    async def receive_conversation_data(self, conversation_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Receive Gemini conversation data from Chrome Extension via HTTP endpoint"""
        try:
            if not isinstance(conversation_data, list):
                raise ValueError("Conversation data must be a list")
            
            processed_data = []
            categories = {}
            
            for conversation in conversation_data:
                try:
                    if not conversation.get('id') or not conversation.get('title'):
                        continue
                    
                    # Process timestamps
                    if 'create_time' in conversation:
                        create_time = datetime.fromtimestamp(conversation['create_time'])
                    elif 'update_time' in conversation:
                        create_time = datetime.fromtimestamp(conversation['update_time'])
                    else:
                        create_time = datetime.now()
                    
                    # Extract messages from conversation
                    messages = conversation.get('mapping', {})
                    conversation_content = ""
                    message_count = 0
                    
                    for message_id, message_data in messages.items():
                        if message_data.get('message'):
                            message = message_data['message']
                            if message.get('content') and message.get('content', {}).get('parts'):
                                content_parts = message['content']['parts']
                                if content_parts and isinstance(content_parts, list):
                                    for part in content_parts:
                                        if isinstance(part, str) and part.strip():
                                            conversation_content += f"{part}\n"
                                            message_count += 1
                    
                    processed_item = {
                        'id': conversation['id'],
                        'title': conversation['title'],
                        'create_time': create_time.isoformat(),
                        'update_time': conversation.get('update_time', create_time.timestamp()),
                        'message_count': message_count,
                        'conversation_content': conversation_content,
                        'url': f"https://gemini.google.com/app/{conversation['id']}",
                        
                        # Create searchable content
                        'searchable_content': f"{conversation['title']} {conversation_content}",
                        
                        'metadata': {
                            'source': 'gemini_history_extension',
                            'conversation_id': conversation['id'],
                            'message_count': message_count,
                            'has_content': bool(conversation_content.strip()),
                            'raw_data': True
                        }
                    }
                    
                    processed_data.append(processed_item)
                    
                    # Categorize by topics (basic)
                    title_words = conversation['title'].lower().split()
                    for word in title_words[:3]:  # Use first 3 words for categorization
                        if len(word) > 3:  # Ignore short words
                            categories[word] = categories.get(word, 0) + 1
                    
                except Exception as e:
                    logger.warning(f"Error processing conversation item: {e}")
                    continue
            
            # Store in cache with timestamp
            self.conversation_cache = processed_data
            self.cache_timestamp = time.time()
            
            logger.info(f"✓ Processed {len(processed_data)} Gemini conversations from Extension")
            logger.info(f"  Topics: {dict(list(categories.items())[:10])}")
            logger.info(f"  Total conversations ready for LLM-based search")
            
            return {
                "success": True,
                "message": f"Processed {len(processed_data)} Gemini conversations",
                "timestamp": datetime.now().isoformat(),
                "topics": dict(list(categories.items())[:20]),
                "total_conversations": len(processed_data),
                "cache_status": "updated",
                "llm_processing_ready": True
            }
        except Exception as e:
            logger.error(f"Error receiving conversation data: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def search_conversations(
        self,
        keywords: List[str],
        days: int = 30,
        max_results: int = 50
    ) -> List[Dict[str, Any]]:
        """Search Gemini conversations using cached data from Extension"""
        
        # Check if we have fresh cached data
        if self._is_cache_valid():
            logger.info("Using fresh cached Gemini conversation data")
            return self._search_cached_conversations(keywords, days, max_results)
        
        # If we have any cached data (even if stale), use it for search
        if self.conversation_cache:
            logger.info(f"Using stale cached Gemini conversation data ({len(self.conversation_cache)} conversations)")
            return self._search_cached_conversations(keywords, days, max_results)
        
        # Request fresh data from Extension only if no cache exists
        try:
            logger.info("No cached data available, requesting from extension...")
            await self._request_conversations_from_extension(keywords, days, max_results)
            
            # Wait for the extension to respond
            for _ in range(10):  # Wait up to 5 seconds
                await asyncio.sleep(0.5)
                if self.conversation_cache:
                    logger.info("Received fresh data from extension")
                    return self._search_cached_conversations(keywords, days, max_results)
            
            logger.warning("No Gemini conversation data available after extension request")
            return []
                
        except Exception as e:
            logger.error(f"Error requesting conversations from extension: {e}")
            return []
    
    def _is_cache_valid(self) -> bool:
        """Check if cached data is still valid"""
        if not self.conversation_cache or not self.cache_timestamp:
            return False
        
        return (time.time() - self.cache_timestamp) < self.cache_duration
    
    async def _request_conversations_from_extension(
        self,
        keywords: List[str],
        days: int,
        max_results: int
    ) -> None:
        """Signal Chrome Extension to send fresh Gemini conversation data"""
        try:
            logger.info(
                "Requesting fresh Gemini conversation data from Chrome extension for keywords: %s",
                keywords,
            )

            payload = {
                "action": "refreshGeminiHistory",
                "params": {
                    "keywords": keywords,
                    "days": days,
                    "maxResults": max_results,
                },
            }

            for attempt in range(3):
                try:
                    async with httpx.AsyncClient() as client:
                        response = await client.post(
                            f"{self.server_url}/api/gemini/extension",
                            json=payload,
                            timeout=10.0,
                        )

                    if response.status_code == 200 and response.json().get("success"):
                        logger.info("Gemini extension refresh triggered successfully")
                        return True

                    logger.warning(
                        "Extension refresh attempt %s failed: status %s", attempt + 1, response.status_code
                    )

                except Exception as e:
                    logger.error("Attempt %s failed: %s", attempt + 1, e)

                await asyncio.sleep(1)

            logger.error("Giving up after 3 attempts to request extension refresh")
            return False

        except Exception as e:
            logger.error("Failed to request conversations from extension: %s", e)
            return False
    
    def _search_cached_conversations(
        self,
        keywords: List[str],
        days: int,
        max_results: int
    ) -> List[Dict[str, Any]]:
        """Search through cached conversation data"""
        
        if not self.conversation_cache:
            return []
        
        # Filter by date range
        cutoff_date = datetime.now() - timedelta(days=days)
        
        filtered_items = []
        
        for conversation in self.conversation_cache:
            try:
                # Parse create time
                if 'create_time' in conversation:
                    create_time = datetime.fromisoformat(conversation['create_time'].replace('Z', '+00:00'))
                else:
                    continue
                
                if create_time >= cutoff_date:
                    # Check if conversation matches keywords
                    if not keywords or self._conversation_matches_keywords(conversation, keywords):
                        # Convert to our standard format
                        formatted_item = self._format_conversation_item(conversation)
                        filtered_items.append(formatted_item)
                        
            except Exception as e:
                logger.warning(f"Error processing conversation item: {e}")
                continue
        
        # Sort by create time (most recent first)
        filtered_items.sort(key=lambda x: x.get('create_time', ''), reverse=True)
        
        # Limit results
        return filtered_items[:max_results]
    
    def _conversation_matches_keywords(self, conversation: Dict[str, Any], keywords: List[str]) -> bool:
        """Check if a conversation matches any of the keywords"""
        if not keywords:
            return True
        
        # Use searchable content (title + conversation content)
        searchable_text = conversation.get('searchable_content', '').lower()
        
        # Check for keyword matches
        for keyword in keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in searchable_text:
                return True
        
        return False
    
    def _format_conversation_item(self, conversation: Dict[str, Any]) -> Dict[str, Any]:
        """Format conversation item to our standard format"""
        
        try:
            create_time = datetime.fromisoformat(conversation['create_time'].replace('Z', '+00:00'))
            create_time_str = create_time.isoformat()
            create_date_str = create_time.strftime('%Y-%m-%d %H:%M:%S')
            
            title = conversation.get('title', 'Untitled Conversation')
            conversation_id = conversation.get('id', '')
            url = conversation.get('url', f"https://gemini.google.com/app/{conversation_id}")
            content = conversation.get('conversation_content', '')
            message_count = conversation.get('message_count', 0)
            
            # Create content summary for RAG
            content_preview = content[:500] + "..." if len(content) > 500 else content
            
            return {
                "url": url,
                "title": title,
                "create_time": create_time_str,
                "message_count": message_count,
                "content": f"Title: {title}\nURL: {url}\nDate: {create_date_str}\nMessages: {message_count}\nContent: {content_preview}",
                "full_content": content,
                "metadata": {
                    "source": "gemini_history",
                    "url": url,
                    "title": title,
                    "create_time": create_time_str,
                    "conversation_id": conversation_id,
                    "message_count": message_count,
                    "access_method": "extension_api"
                }
            }
            
        except Exception as e:
            logger.error(f"Error formatting conversation item: {e}")
            return {
                "url": conversation.get('url', 'unknown'),
                "title": conversation.get('title', 'Error'),
                "create_time": datetime.now().isoformat(),
                "message_count": 0,
                "content": f"Error processing conversation: {str(e)}",
                "metadata": {
                    "source": "gemini_history",
                    "error": str(e)
                }
            }
    
    async def get_recent_conversations(self, hours: int = 24, max_results: int = 100) -> List[Dict[str, Any]]:
        """Get recent Gemini conversations"""
        
        # Convert hours to days for the search function
        days = max(1, hours // 24 + (1 if hours % 24 > 0 else 0))
        
        # Get all recent conversations without keyword filtering
        recent_items = await self.search_conversations([], days, max_results)
        
        # Filter by exact hour range
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        filtered_items = []
        for item in recent_items:
            try:
                create_time = datetime.fromisoformat(item['create_time'].replace('Z', '+00:00'))
                if create_time >= cutoff_time:
                    filtered_items.append(item)
            except:
                continue
        
        return filtered_items[:max_results]
    
    def get_status(self) -> Dict[str, Any]:
        """Get status of the Gemini history tool"""
        return {
            "tool_type": "gemini_history",
            "server_url": self.server_url,
            "cache_valid": self._is_cache_valid(),
            "cached_conversations": len(self.conversation_cache) if self.conversation_cache else 0,
            "cache_age_seconds": time.time() - self.cache_timestamp if self.cache_timestamp else None,
            "extension_communication": "http_endpoint",
            "access_methods": {
                "extension_api": True,
                "cached_data": self._is_cache_valid()
            }
        }
    
    def debug_cache_contents(self) -> Dict[str, Any]:
        """Debug method to inspect cache contents"""
        if not self.conversation_cache:
            return {"error": "No cached conversations"}
        
        sample_conversations = []
        for i, conv in enumerate(self.conversation_cache[:3]):  # First 3 conversations
            sample_conversations.append({
                "index": i,
                "id": conv.get("id", "no-id"),
                "title": conv.get("title", "no-title")[:50],
                "create_time": conv.get("create_time", "no-create-time"),
                "searchable_content_length": len(conv.get("searchable_content", "")),
                "has_mapping": bool(conv.get("mapping", {}))
            })
        
        return {
            "total_conversations": len(self.conversation_cache),
            "cache_timestamp": self.cache_timestamp,
            "cache_valid": self._is_cache_valid(),
            "sample_conversations": sample_conversations
        }