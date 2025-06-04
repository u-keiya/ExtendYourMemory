"""
Google Drive MCP Tool Implementation
"""

import os
import asyncio
from typing import List, Dict, Any, Optional
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import logging

logger = logging.getLogger(__name__)

class GoogleDriveTool:
    def __init__(self):
        self.service = None
        self.credentials = None
        self._initialize_service()
    
    def _initialize_service(self):
        """Google Drive APIサービスを初期化"""
        try:
            # サービスアカウントキーファイルのパス
            service_account_file = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE', './credentials/service-account-key.json')
            
            if os.path.exists(service_account_file):
                # サービスアカウント認証
                scopes = [
                    'https://www.googleapis.com/auth/drive.readonly',
                    'https://www.googleapis.com/auth/drive.metadata.readonly'
                ]
                
                self.credentials = service_account.Credentials.from_service_account_file(
                    service_account_file, scopes=scopes
                )
                
                self.service = build('drive', 'v3', credentials=self.credentials)
                logger.info("Google Drive service initialized with service account")
                
            else:
                logger.warning(f"Service account file not found: {service_account_file}")
                logger.info("Google Drive tool will use mock responses")
                
        except Exception as e:
            logger.error(f"Failed to initialize Google Drive service: {e}")
            logger.info("Google Drive tool will use mock responses")
    
    async def search_files(
        self,
        keywords: List[str],
        file_types: Optional[List[str]] = None,
        folder_id: Optional[str] = "root",
        max_results: int = 50
    ) -> List[Dict[str, Any]]:
        """Google Driveからファイルを検索"""
        
        if not self.service:
            return await self._mock_search_results(keywords)
        
        try:
            # クエリ構築
            query_parts = []
            
            # フォルダ指定
            if folder_id and folder_id != "root":
                query_parts.append(f"'{folder_id}' in parents")
            
            # ファイルタイプ指定
            if file_types:
                mime_type_map = {
                    'document': 'application/vnd.google-apps.document',
                    'sheet': 'application/vnd.google-apps.spreadsheet',
                    'pdf': 'application/pdf',
                    'presentation': 'application/vnd.google-apps.presentation'
                }
                
                mime_conditions = []
                for file_type in file_types:
                    if file_type.lower() in mime_type_map:
                        mime_conditions.append(f"mimeType='{mime_type_map[file_type.lower()]}'")
                
                if mime_conditions:
                    query_parts.append(f"({' or '.join(mime_conditions)})")
            
            # キーワード検索
            if keywords:
                keyword_conditions = []
                for keyword in keywords:
                    keyword_conditions.append(f"fullText contains '{keyword}'")
                query_parts.append(f"({' or '.join(keyword_conditions)})")
            
            # トラッシュを除外
            query_parts.append("trashed=false")
            
            query = " and ".join(query_parts)
            logger.info(f"Google Drive search query: {query}")
            
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
            
            logger.info(f"Found {len(documents)} documents matching keywords: {keywords}")
            return documents
            
        except HttpError as e:
            logger.error(f"Google Drive API error: {e}")
            return await self._mock_search_results(keywords)
        except Exception as e:
            logger.error(f"Unexpected error in Google Drive search: {e}")
            return await self._mock_search_results(keywords)
    
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
    
    async def _mock_search_results(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """モック検索結果（APIが利用できない場合）"""
        logger.info("Using mock Google Drive search results")
        
        mock_documents = []
        for i, keyword in enumerate(keywords[:3]):  # 最大3つのモック結果
            mock_documents.append({
                "content": f"""# Mock Document: {keyword}

This is a mock Google Drive document containing information about {keyword}.

## Content
Lorem ipsum dolor sit amet, consectetur adipiscing elit. This document would normally contain real content from Google Drive related to {keyword}.

## Key Points
- Mock implementation for testing
- Real implementation requires Google Service Account
- Document ID: mock_{i+1}
""",
                "metadata": {
                    "id": f"mock_drive_id_{i+1}",
                    "title": f"Mock Document - {keyword}",
                    "mimeType": "application/vnd.google-apps.document",
                    "createdTime": "2024-01-01T00:00:00.000Z",
                    "modifiedTime": "2024-01-01T00:00:00.000Z",
                    "source": "google_drive_mock"
                },
                "file_id": f"mock_drive_id_{i+1}",
                "title": f"Mock Document - {keyword}",
                "mime_type": "application/vnd.google-apps.document"
            })
        
        return mock_documents
    
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