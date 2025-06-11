# Google Drive フォルダ除外機能

## 概要

Google Drive検索で特定のフォルダを除外する機能が実装されました。この機能により、検索結果から不要なフォルダのファイルを排除できます。

## 使用方法

### 1. フォルダIDの確認

除外したいGoogle DriveフォルダのフォルダIDを取得してください。

- Google DriveでフォルダのURLを確認
- URL: `https://drive.google.com/drive/folders/FOLDER_ID_HERE`
- `FOLDER_ID_HERE`の部分がフォルダIDです

### 2. REST API経由での使用

```bash
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "AI技術について",
    "excluded_folder_ids": ["1ABC123_example_folder_id", "2DEF456_another_folder_id"]
  }'
```

### 3. WebSocket経由での使用

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/search');

ws.onopen = () => {
  ws.send(JSON.stringify({
    query: "AI技術について",
    excluded_folder_ids: ["1ABC123_example_folder_id", "2DEF456_another_folder_id"]
  }));
};
```

### 4. MCP Server直接呼び出し

```bash
curl -X POST "http://localhost:8501/tools/search_google_drive" \
  -H "Content-Type: application/json" \
  -d '{
    "keywords": ["AI", "機械学習"],
    "file_types": ["document", "pdf"],
    "excluded_folder_ids": ["1ABC123_example_folder_id", "2DEF456_another_folder_id"],
    "max_results": 50
  }'
```

## 実装詳細

### フォルダ除外の仕組み（改善版）

1. **事前フォルダ展開**: 除外フォルダの全子孫フォルダを事前に取得
2. **クエリレベル除外**: Google Drive APIのクエリ構文で直接除外（`not 'folder_id' in parents`）
3. **階層的除外**: 指定フォルダとその子フォルダ全てを除外
4. **循環参照回避**: フォルダ階層をたどる際に循環参照を検出・回避

### 除外処理の順序

**改善後（推奨）**:
1. 除外フォルダとその子孫フォルダを事前取得
2. Google Drive APIクエリに除外条件を組み込み
3. 検索実行（除外フォルダのファイルは最初から検索されない）
4. ドキュメント数の減少なし

**以前の方式**:
1. 全ファイルを検索
2. 検索結果から除外フォルダのファイルを削除  
3. ドキュメント数が予期せず減少する可能性

### パフォーマンス考慮

- **事前フォルダ取得**: 除外フォルダの子フォルダ構造を1回だけ取得
- **クエリ最適化**: 除外されるファイルは検索時点で除外
- **API効率**: 不要なファイル内容取得を回避
- **ドキュメント数保証**: `max_results`で指定した数のドキュメントを確実に取得

## 使用例

### シナリオ1: プライベートフォルダの除外

```json
{
  "query": "プロジェクト資料",
  "excluded_folder_ids": ["personal_photos_folder_id", "private_docs_folder_id"]
}
```

### シナリオ2: アーカイブフォルダの除外

```json
{
  "query": "最新の技術文書",
  "excluded_folder_ids": ["archive_2022_folder_id", "old_backups_folder_id"]
}
```

## 制限事項

1. **API制限**: Google Drive APIの呼び出し制限に注意してください
2. **権限**: 除外フォルダの親フォルダ情報を取得するには適切な権限が必要です
3. **パフォーマンス**: 多数のファイルと除外フォルダがある場合、検索時間が増加する可能性があります

## トラブルシューティング

### よくある問題

1. **フォルダIDが無効**: フォルダIDが正しいか確認してください
2. **権限不足**: Google Drive APIの権限設定を確認してください
3. **API制限**: 大量の除外フォルダを指定する場合は制限に注意してください

### ログの確認

```bash
# MCPサーバーのログ
docker logs extendyourmemory-mcp-server-1

# バックエンドのログ
docker logs extendyourmemory-backend-1
```

除外フォルダの情報はログに出力されるため、動作確認に利用してください。