"""
Google Drive MCP Tool Implementation with LangChain Integration
"""

import os
import asyncio
from typing import List, Dict, Any, Optional
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import logging
import json

logger = logging.getLogger(__name__)

# LangChain Google Drive support
try:
    from langchain_google_community import GoogleDriveLoader
    LANGCHAIN_GOOGLE_AVAILABLE = True
    logger.info("LangChain Google Drive loader available")
except ImportError:
    LANGCHAIN_GOOGLE_AVAILABLE = False
    logger.warning("LangChain Google Drive loader not available")

class GoogleDriveTool:
    # ファイルタイプマッピング（クラス定数）
    MIME_TYPE_MAP = {
        'document': 'application/vnd.google-apps.document',
        'sheet': 'application/vnd.google-apps.spreadsheet',
        'pdf': 'application/pdf',
        'presentation': 'application/vnd.google-apps.presentation',
        # Markdown ファイルはGoogle Drive上では text/plain として扱われる場合
        # もあるため、複数の候補を保持しておく
        'markdown': ['text/markdown', 'text/plain', 'text/x-markdown'],
        'text': 'text/plain'
    }
    
    def __init__(self):
        self.service = None
        self.credentials = None
        self.oauth_flow = None
        self.scopes = [
            'https://www.googleapis.com/auth/drive.readonly',
            'https://www.googleapis.com/auth/drive.metadata.readonly'
        ]
        self._initialize_service()
    
    def _initialize_service(self):
        """Google Drive APIサービスを初期化"""
        try:
            # 1. 既存のOAuth2トークンをチェック
            if self._load_oauth_credentials():
                logger.info("Google Drive service initialized with OAuth2 credentials")
                return
            
            # 2. サービスアカウント認証を試行
            service_account_file = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE', './credentials/service-account-key.json')
            
            if os.path.exists(service_account_file):
                # サービスアカウント認証
                self.credentials = service_account.Credentials.from_service_account_file(
                    service_account_file, scopes=self.scopes
                )
                
                self.service = build('drive', 'v3', credentials=self.credentials)
                logger.info("Google Drive service initialized with service account")
                return
                
            # 3. OAuth2設定をチェック
            if self._setup_oauth_flow():
                logger.info("OAuth2 flow configured - authentication required")
            else:
                logger.warning("No Google Drive authentication method available")
                logger.info("Google Drive tool will use mock responses")
                
        except Exception as e:
            logger.error(f"Failed to initialize Google Drive service: {e}")
            logger.info("Google Drive tool will use mock responses")
    
    def _setup_oauth_flow(self) -> bool:
        """OAuth2フローを設定"""
        try:
            client_id = os.getenv('GOOGLE_OAUTH_CLIENT_ID')
            client_secret = os.getenv('GOOGLE_OAUTH_CLIENT_SECRET')
            redirect_uri = os.getenv('GOOGLE_OAUTH_REDIRECT_URI', 'http://localhost:8000/auth/google/callback')
            
            if not client_id or not client_secret:
                return False
            
            client_config = {
                "web": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://accounts.google.com/o/oauth2/token",
                    "redirect_uris": [redirect_uri]
                }
            }
            
            self.oauth_flow = Flow.from_client_config(
                client_config,
                scopes=self.scopes,
                redirect_uri=redirect_uri
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup OAuth2 flow: {e}")
            return False
    
    def _load_oauth_credentials(self) -> bool:
        """保存されたOAuth2認証情報を読み込み"""
        try:
            token_file = './credentials/google_oauth_token.json'
            
            if not os.path.exists(token_file):
                return False
            
            with open(token_file, 'r') as f:
                token_data = json.load(f)
            
            self.credentials = Credentials.from_authorized_user_info(token_data, self.scopes)
            
            # 認証情報が有効かチェック
            if not self.credentials.valid:
                if self.credentials.expired and self.credentials.refresh_token:
                    self.credentials.refresh(Request())
                    self._save_oauth_credentials()
                else:
                    return False
            
            self.service = build('drive', 'v3', credentials=self.credentials)
            return True
            
        except Exception as e:
            logger.error(f"Failed to load OAuth2 credentials: {e}")
            return False
    
    def _save_oauth_credentials(self):
        """OAuth2認証情報を保存"""
        try:
            os.makedirs('./credentials', exist_ok=True)
            token_file = './credentials/google_oauth_token.json'
            
            with open(token_file, 'w') as f:
                json.dump({
                    'token': self.credentials.token,
                    'refresh_token': self.credentials.refresh_token,
                    'token_uri': self.credentials.token_uri,
                    'client_id': self.credentials.client_id,
                    'client_secret': self.credentials.client_secret,
                    'scopes': self.credentials.scopes
                }, f)
            
            logger.info("OAuth2 credentials saved")
            
        except Exception as e:
            logger.error(f"Failed to save OAuth2 credentials: {e}")
    
    def get_authorization_url(self) -> Optional[str]:
        """OAuth2認証用のURLを取得"""
        if not self.oauth_flow:
            return None
        
        try:
            auth_url, _ = self.oauth_flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true'
            )
            return auth_url
            
        except Exception as e:
            logger.error(f"Failed to get authorization URL: {e}")
            return None
    
    def handle_oauth_callback(self, authorization_code: str) -> bool:
        """OAuth2コールバックを処理"""
        if not self.oauth_flow:
            return False
        
        try:
            self.oauth_flow.fetch_token(code=authorization_code)
            self.credentials = self.oauth_flow.credentials
            self.service = build('drive', 'v3', credentials=self.credentials)
            
            # 認証情報を保存
            self._save_oauth_credentials()
            
            logger.info("OAuth2 authentication successful")
            return True
            
        except Exception as e:
            logger.error(f"Failed to handle OAuth2 callback: {e}")
            return False
    
    def build_optimized_drive_query(self, hierarchical_keywords: Dict[str, List[str]], file_types: Optional[List[str]] = None) -> str:
        """階層的キーワードに基づく最適化されたGoogle Drive検索クエリ構築"""
        
        query_parts = []
        
        try:
            # 必須キーワード (AND検索) - フレーズマッチング対応
            primary_keywords = hierarchical_keywords.get('primary_keywords', [])
            if primary_keywords:
                primary_conditions = []
                for keyword in primary_keywords:
                    if ' ' in keyword and len(keyword.split()) <= 3:
                        # フレーズマッチング: スペースを含む2-3語
                        primary_conditions.append(f'fullText contains "{keyword}"')
                    else:
                        # 単語マッチング
                        primary_conditions.append(f'fullText contains \'{keyword}\'')
                
                if len(primary_conditions) == 1:
                    query_parts.append(primary_conditions[0])
                else:
                    query_parts.append(f"({' and '.join(primary_conditions)})")
            
            # 関連キーワード (OR検索)
            secondary_keywords = hierarchical_keywords.get('secondary_keywords', [])
            if secondary_keywords:
                secondary_conditions = []
                for keyword in secondary_keywords:
                    if ' ' in keyword and len(keyword.split()) <= 3:
                        secondary_conditions.append(f'fullText contains "{keyword}"')
                    else:
                        secondary_conditions.append(f'fullText contains \'{keyword}\'')
                
                if secondary_conditions:
                    query_parts.append(f"({' or '.join(secondary_conditions)})")
            
            # 文脈キーワード (OR検索、重み付け低)
            context_keywords = hierarchical_keywords.get('context_keywords', [])
            if context_keywords and len(query_parts) > 0:  # 他にキーワードがある場合のみ
                context_conditions = []
                for keyword in context_keywords:
                    if ' ' in keyword:
                        context_conditions.append(f'fullText contains "{keyword}"')
                    else:
                        context_conditions.append(f'fullText contains \'{keyword}\'')
                
                if context_conditions:
                    query_parts.append(f"({' or '.join(context_conditions)})")
            
            # 除外キーワード
            negative_keywords = hierarchical_keywords.get('negative_keywords', [])
            for neg_keyword in negative_keywords:
                if ' ' in neg_keyword:
                    query_parts.append(f'not fullText contains "{neg_keyword}"')
                else:
                    query_parts.append(f'not fullText contains \'{neg_keyword}\'')
            
            # ファイルタイプ制限
            if file_types:
                mime_conditions = []
                lower_types = [ft.lower() for ft in file_types]
                for file_type in lower_types:
                    if file_type in self.MIME_TYPE_MAP:
                        mime_value = self.MIME_TYPE_MAP[file_type]
                        if isinstance(mime_value, list):
                            mime_conditions.extend([f"mimeType='{v}'" for v in mime_value])
                        else:
                            mime_conditions.append(f"mimeType='{mime_value}'")

                if mime_conditions:
                    query_parts.append(f"({' or '.join(mime_conditions)})")

                # Markdown ファイルタイプでは拡張子フィルタも追加
                if 'markdown' in lower_types:
                    query_parts.append("name contains '.md'")
            
            # トラッシュを除外
            query_parts.append("trashed=false")
            
            final_query = " and ".join(query_parts)
            logger.info(f"Optimized Google Drive query: {final_query}")
            
            return final_query
            
        except Exception as e:
            logger.error(f"Error building optimized query: {e}")
            # フォールバック: シンプルなOR検索
            all_keywords = []
            for keyword_list in hierarchical_keywords.values():
                if isinstance(keyword_list, list):
                    all_keywords.extend(keyword_list)
            
            if all_keywords:
                simple_conditions = [f'fullText contains \'{kw}\'' for kw in all_keywords[:10]]
                return f"({' or '.join(simple_conditions)}) and trashed=false"
            else:
                return "trashed=false"

    async def search_files(
        self,
        keywords: List[str],
        file_types: Optional[List[str]] = None,
        folder_id: Optional[str] = "root",
        max_results: int = 50,
        excluded_folder_ids: Optional[List[str]] = None,
        hierarchical_keywords: Optional[Dict[str, List[str]]] = None
    ) -> List[Dict[str, Any]]:
        """Google Driveからファイルを検索"""
        
        if not self.service:
            logger.error("Google Drive service not available")
            return []
        
        try:
            # 階層的キーワードが提供されている場合は最適化クエリを使用
            if hierarchical_keywords:
                base_query = self.build_optimized_drive_query(hierarchical_keywords, file_types)
            else:
                # フォールバック: 従来のシンプルなクエリ構築
                query_parts = []
                
                # キーワード検索
                if keywords:
                    keyword_conditions = []
                    for keyword in keywords:
                        # フレーズ検出の改善
                        if ' ' in keyword and len(keyword.split()) <= 3:
                            keyword_conditions.append(f'fullText contains "{keyword}"')
                        else:
                            keyword_conditions.append(f'fullText contains \'{keyword}\'')
                    query_parts.append(f"({' or '.join(keyword_conditions)})")
                
                # ファイルタイプ指定
                if file_types:
                    mime_conditions = []
                    lower_types = [ft.lower() for ft in file_types]
                    for file_type in lower_types:
                        if file_type in self.MIME_TYPE_MAP:
                            mime_value = self.MIME_TYPE_MAP[file_type]
                            if isinstance(mime_value, list):
                                mime_conditions.extend([f"mimeType='{v}'" for v in mime_value])
                            else:
                                mime_conditions.append(f"mimeType='{mime_value}'")

                    if mime_conditions:
                        query_parts.append(f"({' or '.join(mime_conditions)})")

                    if 'markdown' in lower_types:
                        query_parts.append("name contains '.md'")
                
                # トラッシュを除外
                query_parts.append("trashed=false")
                
                base_query = " and ".join(query_parts)
            
            # フォルダ制限と除外の追加
            query_parts = [base_query] if base_query != "trashed=false" else ["trashed=false"]
            
            # フォルダ指定
            if folder_id and folder_id != "root":
                query_parts.append(f"'{folder_id}' in parents")
            
            # 除外フォルダ指定（階層的除外）
            all_excluded_folders = []
            if excluded_folder_ids:
                all_excluded_folders = await self._get_all_descendant_folders(excluded_folder_ids)
                logger.info(f"Total folders to exclude (including descendants): {len(all_excluded_folders)}")
                
                # クエリで全除外フォルダを指定 (分割処理)
                if len(all_excluded_folders) > 20:  # Google Drive APIの制限を考慮
                    logger.warning(f"Too many excluded folders ({len(all_excluded_folders)}), limiting to first 20")
                    all_excluded_folders = all_excluded_folders[:20]
                
                for excluded_id in all_excluded_folders:
                    query_parts.append(f"not '{excluded_id}' in parents")
            
            query = " and ".join(query_parts)
            logger.info(f"Final Google Drive search query: {query[:500]}...")  # ログを制限
            
            # ファイル検索実行
            results = self.service.files().list(
                q=query,
                pageSize=max_results,
                fields="nextPageToken, files(id, name, mimeType, createdTime, modifiedTime, size, webViewLink)"
            ).execute()
            
            files = results.get('files', [])
            
            # ファイル内容を取得
            documents = []
            for file in files:
                try:
                    content = await self._get_file_content(file)
                    if content:
                        documents.append({
                            "content": content,
                            "metadata": {
                                "id": file['id'],
                                "title": file['name'],
                                "mimeType": file['mimeType'],
                                "createdTime": file.get('createdTime'),
                                "modifiedTime": file.get('modifiedTime'),
                                "size": file.get('size'),
                                "webViewLink": file.get('webViewLink'),
                                "source": "google_drive"
                            },
                            "file_id": file['id'],
                            "title": file['name'],
                            "mime_type": file['mimeType']
                        })
                except Exception as e:
                    logger.error(f"Error processing file {file['name']}: {e}")
                    continue
            
            # 結果品質の分析とログ
            if hierarchical_keywords:
                primary_count = len(hierarchical_keywords.get('primary_keywords', []))
                secondary_count = len(hierarchical_keywords.get('secondary_keywords', []))
                logger.info(f"Found {len(documents)} documents using hierarchical keywords")
                logger.info(f"  Primary keywords: {primary_count}, Secondary: {secondary_count}")
            else:
                logger.info(f"Found {len(documents)} documents using simple keywords: {keywords[:3]}...")
            
            # 結果の多様性分析
            source_types = {}
            for doc in documents:
                mime_type = doc.get('mime_type', 'unknown')
                source_types[mime_type] = source_types.get(mime_type, 0) + 1
            
            logger.info(f"Result diversity: {dict(list(source_types.items())[:5])}")  # Top 5 types
            return documents
            
        except HttpError as e:
            logger.error(f"Google Drive API error: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error in Google Drive search: {e}")
            return []
    
    async def _get_file_content(self, file: Dict[str, Any]) -> Optional[str]:
        """ファイルの内容を取得"""
        
        file_id = file['id']
        mime_type = file['mimeType']
        
        try:
            # Google Docsの場合
            if mime_type == 'application/vnd.google-apps.document':
                # テキスト形式でエクスポート
                request = self.service.files().export_media(
                    fileId=file_id,
                    mimeType='text/plain'
                )
                content_bytes = request.execute()
                return content_bytes.decode('utf-8')
            
            # Google Sheetsの場合
            elif mime_type == 'application/vnd.google-apps.spreadsheet':
                # CSV形式でエクスポート
                request = self.service.files().export_media(
                    fileId=file_id,
                    mimeType='text/csv'
                )
                content_bytes = request.execute()
                return content_bytes.decode('utf-8')
            
            # PDFファイルの場合
            elif mime_type == 'application/pdf':
                # PDFはMistral OCRで処理するため、バイナリコンテンツを返す
                request = self.service.files().get_media(fileId=file_id)
                content_bytes = request.execute()
                return f"[PDF_BINARY_CONTENT]{len(content_bytes)} bytes"
            
            # その他のファイル
            else:
                request = self.service.files().get_media(fileId=file_id)
                content_bytes = request.execute()
                
                # テキストファイルとして読み込み試行
                try:
                    return content_bytes.decode('utf-8')
                except UnicodeDecodeError:
                    return f"[BINARY_CONTENT]{len(content_bytes)} bytes"
                    
        except HttpError as e:
            logger.error(f"Error getting content for file {file_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting file content: {e}")
            return None
    
    async def _get_all_descendant_folders(self, folder_ids: List[str]) -> List[str]:
        """指定フォルダとその全子孫フォルダのIDリストを取得"""
        
        all_folders = set(folder_ids)  # 指定フォルダ自体も含める
        
        if not self.service:
            return list(all_folders)
        
        try:
            # 各フォルダの子フォルダを再帰的に取得
            for folder_id in folder_ids:
                descendants = await self._get_descendant_folders_recursive(folder_id, set())
                all_folders.update(descendants)
            
            logger.info(f"Expanded {len(folder_ids)} folders to {len(all_folders)} total folders (including descendants)")
            return list(all_folders)
            
        except Exception as e:
            logger.error(f"Error getting descendant folders: {e}")
            return folder_ids  # エラー時は元のリストを返す
    
    async def _get_descendant_folders_recursive(self, folder_id: str, visited: set) -> set:
        """フォルダの子孫フォルダを再帰的に取得（循環参照回避）"""
        
        if folder_id in visited:
            return set()
        
        visited.add(folder_id)
        descendants = {folder_id}
        
        try:
            # 子フォルダを検索
            query = f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
            
            results = self.service.files().list(
                q=query,
                pageSize=1000,  # 大量のフォルダに対応
                fields="files(id)"
            ).execute()
            
            child_folders = results.get('files', [])
            
            # 各子フォルダを再帰的に処理
            for child in child_folders:
                child_id = child['id']
                child_descendants = await self._get_descendant_folders_recursive(child_id, visited.copy())
                descendants.update(child_descendants)
            
            return descendants
            
        except Exception as e:
            logger.error(f"Error getting child folders for {folder_id}: {e}")
            return {folder_id}
    
    async def _is_file_in_excluded_folders(self, file_id: str, excluded_folder_ids: List[str]) -> bool:
        """ファイルが除外フォルダ内にあるかチェック"""
        
        if not self.service or not excluded_folder_ids:
            return False
        
        try:
            # ファイルの親フォルダ情報を取得
            file_info = self.service.files().get(
                fileId=file_id,
                fields="parents"
            ).execute()
            
            parents = file_info.get('parents', [])
            
            # 直接の親フォルダが除外リストにあるかチェック
            for parent_id in parents:
                if parent_id in excluded_folder_ids:
                    return True
                
                # 祖先フォルダも再帰的にチェック
                if await self._is_folder_descendant_of_excluded(parent_id, excluded_folder_ids):
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking file parents for {file_id}: {e}")
            return False
    
    async def _is_folder_descendant_of_excluded(self, folder_id: str, excluded_folder_ids: List[str], visited: Optional[set] = None) -> bool:
        """フォルダが除外フォルダの子孫かチェック（循環参照回避）"""
        
        if visited is None:
            visited = set()
        
        if folder_id in visited:
            return False
        
        visited.add(folder_id)
        
        try:
            # フォルダの親フォルダ情報を取得
            folder_info = self.service.files().get(
                fileId=folder_id,
                fields="parents"
            ).execute()
            
            parents = folder_info.get('parents', [])
            
            for parent_id in parents:
                if parent_id in excluded_folder_ids:
                    return True
                
                # ルートフォルダに達した場合は停止
                if parent_id == 'root':
                    continue
                
                # 祖先フォルダを再帰的にチェック
                if await self._is_folder_descendant_of_excluded(parent_id, excluded_folder_ids, visited):
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking folder hierarchy for {folder_id}: {e}")
            return False
    
    async def _is_file_in_excluded_folders_fast(self, file_id: str, all_excluded_folder_ids: List[str]) -> bool:
        """効率化版：ファイルが除外フォルダ内にあるかチェック（事前に取得した全除外フォルダリスト使用）"""
        
        if not self.service or not all_excluded_folder_ids:
            return False
        
        try:
            # ファイルの直接の親フォルダ情報を取得
            file_info = self.service.files().get(
                fileId=file_id,
                fields="parents"
            ).execute()
            
            parents = file_info.get('parents', [])
            
            # 直接の親フォルダが除外リストにあるかチェック
            for parent_id in parents:
                if parent_id in all_excluded_folder_ids:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking file parents for {file_id}: {e}")
            return False
    
    async def list_files_in_folder(self, folder_id: str = "root") -> List[Dict[str, Any]]:
        """指定されたフォルダ内のファイル一覧を取得"""
        
        if not self.service:
            return []
        
        try:
            query = f"'{folder_id}' in parents and trashed=false"
            
            results = self.service.files().list(
                q=query,
                pageSize=100,
                fields="nextPageToken, files(id, name, mimeType, createdTime, modifiedTime)"
            ).execute()
            
            files = results.get('files', [])
            
            return [{
                "id": file['id'],
                "name": file['name'],
                "mimeType": file['mimeType'],
                "createdTime": file.get('createdTime'),
                "modifiedTime": file.get('modifiedTime')
            } for file in files]
            
        except HttpError as e:
            logger.error(f"Error listing files in folder {folder_id}: {e}")
            return []
    
    async def search_files_with_hierarchical_keywords(
        self,
        hierarchical_keywords: Dict[str, List[str]],
        file_types: Optional[List[str]] = None,
        folder_id: Optional[str] = "root",
        max_results: int = 50,
        excluded_folder_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """階層的キーワードを使用した最適化された検索"""
        
        return await self.search_files(
            keywords=[],  # 空のキーワードリスト
            file_types=file_types,
            folder_id=folder_id,
            max_results=max_results,
            excluded_folder_ids=excluded_folder_ids,
            hierarchical_keywords=hierarchical_keywords
        )

    async def search_files_with_langchain(
        self,
        keywords: List[str],
        file_types: Optional[List[str]] = None,
        folder_id: Optional[str] = "root",
        max_results: int = 50,
        excluded_folder_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """LangChainのGoogleDriveLoaderを使用したファイル検索"""
        
        if not LANGCHAIN_GOOGLE_AVAILABLE:
            logger.warning("LangChain GoogleDriveLoader not available, falling back to regular search")
            return await self.search_files(keywords, file_types, folder_id, max_results, excluded_folder_ids)
        
        try:
            # LangChain GoogleDriveLoaderを使用
            loader = GoogleDriveLoader(
                folder_id=folder_id,
                file_types=file_types or ["document", "sheet", "pdf"],
                recursive=True,
                num_results=max_results,
                load_auth=True
            )
            
            # ドキュメントをロード
            documents = await asyncio.to_thread(loader.load)
            
            # キーワードと除外フォルダでフィルタリング
            filtered_docs = []
            all_excluded_folders = []
            if excluded_folder_ids:
                all_excluded_folders = await self._get_all_descendant_folders(excluded_folder_ids)
            
            for doc in documents:
                content_lower = doc.page_content.lower()
                if any(keyword.lower() in content_lower for keyword in keywords):
                    # 除外フォルダをチェック（効率化版）
                    file_id = doc.metadata.get("id")
                    if all_excluded_folders and file_id:
                        if await self._is_file_in_excluded_folders_fast(file_id, all_excluded_folders):
                            continue
                    
                    filtered_docs.append({
                        "content": doc.page_content,
                        "metadata": {
                            **doc.metadata,
                            "source": "google_drive_langchain"
                        },
                        "file_id": file_id,
                        "title": doc.metadata.get("title"),
                        "mime_type": doc.metadata.get("mimeType")
                    })
            
            logger.info(f"LangChain GoogleDriveLoader found {len(filtered_docs)} documents")
            return filtered_docs
            
        except Exception as e:
            logger.error(f"Error with LangChain GoogleDriveLoader: {e}")
            logger.info("Falling back to regular Google Drive search")
            return await self.search_files(keywords, file_types, folder_id, max_results, excluded_folder_ids)
    
    def get_status(self) -> Dict[str, Any]:
        """Google Drive ツールの状態を取得"""
        auth_method = "none"
        if self.credentials:
            if hasattr(self.credentials, 'service_account_email'):
                auth_method = "service_account"
            else:
                auth_method = "oauth2"
        
        return {
            "service_initialized": self.service is not None,
            "credentials_available": self.credentials is not None,
            "authentication_method": auth_method,
            "oauth_flow_configured": self.oauth_flow is not None,
            "needs_authentication": self.service is None and self.oauth_flow is not None,
            "langchain_available": LANGCHAIN_GOOGLE_AVAILABLE,
            "hierarchical_search_enabled": True,
            "advanced_query_builder": True,
            "phrase_matching_support": True
        }