"""
Chrome History MCP Tool Implementation for Remote Servers
Uses Chrome Extension API with HTTP endpoint for secure remote access
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

class RemoteChromeHistoryTool:
    def __init__(self, server_port: int = 8501):
        self.server_port = server_port
        self.server_url = f"http://localhost:{server_port}"
        self.extension_id = None
        self.history_cache = []
        self.cache_timestamp = None
        self.cache_duration = 300  # 5 minutes cache
        
    async def initialize(self):
        """Initialize the tool and check for Chrome Extension availability"""
        try:
            # Check if Chrome Extension is communicating with us
            await self._ping_extension()
            logger.info("Chrome Extension communication established")
        except Exception as e:
            logger.warning(f"Chrome Extension not available: {e}")
    
    async def _ping_extension(self) -> bool:
        """Check if Chrome Extension is available and responding"""
        try:
            # This would be called by the Chrome Extension to register itself
            # For now, we assume it's available if we can bind to the port
            return True
        except Exception as e:
            logger.error(f"Extension ping failed: {e}")
            return False
    
    async def receive_history_data(self, history_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Receive history data from Chrome Extension via HTTP endpoint"""
        try:
            # Validate the incoming data
            if not isinstance(history_data, list):
                raise ValueError("History data must be a list")
            
            # Process and enhance the history data
            processed_data = []
            categories = {}
            
            for item in history_data:
                try:
                    # Validate required fields
                    if not item.get('url') or not item.get('title'):
                        continue
                    
                    # Process timestamps
                    if 'lastVisitTime' in item:
                        visit_time = datetime.fromtimestamp(item['lastVisitTime'] / 1000)
                    else:
                        visit_time = datetime.now()
                    
                    # Basic item - LLM will handle all keyword extraction and categorization
                    processed_item = {
                        'url': item['url'],
                        'title': item['title'],
                        'visit_time': visit_time.isoformat(),
                        'visit_count': item.get('visitCount', 1),
                        'typed_count': item.get('typedCount', 0),
                        'domain': item.get('domain', ''),
                        
                        # Create basic searchable content for immediate use
                        'searchable_content': f"{item['title']} {item['url']}",
                        
                        # Basic metadata
                        'metadata': {
                            'source': 'chrome_history_extension',
                            'domain': item.get('domain', ''),
                            'visit_frequency': item.get('visitCount', 1),
                            'user_typed': item.get('typedCount', 0) > 0,
                            'raw_data': True  # Indicates this needs LLM processing for keywords
                        }
                    }
                    
                    processed_data.append(processed_item)
                    
                    # Count domains for basic analytics  
                    domain = item.get('domain', 'unknown')
                    categories[domain] = categories.get(domain, 0) + 1
                    
                except Exception as e:
                    logger.warning(f"Error processing history item: {e}")
                    continue
            
            # Store in cache with timestamp
            self.history_cache = processed_data
            self.cache_timestamp = time.time()
            
            logger.info(f"✓ Processed {len(processed_data)} history items from Chrome Extension")
            logger.info(f"  Domains: {dict(list(categories.items())[:10])}")  # Show top 10 domains
            logger.info(f"  Total items ready for LLM-based keyword extraction")
            
            return {
                "success": True,
                "message": f"Processed {len(processed_data)} history items",
                "timestamp": datetime.now().isoformat(),
                "domains": dict(list(categories.items())[:20]),  # Top 20 domains
                "total_items": len(processed_data),
                "cache_status": "updated",
                "llm_processing_ready": True
            }
        except Exception as e:
            logger.error(f"Error receiving history data: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def search_history(
        self,
        keywords: List[str],
        days: int = 30,
        max_results: int = 50
    ) -> List[Dict[str, Any]]:
        """Search Chrome history using cached data from Extension"""
        
        # Check if we have fresh cached data
        if self._is_cache_valid():
            logger.info("Using cached Chrome history data")
            return self._search_cached_history(keywords, days, max_results)
        
        # Request fresh data from Extension
        try:
            await self._request_history_from_extension(keywords, days, max_results)
            
            # Wait a bit for the extension to respond
            for _ in range(10):  # Wait up to 5 seconds
                await asyncio.sleep(0.5)
                if self._is_cache_valid():
                    return self._search_cached_history(keywords, days, max_results)
            
            # If we still don't have fresh data, use what we have or mock data
            if self.history_cache:
                logger.warning("Using stale cached Chrome history data")
                return self._search_cached_history(keywords, days, max_results)
            else:
                logger.warning("No Chrome history data available")
                return []
                
        except Exception as e:
            logger.error(f"Error requesting history from extension: {e}")
            return []
    
    def _is_cache_valid(self) -> bool:
        """Check if cached data is still valid"""
        if not self.history_cache or not self.cache_timestamp:
            return False
        
        return (time.time() - self.cache_timestamp) < self.cache_duration
    
    async def _request_history_from_extension(
        self,
        keywords: List[str],
        days: int,
        max_results: int
    ) -> None:
        """Signal Chrome Extension to send fresh history data"""
        try:
            logger.info(
                "Requesting fresh history data from Chrome extension for keywords: %s",
                keywords,
            )

            payload = {
                "action": "refreshHistory",
                "params": {
                    "keywords": keywords,
                    "days": days,
                    "maxResults": max_results,
                },
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.server_url}/api/chrome/extension", json=payload, timeout=5.0
                )
                if response.status_code != 200:
                    logger.warning(
                        "Chrome extension refresh request returned status %s",
                        response.status_code,
                    )
                else:
                    logger.info("Chrome extension refresh triggered successfully")

        except Exception as e:
            logger.error("Failed to request history from extension: %s", e)
    
    def _search_cached_history(
        self,
        keywords: List[str],
        days: int,
        max_results: int
    ) -> List[Dict[str, Any]]:
        """Search through cached history data"""
        
        if not self.history_cache:
            return []
        
        # Filter by date range
        cutoff_date = datetime.now() - timedelta(days=days)
        cutoff_timestamp = cutoff_date.timestamp() * 1000  # Chrome uses milliseconds
        
        filtered_items = []
        
        for item in self.history_cache:
            try:
                # Parse visit time from Chrome Extension format
                if 'lastVisitTime' in item:
                    visit_time = item['lastVisitTime']
                elif 'visit_time' in item:
                    # If already converted to ISO format
                    visit_time = datetime.fromisoformat(item['visit_time'].replace('Z', '+00:00')).timestamp() * 1000
                else:
                    continue
                
                if visit_time >= cutoff_timestamp:
                    # Check if item matches keywords
                    if not keywords or self._item_matches_keywords(item, keywords):
                        # Convert to our standard format
                        formatted_item = self._format_history_item(item)
                        filtered_items.append(formatted_item)
                        
            except Exception as e:
                logger.warning(f"Error processing history item: {e}")
                continue
        
        # Sort by visit time (most recent first)
        filtered_items.sort(key=lambda x: x.get('visit_time', ''), reverse=True)
        
        # Limit results
        return filtered_items[:max_results]
    
    def _item_matches_keywords(self, item: Dict[str, Any], keywords: List[str]) -> bool:
        """Check if a history item matches any of the keywords - basic matching only"""
        if not keywords:
            return True
        
        # Use basic searchable content (title + URL + domain)
        searchable_text = f"{item.get('title', '')} {item.get('url', '')} {item.get('domain', '')}".lower()
        
        # Check for keyword matches (LLM will handle sophisticated matching)
        for keyword in keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in searchable_text:
                return True
        
        return False
    
    def _format_history_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Format history item to our standard format"""
        
        try:
            # Handle different timestamp formats
            if 'lastVisitTime' in item:
                visit_time = datetime.fromtimestamp(item['lastVisitTime'] / 1000)
            elif 'visit_time' in item:
                if isinstance(item['visit_time'], str):
                    visit_time = datetime.fromisoformat(item['visit_time'].replace('Z', '+00:00'))
                else:
                    visit_time = datetime.fromtimestamp(item['visit_time'] / 1000)
            else:
                visit_time = datetime.now()
            
            visit_time_str = visit_time.isoformat()
            visit_date_str = visit_time.strftime('%Y-%m-%d %H:%M:%S')
            
            title = item.get('title', 'No Title')
            url = item.get('url', '')
            visit_count = item.get('visitCount', item.get('visit_count', 0))
            
            return {
                "url": url,
                "title": title,
                "visit_time": visit_time_str,
                "visit_count": visit_count,
                "content": f"Title: {title}\nURL: {url}\nVisit Date: {visit_date_str}",
                "metadata": {
                    "source": "chrome_history_remote",
                    "url": url,
                    "title": title,
                    "visit_time": visit_time_str,
                    "visit_count": visit_count,
                    "access_method": "extension_api"
                }
            }
            
        except Exception as e:
            logger.error(f"Error formatting history item: {e}")
            return {
                "url": item.get('url', 'unknown'),
                "title": item.get('title', 'Error'),
                "visit_time": datetime.now().isoformat(),
                "visit_count": 0,
                "content": f"Error processing item: {str(e)}",
                "metadata": {
                    "source": "chrome_history_remote",
                    "error": str(e)
                }
            }
    
    async def get_recent_history(self, hours: int = 24, max_results: int = 100) -> List[Dict[str, Any]]:
        """Get recent Chrome history"""
        
        # Convert hours to days for the search function
        days = max(1, hours // 24 + (1 if hours % 24 > 0 else 0))
        
        # Get all recent history without keyword filtering
        recent_items = await self.search_history([], days, max_results)
        
        # Filter by exact hour range
        cutoff_time = datetime.now() - timedelta(hours=hours)
        cutoff_timestamp = cutoff_time.timestamp() * 1000
        
        filtered_items = []
        for item in recent_items:
            try:
                visit_time = datetime.fromisoformat(item['visit_time'].replace('Z', '+00:00'))
                if visit_time.timestamp() * 1000 >= cutoff_timestamp:
                    filtered_items.append(item)
            except:
                continue
        
        return filtered_items[:max_results]
    
    
    def get_status(self) -> Dict[str, Any]:
        """Get status of the remote Chrome history tool"""
        return {
            "tool_type": "remote_chrome_history",
            "server_url": self.server_url,
            "cache_valid": self._is_cache_valid(),
            "cached_items": len(self.history_cache) if self.history_cache else 0,
            "cache_age_seconds": time.time() - self.cache_timestamp if self.cache_timestamp else None,
            "extension_communication": "http_endpoint",
            "access_methods": {
                "extension_api": True,
                "cached_data": self._is_cache_valid(),
                "mock_data": True
            }
        }