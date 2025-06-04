"""
Chrome History MCP Tool Implementation (Version 2)
Uses Chrome Extension API for secure and proper history access, with SQLite fallback
"""

import os
import sqlite3
import asyncio
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging
import platform
import shutil
import json

logger = logging.getLogger(__name__)

class ChromeHistoryTool:
    def __init__(self):
        self.extension_available = False
        self.chrome_history_path = self._get_chrome_history_path()
        self.fallback_enabled = True
        
    async def check_extension_availability(self) -> bool:
        """Chrome拡張機能の利用可能性をチェック"""
        try:
            # 実際の実装では、拡張機能のメッセージAPIを使用
            # 現在は開発時のためフォールバックを使用
            logger.info("Checking Chrome Extension availability...")
            self.extension_available = False  # 開発時はfalseに設定
            return self.extension_available
        except Exception as e:
            logger.warning(f"Chrome extension not available: {e}")
            self.extension_available = False
            return False
    
    def _get_chrome_history_path(self) -> Optional[str]:
        """プラットフォーム別のChrome履歴ファイルパスを取得（フォールバック用）"""
        system = platform.system()
        
        if system == "Windows":
            username = os.getenv('USERNAME')
            paths = [
                f"C:\\Users\\{username}\\AppData\\Local\\Google\\Chrome\\User Data\\Default\\History",
                f"C:\\Users\\{username}\\AppData\\Local\\Google\\Chrome\\User Data\\Profile 1\\History"
            ]
        elif system == "Darwin":
            username = os.getenv('USER')
            paths = [
                f"/Users/{username}/Library/Application Support/Google/Chrome/Default/History",
                f"/Users/{username}/Library/Application Support/Google/Chrome/Profile 1/History"
            ]
        elif system == "Linux":
            username = os.getenv('USER')
            paths = [
                f"/home/{username}/.config/google-chrome/Default/History",
                f"/home/{username}/.config/google-chrome/Profile 1/History",
                f"/home/{username}/.config/chromium/Default/History"
            ]
        else:
            logger.warning(f"Unsupported platform: {system}")
            return None
        
        for path in paths:
            if os.path.exists(path):
                logger.info(f"Found Chrome history at: {path}")
                return path
        
        logger.warning("Chrome history file not found")
        return None
    
    async def search_history(
        self,
        keywords: List[str],
        days: int = 30,
        max_results: int = 50
    ) -> List[Dict[str, Any]]:
        """Chrome履歴からキーワードに基づいて検索"""
        
        # Chrome Extension APIを優先使用
        if await self.check_extension_availability():
            return await self._search_with_extension(keywords, days, max_results)
        
        # フォールバック: 直接SQLiteアクセス
        elif self.fallback_enabled and self.chrome_history_path:
            logger.info("Using SQLite fallback for Chrome history access")
            return await self._search_with_sqlite(keywords, days, max_results)
        
        # 最終フォールバック: モックデータ
        else:
            logger.info("Using mock Chrome history data")
            return await self._mock_search_results(keywords)
    
    async def _search_with_extension(
        self,
        keywords: List[str],
        days: int,
        max_results: int
    ) -> List[Dict[str, Any]]:
        """Chrome Extension APIを使用した検索"""
        
        try:
            # この実装は実際の拡張機能統合時に完成
            # 現在はプレースホルダー
            logger.info("Searching history via Chrome Extension API")
            
            # 拡張機能との通信プロトコル例:
            # 1. メッセージをChrome Extension に送信
            # 2. Extension がchrome.history.search() を実行
            # 3. 結果をメッセージで受信
            
            # 現在はフォールバックに移行
            return await self._search_with_sqlite(keywords, days, max_results)
            
        except Exception as e:
            logger.error(f"Chrome Extension API error: {e}")
            return await self._search_with_sqlite(keywords, days, max_results)
    
    async def _search_with_sqlite(
        self,
        keywords: List[str],
        days: int,
        max_results: int
    ) -> List[Dict[str, Any]]:
        """SQLiteファイル直接アクセス（フォールバック）"""
        
        if not self.chrome_history_path:
            return await self._mock_search_results(keywords)
        
        temp_history_path = None
        try:
            temp_history_path = f"/tmp/chrome_history_copy_{datetime.now().timestamp()}.db"
            shutil.copy2(self.chrome_history_path, temp_history_path)
            
            return await self._search_history_db(temp_history_path, keywords, days, max_results)
            
        except Exception as e:
            logger.error(f"Error accessing Chrome history via SQLite: {e}")
            return await self._mock_search_results(keywords)
        
        finally:
            if temp_history_path and os.path.exists(temp_history_path):
                try:
                    os.remove(temp_history_path)
                except Exception as e:
                    logger.warning(f"Failed to remove temp history file: {e}")
    
    async def _search_history_db(
        self,
        db_path: str,
        keywords: List[str],
        days: int,
        max_results: int
    ) -> List[Dict[str, Any]]:
        """SQLiteデータベースから履歴を検索"""
        
        history_items = []
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            start_time = datetime.now() - timedelta(days=days)
            start_timestamp = int(start_time.timestamp() * 1000000)
            
            # キーワード条件構築
            keyword_conditions = []
            params = []
            
            for keyword in keywords:
                keyword_conditions.append("(urls.title LIKE ? OR urls.url LIKE ?)")
                params.extend([f"%{keyword}%", f"%{keyword}%"])
            
            keyword_clause = " OR ".join(keyword_conditions) if keyword_conditions else "1=1"
            
            query = f"""
            SELECT 
                urls.url,
                urls.title,
                urls.visit_count,
                visits.visit_time,
                urls.last_visit_time
            FROM urls
            LEFT JOIN visits ON urls.id = visits.url
            WHERE visits.visit_time > ? 
            AND ({keyword_clause})
            ORDER BY visits.visit_time DESC
            LIMIT ?
            """
            
            params = [start_timestamp] + params + [max_results]
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            for row in rows:
                url, title, visit_count, visit_time, last_visit_time = row
                
                if visit_time:
                    visit_datetime = datetime.fromtimestamp(visit_time / 1000000)
                else:
                    visit_datetime = datetime.fromtimestamp(last_visit_time / 1000000) if last_visit_time else datetime.now()
                
                history_items.append({
                    "url": url,
                    "title": title or "No Title",
                    "visit_time": visit_datetime.isoformat(),
                    "visit_count": visit_count or 0,
                    "content": f"Title: {title}\nURL: {url}\nVisit Date: {visit_datetime.strftime('%Y-%m-%d %H:%M:%S')}",
                    "metadata": {
                        "source": "chrome_history_sqlite",
                        "url": url,
                        "title": title,
                        "visit_time": visit_datetime.isoformat(),
                        "visit_count": visit_count,
                        "access_method": "sqlite_fallback"
                    }
                })
            
            conn.close()
            
            logger.info(f"Found {len(history_items)} Chrome history items via SQLite")
            return history_items
            
        except sqlite3.Error as e:
            logger.error(f"SQLite error: {e}")
            return await self._mock_search_results(keywords)
        except Exception as e:
            logger.error(f"Unexpected error searching Chrome history: {e}")
            return await self._mock_search_results(keywords)
    
    async def get_recent_history(self, hours: int = 24, max_results: int = 100) -> List[Dict[str, Any]]:
        """最近の履歴を取得"""
        
        # Extension API を優先使用
        if await self.check_extension_availability():
            return await self._get_recent_with_extension(hours, max_results)
        
        # フォールバック: SQLiteアクセス
        elif self.fallback_enabled and self.chrome_history_path:
            return await self._get_recent_with_sqlite(hours, max_results)
        
        # モックデータ
        else:
            return []
    
    async def _get_recent_with_extension(self, hours: int, max_results: int) -> List[Dict[str, Any]]:
        """Chrome Extension API で最近の履歴を取得"""
        
        try:
            # 実際の拡張機能実装時に完成
            logger.info("Getting recent history via Chrome Extension API")
            return await self._get_recent_with_sqlite(hours, max_results)
            
        except Exception as e:
            logger.error(f"Extension API error: {e}")
            return await self._get_recent_with_sqlite(hours, max_results)
    
    async def _get_recent_with_sqlite(self, hours: int, max_results: int) -> List[Dict[str, Any]]:
        """SQLite で最近の履歴を取得"""
        
        if not self.chrome_history_path:
            return []
        
        temp_history_path = None
        try:
            temp_history_path = f"/tmp/chrome_recent_history_{datetime.now().timestamp()}.db"
            shutil.copy2(self.chrome_history_path, temp_history_path)
            
            conn = sqlite3.connect(temp_history_path)
            cursor = conn.cursor()
            
            start_time = datetime.now() - timedelta(hours=hours)
            start_timestamp = int(start_time.timestamp() * 1000000)
            
            query = """
            SELECT 
                urls.url,
                urls.title,
                urls.visit_count,
                visits.visit_time
            FROM urls
            LEFT JOIN visits ON urls.id = visits.url
            WHERE visits.visit_time > ?
            ORDER BY visits.visit_time DESC
            LIMIT ?
            """
            
            cursor.execute(query, [start_timestamp, max_results])
            rows = cursor.fetchall()
            
            recent_items = []
            for row in rows:
                url, title, visit_count, visit_time = row
                visit_datetime = datetime.fromtimestamp(visit_time / 1000000)
                
                recent_items.append({
                    "url": url,
                    "title": title or "No Title",
                    "visit_time": visit_datetime.isoformat(),
                    "visit_count": visit_count or 0,
                    "access_method": "sqlite_fallback"
                })
            
            conn.close()
            return recent_items
            
        except Exception as e:
            logger.error(f"Error getting recent history: {e}")
            return []
        
        finally:
            if temp_history_path and os.path.exists(temp_history_path):
                try:
                    os.remove(temp_history_path)
                except Exception:
                    pass
    
    async def _mock_search_results(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """モック検索結果（履歴アクセスできない場合）"""
        logger.info("Using mock Chrome history search results")
        
        mock_items = []
        base_urls = [
            "https://stackoverflow.com",
            "https://github.com",
            "https://docs.python.org",
            "https://developer.mozilla.org",
            "https://www.google.com"
        ]
        
        for i, keyword in enumerate(keywords[:3]):
            for j, base_url in enumerate(base_urls[:2]):
                visit_time = datetime.now() - timedelta(days=j+1, hours=i*2)
                
                mock_items.append({
                    "url": f"{base_url}/search?q={keyword}",
                    "title": f"Search results for {keyword} - Mock Site",
                    "visit_time": visit_time.isoformat(),
                    "visit_count": 3 + j,
                    "content": f"""Title: Search results for {keyword} - Mock Site
URL: {base_url}/search?q={keyword}
Visit Date: {visit_time.strftime('%Y-%m-%d %H:%M:%S')}

This is a mock Chrome history entry that would normally contain real browsing history related to {keyword}.""",
                    "metadata": {
                        "source": "chrome_history_mock",
                        "url": f"{base_url}/search?q={keyword}",
                        "title": f"Search results for {keyword} - Mock Site",
                        "visit_time": visit_time.isoformat(),
                        "visit_count": 3 + j,
                        "access_method": "mock"
                    }
                })
        
        return mock_items
    
    def get_status(self) -> Dict[str, Any]:
        """Chrome履歴ツールの状態を取得"""
        return {
            "extension_available": self.extension_available,
            "sqlite_fallback_available": bool(self.chrome_history_path),
            "chrome_history_path": self.chrome_history_path,
            "fallback_enabled": self.fallback_enabled,
            "access_methods": {
                "extension_api": self.extension_available,
                "sqlite_direct": bool(self.chrome_history_path),
                "mock_data": True
            }
        }