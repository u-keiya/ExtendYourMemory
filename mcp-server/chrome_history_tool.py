"""
Chrome History MCP Tool Implementation
"""

import os
import sqlite3
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging
import platform
import shutil

logger = logging.getLogger(__name__)

class ChromeHistoryTool:
    def __init__(self):
        self.chrome_history_path = self._get_chrome_history_path()
    
    def _get_chrome_history_path(self) -> Optional[str]:
        """プラットフォーム別のChrome履歴ファイルパスを取得"""
        system = platform.system()
        
        if system == "Windows":
            # Windows
            username = os.getenv('USERNAME')
            paths = [
                f"C:\\Users\\{username}\\AppData\\Local\\Google\\Chrome\\User Data\\Default\\History",
                f"C:\\Users\\{username}\\AppData\\Local\\Google\\Chrome\\User Data\\Profile 1\\History"
            ]
        elif system == "Darwin":
            # macOS
            username = os.getenv('USER')
            paths = [
                f"/Users/{username}/Library/Application Support/Google/Chrome/Default/History",
                f"/Users/{username}/Library/Application Support/Google/Chrome/Profile 1/History"
            ]
        elif system == "Linux":
            # Linux
            username = os.getenv('USER')
            paths = [
                f"/home/{username}/.config/google-chrome/Default/History",
                f"/home/{username}/.config/google-chrome/Profile 1/History",
                f"/home/{username}/.config/chromium/Default/History"
            ]
        else:
            logger.warning(f"Unsupported platform: {system}")
            return None
        
        # 存在するパスを探す
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
        
        if not self.chrome_history_path:
            return await self._mock_search_results(keywords)
        
        # Chrome が履歴ファイルをロックしている可能性があるため、コピーを作成
        temp_history_path = None
        try:
            temp_history_path = f"/tmp/chrome_history_copy_{datetime.now().timestamp()}.db"
            shutil.copy2(self.chrome_history_path, temp_history_path)
            
            return await self._search_history_db(temp_history_path, keywords, days, max_results)
            
        except Exception as e:
            logger.error(f"Error accessing Chrome history: {e}")
            return await self._mock_search_results(keywords)
        
        finally:
            # 一時ファイルのクリーンアップ
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
            # SQLite接続
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 検索開始日時（UNIX時間マイクロ秒）
            start_time = datetime.now() - timedelta(days=days)
            start_timestamp = int(start_time.timestamp() * 1000000)
            
            # キーワード条件構築
            keyword_conditions = []
            params = []
            
            for keyword in keywords:
                keyword_conditions.append("(urls.title LIKE ? OR urls.url LIKE ?)")
                params.extend([f"%{keyword}%", f"%{keyword}%"])
            
            keyword_clause = " OR ".join(keyword_conditions) if keyword_conditions else "1=1"
            
            # SQLクエリ
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
                
                # UNIX時間マイクロ秒を datetime に変換
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
                        "source": "chrome_history",
                        "url": url,
                        "title": title,
                        "visit_time": visit_datetime.isoformat(),
                        "visit_count": visit_count
                    }
                })
            
            conn.close()
            
            logger.info(f"Found {len(history_items)} Chrome history items matching keywords: {keywords}")
            return history_items
            
        except sqlite3.Error as e:
            logger.error(f"SQLite error: {e}")
            return await self._mock_search_results(keywords)
        except Exception as e:
            logger.error(f"Unexpected error searching Chrome history: {e}")
            return await self._mock_search_results(keywords)
    
    async def _mock_search_results(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """モック検索結果（履歴ファイルにアクセスできない場合）"""
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
            for j, base_url in enumerate(base_urls[:2]):  # 各キーワードに対して2つのモック結果
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
                        "visit_count": 3 + j
                    }
                })
        
        return mock_items
    
    async def get_recent_history(self, hours: int = 24, max_results: int = 100) -> List[Dict[str, Any]]:
        """最近の履歴を取得"""
        
        if not self.chrome_history_path:
            return []
        
        temp_history_path = None
        try:
            temp_history_path = f"/tmp/chrome_recent_history_{datetime.now().timestamp()}.db"
            shutil.copy2(self.chrome_history_path, temp_history_path)
            
            conn = sqlite3.connect(temp_history_path)
            cursor = conn.cursor()
            
            # 検索開始時刻
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
                    "visit_count": visit_count or 0
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