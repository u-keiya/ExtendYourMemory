"""
Web Fetch Tool for MCP Server using LangChain WebBaseLoader
Fetches and processes web pages for RAG integration with advanced features
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
from urllib.parse import urlparse
import time

# LangChain imports
from langchain_community.document_loaders import WebBaseLoader, AsyncChromiumLoader
from langchain_community.document_transformers import Html2TextTransformer
from langchain.schema import Document

logger = logging.getLogger(__name__)

class WebFetchTool:
    def __init__(self):
        self.cache = {}
        self.cache_timeout = 1800  # 30 minutes
        self.html2text = Html2TextTransformer()
        
    def _is_valid_url(self, url: str) -> bool:
        """Validate URL format and safety"""
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return False
            
            # Only allow HTTP/HTTPS
            if parsed.scheme.lower() not in ['http', 'https']:
                return False
                
            # Block local/private IPs
            blocked_domains = ['localhost', '127.0.0.1', '0.0.0.0', '::1']
            if any(domain in parsed.netloc.lower() for domain in blocked_domains):
                return False
                
            return True
        except Exception:
            return False
    
    def _document_to_dict(self, doc: Document, url: str) -> Dict[str, Any]:
        """Convert LangChain Document to dict format"""
        return {
            'url': url,
            'title': doc.metadata.get('title', ''),
            'content': doc.page_content,
            'metadata': {
                **doc.metadata,
                'url': url,
                'source': 'web_fetch_langchain',
                'fetch_time': datetime.now().isoformat()
            },
            'fetch_time': datetime.now().isoformat(),
            'content_length': len(doc.page_content)
        }
    
    async def fetch_url(self, url: str, use_chromium: bool = False) -> Optional[Dict[str, Any]]:
        """Fetch a single URL and return processed content using LangChain WebBaseLoader"""
        
        if not self._is_valid_url(url):
            logger.error(f"Invalid URL: {url}")
            return None
            
        # Check cache
        cache_key = f"{url}_{'chromium' if use_chromium else 'basic'}"
        if cache_key in self.cache:
            cached_time, cached_data = self.cache[cache_key]
            if time.time() - cached_time < self.cache_timeout:
                logger.info(f"Using cached data for: {url}")
                return cached_data
        
        try:
            if use_chromium:
                # Use AsyncChromiumLoader for JavaScript-heavy sites
                loader = AsyncChromiumLoader([url])
                docs = await loader.aload()
                
                # Transform HTML to text
                docs = self.html2text.transform_documents(docs)
            else:
                # Use WebBaseLoader for standard sites
                loader = WebBaseLoader([url])
                docs = await asyncio.to_thread(loader.load)
            
            if not docs:
                logger.error(f"No content loaded from {url}")
                return None
                
            doc = docs[0]
            result = self._document_to_dict(doc, url)
            
            # Cache result
            self.cache[cache_key] = (time.time(), result)
            
            logger.info(f"Successfully fetched {url}: {len(result['content'])} chars")
            return result
                
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    async def fetch_multiple_urls(self, urls: List[str], max_concurrent: int = 5, use_chromium: bool = False) -> List[Dict[str, Any]]:
        """Fetch multiple URLs concurrently using LangChain loaders"""
        
        valid_urls = [url for url in urls if self._is_valid_url(url)]
        
        if not valid_urls:
            logger.warning("No valid URLs to fetch")
            return []
        
        logger.info(f"Fetching {len(valid_urls)} URLs with max_concurrent={max_concurrent}")
        
        try:
            if use_chromium:
                # Use AsyncChromiumLoader for JavaScript-heavy sites
                loader = AsyncChromiumLoader(valid_urls)
                docs = await loader.aload()
                
                # Transform HTML to text
                docs = self.html2text.transform_documents(docs)
            else:
                # Use WebBaseLoader for standard sites
                # For multiple URLs, we need to handle them individually to maintain error handling
                semaphore = asyncio.Semaphore(max_concurrent)
                
                async def fetch_with_semaphore(url):
                    async with semaphore:
                        return await self.fetch_url(url, use_chromium=False)
                
                tasks = [fetch_with_semaphore(url) for url in valid_urls]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Filter successful results
                successful_results = []
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        logger.error(f"Exception fetching {valid_urls[i]}: {result}")
                    elif result is not None:
                        successful_results.append(result)
                
                logger.info(f"Successfully fetched {len(successful_results)}/{len(valid_urls)} URLs")
                return successful_results
            
            # Process docs for chromium mode
            results = []
            for i, doc in enumerate(docs):
                if i < len(valid_urls):
                    result = self._document_to_dict(doc, valid_urls[i])
                    results.append(result)
            
            logger.info(f"Successfully fetched {len(results)}/{len(valid_urls)} URLs with chromium")
            return results
            
        except Exception as e:
            logger.error(f"Error in batch fetch: {e}")
            return []
    
    async def search_web_content(self, keywords: List[str], max_results: int = 10) -> List[Dict[str, Any]]:
        """Search web content using Chrome history URLs that match keywords"""
        
        # This is a placeholder - in a real implementation, you might:
        # 1. Use a search engine API (Google Custom Search, Bing, etc.)
        # 2. Use the Chrome history URLs that match keywords
        # 3. Use bookmarks or saved URLs
        
        logger.info(f"Web content search not implemented - would search for: {keywords}")
        return []
    
    async def extract_links_from_page(self, url: str, same_domain_only: bool = True) -> List[str]:
        """Extract links from a webpage using LangChain WebBaseLoader"""
        
        try:
            from urllib.parse import urljoin
            from bs4 import BeautifulSoup
            
            # Fetch the page using LangChain
            loader = WebBaseLoader([url])
            docs = await asyncio.to_thread(loader.load)
            
            if not docs:
                return []
            
            # Get HTML content from the loader's web_path attribute or re-fetch
            loader_single = WebBaseLoader(url)
            html_content = await asyncio.to_thread(lambda: loader_single.scrape())
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            links = []
            base_domain = urlparse(url).netloc
            
            for link in soup.find_all('a', href=True):
                href = link['href']
                
                # Convert relative URLs to absolute
                absolute_url = urljoin(url, href)
                
                # Filter by domain if requested
                if same_domain_only:
                    link_domain = urlparse(absolute_url).netloc
                    if link_domain != base_domain:
                        continue
                
                if self._is_valid_url(absolute_url):
                    links.append(absolute_url)
            
            return list(set(links))  # Remove duplicates
                
        except Exception as e:
            logger.error(f"Error extracting links from {url}: {e}")
            return []
    
    async def get_page_summary(self, url: str, max_length: int = 500) -> str:
        """Get a summary of a webpage"""
        
        result = await self.fetch_url(url)
        if not result:
            return ""
        
        content = result['content']
        
        # Simple summarization - take first meaningful paragraphs
        sentences = content.split('.')
        summary_sentences = []
        total_length = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 20:  # Skip very short sentences
                continue
                
            if total_length + len(sentence) > max_length:
                break
                
            summary_sentences.append(sentence)
            total_length += len(sentence)
        
        return '. '.join(summary_sentences) + '.' if summary_sentences else content[:max_length]
    
    async def fetch_with_javascript(self, url: str) -> Optional[Dict[str, Any]]:
        """Fetch URL with JavaScript support using AsyncChromiumLoader"""
        return await self.fetch_url(url, use_chromium=True)
    
    async def cleanup(self):
        """Clean up resources - LangChain handles its own cleanup"""
        # Clear cache if needed
        self.cache.clear()
        logger.info("WebFetchTool cleanup completed")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        current_time = time.time()
        valid_cache_items = 0
        
        for cached_time, _ in self.cache.values():
            if current_time - cached_time < self.cache_timeout:
                valid_cache_items += 1
        
        return {
            'total_cached_items': len(self.cache),
            'valid_cached_items': valid_cache_items,
            'cache_timeout_minutes': self.cache_timeout / 60,
            'loader_type': 'LangChain WebBaseLoader + AsyncChromiumLoader'
        }