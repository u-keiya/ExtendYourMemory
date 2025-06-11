# 設定ファイルベースの除外フォルダ管理

## 概要

除外フォルダをJSONファイルで管理し、APIを通じて動的に設定できる機能を実装しました。これにより、毎回APIリクエストでフォルダIDを指定する必要がなくなります。

## 設定ファイル

### ファイルの場所
```
config/excluded_folders.json
```

### 設定ファイルの構造

```json
{
  "excluded_folders": [
    {
      "id": "folder_id_here",
      "name": "フォルダ名",
      "description": "フォルダの説明",
      "enabled": true,
      "added_date": "2024-01-01T00:00:00Z"
    }
  ],
  "settings": {
    "auto_exclude_enabled": true,
    "cache_duration_hours": 24,
    "max_excluded_folders": 50
  },
  "last_updated": "2024-01-01T00:00:00Z",
  "version": "1.0"
}
```

## 使用方法

### 1. 自動除外機能

設定ファイルに登録された除外フォルダは、APIリクエストで`excluded_folder_ids`を指定しない場合に自動で適用されます。

```bash
# 除外フォルダを自動で適用
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "AI技術について"}'
```

### 2. 手動指定での無効化

APIリクエストで`excluded_folder_ids`を明示的に指定すると、設定ファイルの自動除外は無効化されます。

```bash
# 設定ファイル無視、指定フォルダのみ除外
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "AI技術について",
    "excluded_folder_ids": ["specific_folder_id"]
  }'

# 全フォルダを検索対象にする（除外なし）
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "AI技術について", 
    "excluded_folder_ids": []
  }'
```

## 設定管理API

### 除外フォルダの確認

```bash
curl "http://localhost:8000/config/excluded-folders"
```

**レスポンス例:**
```json
{
  "excluded_folders": [...],
  "settings": {...},
  "total_enabled": 3
}
```

### 除外フォルダの追加

```bash
curl -X POST "http://localhost:8000/config/excluded-folders" \
  -H "Content-Type: application/json" \
  -d '{
    "folder_id": "new_folder_id",
    "name": "新しいフォルダ",
    "description": "除外したいフォルダ",
    "enabled": true
  }'
```

### 除外フォルダの削除

```bash
curl -X DELETE "http://localhost:8000/config/excluded-folders/folder_id_to_remove"
```

### 除外フォルダの有効/無効切り替え

```bash
curl -X PATCH "http://localhost:8000/config/excluded-folders/folder_id/toggle"
```

### 設定の更新

```bash
curl -X PATCH "http://localhost:8000/config/settings" \
  -H "Content-Type: application/json" \
  -d '{
    "settings": {
      "auto_exclude_enabled": false,
      "max_excluded_folders": 100
    }
  }'
```

### 設定ファイルの再読み込み

```bash
curl -X POST "http://localhost:8000/config/excluded-folders/reload"
```

## 設定オプション

### auto_exclude_enabled
- **デフォルト**: `true`
- **説明**: APIリクエストで除外フォルダが指定されない場合に、設定ファイルの除外フォルダを自動適用するかどうか

### cache_duration_hours
- **デフォルト**: `24`
- **説明**: 除外フォルダのキャッシュ時間（将来の機能）

### max_excluded_folders
- **デフォルト**: `50`
- **説明**: 登録可能な除外フォルダの最大数

## ワークフロー例

### 初期設定

1. **フォルダIDの取得**
   ```bash
   # Google DriveでフォルダのURLを確認
   # URL: https://drive.google.com/drive/folders/FOLDER_ID_HERE
   ```

2. **除外フォルダの追加**
   ```bash
   curl -X POST "http://localhost:8000/config/excluded-folders" \
     -H "Content-Type: application/json" \
     -d '{
       "folder_id": "1ABC123_personal_photos",
       "name": "Personal Photos",
       "description": "プライベートな写真フォルダ"
     }'
   ```

3. **設定確認**
   ```bash
   curl "http://localhost:8000/config/excluded-folders"
   ```

### 日常的な使用

```bash
# 通常の検索（除外フォルダ自動適用）
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "プロジェクト資料"}'
```

### 設定の調整

```bash
# 特定フォルダを一時的に無効化
curl -X PATCH "http://localhost:8000/config/excluded-folders/1ABC123_personal_photos/toggle"

# 自動除外機能を無効化
curl -X PATCH "http://localhost:8000/config/settings" \
  -H "Content-Type: application/json" \
  -d '{"settings": {"auto_exclude_enabled": false}}'
```

## 利点

1. **設定の永続化**: 除外フォルダ設定がファイルに保存される
2. **管理の簡単さ**: Web APIで設定を動的に変更可能
3. **柔軟性**: 自動除外とリクエスト別除外の両方をサポート
4. **デバッグしやすさ**: 設定ファイルで現在の除外状態が確認可能
5. **バックアップ可能**: JSONファイルを簡単にバックアップ・復元可能

## トラブルシューティング

### 設定ファイルが見つからない場合

システムが自動でデフォルト設定ファイルを作成します。

### 除外が効かない場合

1. 設定の確認:
   ```bash
   curl "http://localhost:8000/config/excluded-folders"
   ```

2. 自動除外設定の確認:
   ```json
   {
     "settings": {
       "auto_exclude_enabled": true  // これがtrueであることを確認
     }
   }
   ```

3. フォルダIDの確認:
   - Google DriveのフォルダURLからフォルダIDが正しいか確認

4. ログの確認:
   ```bash
   docker logs extendyourmemory-backend-1 | grep "excluded"
   ```

### 設定ファイルの手動編集

必要に応じて`config/excluded_folders.json`を直接編集できます。編集後は再読み込みAPIを実行してください。

```bash
curl -X POST "http://localhost:8000/config/excluded-folders/reload"
```