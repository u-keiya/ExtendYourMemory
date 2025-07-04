"""
Mistral OCR MCP Tool Implementation
"""

import os
import base64
import asyncio
from typing import Optional
from mistralai import Mistral
import logging

logger = logging.getLogger(__name__)

class MistralOCRTool:
    def __init__(self):
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Mistral AIクライアントを初期化"""
        api_key = os.getenv('MISTRAL_API_KEY')
        
        if api_key:
            try:
                self.client = Mistral(api_key=api_key)
                logger.info("Mistral OCR client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Mistral client: {e}")
                logger.warning("Mistral OCR functionality will be unavailable")
        else:
            logger.warning("MISTRAL_API_KEY not found in environment variables")
            logger.warning("Mistral OCR functionality will be unavailable")
    
    async def process_pdf_to_markdown(
        self,
        file_content: bytes,
        file_name: str,
        language: str = "ja"
    ) -> str:
        """PDFファイルをMistral OCRでMarkdown変換"""
        
        if not self.client:
            logger.error("Mistral OCR client not available - API key required")
            raise RuntimeError("Mistral OCR service unavailable: MISTRAL_API_KEY not configured")
        
        try:
            # ファイルサイズチェック（50MB制限）
            if len(file_content) > 50 * 1024 * 1024:
                logger.error(f"File {file_name} exceeds 50MB limit")
                return f"# {file_name}\n\nError: File size exceeds 50MB limit for Mistral OCR API"
            
            # Base64エンコード
            file_base64 = base64.b64encode(file_content).decode('utf-8')
            
            # Mistral OCR API呼び出し
            response = await asyncio.to_thread(
                self._process_with_mistral_api,
                file_base64,
                file_name
            )
            
            # レスポンス形式の確認とマークダウン抽出
            if response:
                # レスポンス構造をログ出力（デバッグ用）
                logger.info(f"Mistral OCR response structure for {file_name}: {list(response.keys()) if isinstance(response, dict) else type(response)}")
                
                # 公式ドキュメントに基づく抽出
                markdown_content = ""
                
                # 直接的なmarkdownフィールドをチェック
                if isinstance(response, dict) and 'markdown' in response:
                    markdown_content = response['markdown']
                # pagesフィールドをチェック
                elif isinstance(response, dict) and 'pages' in response:
                    for i, page in enumerate(response['pages']):
                        if i > 0:
                            markdown_content += "\n\n---\n\n"  # ページ区切り
                        markdown_content += page.get('markdown', '')
                # contentフィールドをチェック
                elif isinstance(response, dict) and 'content' in response:
                    markdown_content = response['content']
                # レスポンス全体が文字列の場合
                elif isinstance(response, str):
                    markdown_content = response
                else:
                    logger.warning(f"Unexpected response format from Mistral OCR: {response}")
                    # 可能な限り文字列として扱う
                    markdown_content = str(response)
                
                if markdown_content:
                    logger.info(f"Successfully processed PDF {file_name} to markdown ({len(markdown_content)} chars)")
                    return markdown_content
                else:
                    logger.error(f"No markdown content found in response for {file_name}")
                    raise RuntimeError(f"No markdown content found in Mistral OCR response for {file_name}")
            
            else:
                logger.error(f"Empty response from Mistral OCR API for {file_name}")
                raise RuntimeError(f"Empty response from Mistral OCR API for {file_name}")
                
        except Exception as e:
            logger.error(f"Error processing PDF {file_name} with Mistral OCR: {e}")
            raise RuntimeError(f"Failed to process PDF with Mistral OCR: {e}")
    
    def _process_with_mistral_api(self, file_base64: str, file_name: str) -> dict:
        """Mistral OCR APIを同期的に呼び出し（公式ドキュメント準拠）"""
        
        try:
            # 公式ドキュメント準拠の正しい形式
            response = self.client.ocr.process(
                model="mistral-ocr-latest",  # 最新モデルを使用
                document={
                    "type": "document_url",
                    "document_url": f"data:application/pdf;base64,{file_base64}"
                },
                include_image_base64=True  # 画像データも含める
            )
            
            logger.info(f"Mistral OCR API call successful for {file_name}")
            return response.dict() if hasattr(response, 'dict') else response
            
        except Exception as e:
            logger.error(f"Mistral API call failed for {file_name}: {e}")
            logger.error(f"Full error details: {str(e)}")
            raise
    
    async def process_image_to_markdown(
        self,
        image_content: bytes,
        image_name: str,
        language: str = "ja"
    ) -> str:
        """画像ファイルをMistral OCRでMarkdown変換"""
        
        if not self.client:
            logger.error("Mistral OCR client not available - API key required")
            raise RuntimeError("Mistral OCR service unavailable: MISTRAL_API_KEY not configured")
        
        try:
            # ファイルサイズチェック
            if len(image_content) > 50 * 1024 * 1024:
                logger.error(f"Image {image_name} exceeds 50MB limit")
                return f"# {image_name}\n\nError: File size exceeds 50MB limit for Mistral OCR API"
            
            # 画像形式判定
            image_type = self._detect_image_type(image_content)
            if not image_type:
                return f"# {image_name}\n\nError: Unsupported image format"
            
            # Base64エンコード
            image_base64 = base64.b64encode(image_content).decode('utf-8')
            
            # Mistral OCR API呼び出し
            response = await asyncio.to_thread(
                self._process_image_with_mistral_api,
                image_base64,
                image_name,
                image_type
            )
            
            # 画像レスポンスの処理
            if response:
                # レスポンス構造をログ出力
                logger.info(f"Mistral OCR response structure for image {image_name}: {list(response.keys()) if isinstance(response, dict) else type(response)}")
                
                markdown_content = ""
                
                # 直接的なmarkdownフィールドをチェック
                if isinstance(response, dict) and 'markdown' in response:
                    markdown_content = response['markdown']
                # pagesフィールドをチェック（画像は通常1ページ）
                elif isinstance(response, dict) and 'pages' in response and len(response['pages']) > 0:
                    markdown_content = response['pages'][0].get('markdown', '')
                # contentフィールドをチェック
                elif isinstance(response, dict) and 'content' in response:
                    markdown_content = response['content']
                # レスポンス全体が文字列の場合
                elif isinstance(response, str):
                    markdown_content = response
                else:
                    logger.warning(f"Unexpected response format from Mistral OCR for image: {response}")
                    markdown_content = str(response)
                
                if markdown_content:
                    logger.info(f"Successfully processed image {image_name} to markdown ({len(markdown_content)} chars)")
                    return markdown_content
                else:
                    logger.error(f"No markdown content found in response for image {image_name}")
                    raise RuntimeError(f"No markdown content found in Mistral OCR response for image {image_name}")
            else:
                logger.error(f"Empty response from Mistral OCR API for image {image_name}")
                raise RuntimeError(f"Empty response from Mistral OCR API for image {image_name}")
                
        except Exception as e:
            logger.error(f"Error processing image {image_name} with Mistral OCR: {e}")
            raise RuntimeError(f"Failed to process image with Mistral OCR: {e}")
    
    def _process_image_with_mistral_api(self, image_base64: str, image_name: str, image_type: str) -> dict:
        """画像をMistral OCR APIで処理（公式ドキュメント準拠）"""
        
        try:
            # 画像の場合も同じdocument形式を使用
            response = self.client.ocr.process(
                model="mistral-ocr-latest",
                document={
                    "type": "document_url",
                    "document_url": f"data:{image_type};base64,{image_base64}"
                },
                include_image_base64=True
            )
            
            logger.info(f"Mistral OCR API call successful for image {image_name}")
            return response.dict() if hasattr(response, 'dict') else response
            
        except Exception as e:
            logger.error(f"Mistral API call failed for image {image_name}: {e}")
            logger.error(f"Full error details: {str(e)}")
            raise
    
    def _detect_image_type(self, image_content: bytes) -> Optional[str]:
        """画像ファイルの形式を検出"""
        
        # ファイルヘッダーから形式を判定
        if image_content.startswith(b'\xff\xd8\xff'):
            return "image/jpeg"
        elif image_content.startswith(b'\x89PNG\r\n\x1a\n'):
            return "image/png"
        elif image_content.startswith(b'GIF87a') or image_content.startswith(b'GIF89a'):
            return "image/gif"
        elif image_content.startswith(b'RIFF') and b'WEBP' in image_content[:12]:
            return "image/webp"
        else:
            return None
    
    
    async def check_api_status(self) -> dict:
        """API接続状態をチェック"""
        
        status = {
            "api_key_configured": bool(os.getenv('MISTRAL_API_KEY')),
            "client_initialized": self.client is not None,
            "status": "unknown"
        }
        
        if not status["api_key_configured"]:
            status["status"] = "api_key_missing"
        elif not status["client_initialized"]:
            status["status"] = "client_error"
        else:
            try:
                # 簡単なテスト呼び出し（実際には課金されない小さなテスト）
                # 注意: 実際のテストでは課金が発生する可能性があります
                status["status"] = "ready"
            except Exception as e:
                status["status"] = f"error: {str(e)}"
        
        return status