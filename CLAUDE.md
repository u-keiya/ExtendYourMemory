# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Extend Your Memory** は、AI駆動によるデジタル記憶検索・レポート生成システムです。Google Drive、ブラウザ履歴、Webページから情報を横断検索し、引用付きの構造化レポートを自動生成します。MCP (Model Context Protocol) アーキテクチャを採用し、複数のデータソースを統合しています。

## システムアーキテクチャ

### コア技術スタック
- **Frontend**: Next.js 14 (App Router, TypeScript, Tailwind CSS)
- **Backend**: FastAPI + Pydantic v2 (Python 3.9+)
- **MCP Server**: FastMCP framework によるカスタムツール実装
- **Vector Database**: FAISS (ローカルベクトルストレージ)
- **LLM**: Gemini 2.5 Flash
- **Embeddings**: Google text-embedding-004
- **RAG Pipeline**: LangChain + FAISS

### 主要コンポーネント

#### 1. Frontend (`/frontend/`)
- **実装**: 単一ページアプリケーション (SPA)
- **ファイル構造**: 
  - `app/page.tsx`: メインアプリケーションコンポーネント
  - `app/layout.tsx`: ルートレイアウト
  - `app/globals.css`: Tailwind CSS + カスタムスタイル
- **機能**:
  - 3パネルレイアウト（チャット履歴、メイン検索、RAG結果）
  - WebSocket による リアルタイム進捗表示
  - KaTeX による数式レンダリング
  - LocalStorage による チャット履歴永続化（最大50会話）
  - Google Drive OAuth認証
  - Chrome拡張機能連携

#### 2. Backend (`/backend/`)
- **メインファイル**: `main.py` (FastAPI サーバー)
- **RAGパイプライン**: `rag_pipeline.py` (LangChain + FAISS)
- **設定管理**: `config_manager.py` (除外フォルダ設定)
- **LLMクエリ生成**: `llm_query_generator.py` (AGRフレームワーク)
- **適応的最適化**: `adaptive_faiss_optimizer.py` (FAISS検索最適化)

#### 3. MCP Server (`/mcp-server/`)
- **サーバー**: `server_fastapi.py` (FastAPI実装)
- **ツール実装**:
  - `google_drive_tool.py`: Google Drive検索
  - `chrome_history_tool_remote.py`: Chrome履歴検索
  - `mistral_ocr_tool.py`: PDF/画像OCR処理
  - `web_fetch_tool.py`: Webページ取得

#### 4. Chrome Extension (`/chrome-extension/`)
- **マニフェスト**: `manifest.json` (Manifest V3)
- **バックグラウンド**: `background.js` (履歴アクセス管理)
- **コンテンツ**: `content.js` + `history-bridge.js` (データ橋渡し)
- **ポップアップ**: `popup.html` + `popup.js` (設定UI)

## 実装済み機能詳細

### AGRフレームワーク (Advanced Generation Retrieval)
**場所**: `backend/llm_query_generator.py`
- 階層的キーワード生成: Primary, Secondary, Context, Negative keywords
- クエリ分析: Intent classification, Complexity assessment
- 適応的検索戦略: 精密検索 vs 探索的検索

### RAG処理パイプライン
**場所**: `backend/rag_pipeline.py`
1. **キーワード生成**: AGRフレームワークによる多層キーワード
2. **MCP検索**: Google Drive + Chrome履歴の並列検索
3. **Web取得**: 履歴URLからのコンテンツフェッチ
4. **ドキュメント処理**: Markdown対応チャンク分割
5. **ベクトル化**: Google embedding-004 + FAISS
6. **セマンティック検索**: 類似度スコアフィルタリング付きMMR
7. **レポート生成**: 構造化Markdownレポート + KaTeX数式

### 設定管理システム
**場所**: `backend/config_manager.py`
- 除外フォルダ管理（Google Drive）
- 検索パラメータ調整（類似度閾値、最大文書数等）
- 自動除外機能
- 最終関連性チェックの有効/無効

### リアルタイム進捗追跡
**実装**: WebSocket (`/ws/search`)
- 7段階の検索進捗表示
- 詳細な統計情報（キーワード数、文書数、スコア等）
- エラーハンドリングと回復

## Docker環境

```yaml
services:
  mcp-server:    # Port 8501, MCP tools
  backend:       # Port 8000, FastAPI + RAG
  frontend:      # Port 3000, Next.js
```

### 環境変数
```bash
# 必須
GOOGLE_API_KEY=xxx                  # Gemini + Embeddings
MISTRAL_API_KEY=xxx                # OCR処理
GOOGLE_OAUTH_CLIENT_ID=xxx         # Drive OAuth
GOOGLE_OAUTH_CLIENT_SECRET=xxx     # Drive OAuth

# オプション
MCP_SERVER_URL=http://localhost:8501
BACKEND_URL=http://localhost:8000
```

## 開発・運用

### 起動コマンド
```bash
# 開発環境
docker compose up --build

# 個別起動
cd backend && python main.py
cd mcp-server && python server_fastapi.py  
cd frontend && npm run dev
```

### テスト・品質管理
- Backend: pytest (予定)
- Frontend: Jest + React Testing Library (予定)
- Linting: ruff (Python), ESLint (TypeScript)
- Type checking: mypy (Python), TypeScript

### ログとモニタリング
- 構造化ログ出力 (各コンポーネント)
- 検索統計とパフォーマンス追跡
- ベクトルストアヘルス管理

## セキュリティ・プライバシー

- **APIキー**: ユーザー管理、ブラウザ暗号化保存
- **データアクセス**: 読み取り専用、最小権限
- **Chrome履歴**: 明示的許可、Extension経由
- **ベクトルデータ**: 自動クリーンアップ、ローカル保存
- **OAuth**: Google Drive 制限付きスコープ

## 実装状況

✅ **完全実装済み**
- フルスタック RAG パイプライン
- MCP ツール統合
- リアルタイム WebSocket 通信
- Chrome 拡張機能
- 設定管理システム
- Docker 環境

🔄 **継続改善中**
- テストカバレッジ拡大
- パフォーマンス最適化
- UI/UX 改善

## 今後の拡張

- **新しいMCPツール**: Slack, Notion, ローカルファイル
- **LLM選択肢**: ローカルLLM対応
- **高度なUI**: インタラクティブ可視化
- **コラボレーション**: リアルタイム共同編集

## 開発注意事項

1. **設定システム**: `config_manager.py` で検索パラメータを調整
2. **ベクトルストア**: 自動クリーンアップでデータ汚染を防止
3. **エラーハンドリング**: 各段階で適切なフォールバック実装
4. **パフォーマンス**: 適応的最適化で大規模データセット対応
5. **セキュリティ**: APIキー露出防止、最小権限原則