# リモートサーバー展開ガイド

Extend Your Memory をリモートサーバーで展開するための完全ガイドです。

## 📋 前提条件

- Docker & Docker Compose インストール済み
- ポート 3000, 8000, 8501 が利用可能
- 外部ネットワークアクセス設定済み

## 🚀 クイックスタート

### 1. リポジトリクローン
```bash
git clone <repository-url>
cd ExtendYourMemory
```

### 2. 環境変数設定
```bash
# テンプレートをコピー
cp .env.remote.template .env

# 環境変数を編集
nano .env
```

### 3. 必須環境変数の設定
```bash
# Google API キー
GOOGLE_API_KEY=your_google_api_key_here
MISTRAL_API_KEY=your_mistral_api_key_here

# Google OAuth設定
GOOGLE_OAUTH_CLIENT_ID=your_google_oauth_client_id
GOOGLE_OAUTH_CLIENT_SECRET=your_google_oauth_client_secret

# サーバー設定
YOUR_DOMAIN=your_domain  # あなたのTailscale IPまたはドメイン
GOOGLE_OAUTH_REDIRECT_URI=http://your_domain:8000/auth/google/callback
NEXT_PUBLIC_API_URL=http://your_domain:8000
```

### 4. リモート用Docker起動
```bash
# リモート設定でサービス開始
docker compose -f docker-compose.remote.yml up --build -d

# ログ確認
docker compose -f docker-compose.remote.yml logs -f
```

### 5. 接続確認
```bash
# ヘルスチェック
curl http://your_domain:8000/health    # Backend
curl http://your_domain:8501/health    # MCP Server
curl http://your_domain:3000           # Frontend
```

## 🔧 Google OAuth設定

### Google Cloud Console設定
1. [Google Cloud Console](https://console.cloud.google.com/) にアクセス
2. APIs & Services > Credentials
3. OAuth 2.0 Client IDs を編集
4. 以下を追加:

**承認済みJavaScript生成元:**
```
http://your_domain:8000
http://your_domain:3000
```

**承認済みリダイレクトURI:**
```
http://your_domain:8000/auth/google/callback
```

## 🌐 Chrome拡張機能のリモート対応

### 方法1: 自動設定スクリプト使用（推奨）

```bash
# Chrome拡張フォルダに移動
cd chrome-extension/

# 環境変数ファイルを作成（オプション）
cp .env.chrome.template .env.chrome
nano .env.chrome  # 設定を編集

# 自動設定スクリプト実行
./configure-remote.sh
```

**対話式設定例:**
```
リモートサーバーのドメインまたはIPアドレス [your_domain]: your_domain
MCP Server ポート番号 [8501]: 8501
Backend API ポート番号 [8000]: 8000
Frontend ポート番号 [3000]: 3000
```

### 方法2: 環境変数ファイル使用

```bash
# 設定ファイル作成
cat > chrome-extension/.env.chrome << EOF
REMOTE_DOMAIN=your_domain
MCP_PORT=8501
BACKEND_PORT=8000
FRONTEND_PORT=3000
USE_HTTPS=false
EOF

# 設定スクリプト実行（対話なし）
cd chrome-extension/
./configure-remote.sh
```

### 方法3: 手動設定

```bash
# Chrome拡張フォルダに移動
cd chrome-extension/

# リモート用ファイルを本体にコピー
cp manifest.remote.json manifest.json
cp popup.remote.js popup.js
```

### Chrome拡張機能の読み込み

1. Chrome拡張機能管理画面 (`chrome://extensions/`) を開く
2. 「デベロッパーモード」を有効化
3. 「パッケージ化されていない拡張機能を読み込む」
4. `chrome-extension/` フォルダを選択

### 拡張機能設定の確認

設定が正しく適用されているか確認:
1. 拡張機能アイコンをクリック
2. 「View Options」で設定画面を開く
3. URL設定を確認・調整

### ローカル開発環境に戻す

```bash
cd chrome-extension/
./reset-to-local.sh
```

## 🎯 アクセス方法

### メインアプリケーション
```
http://your_domain:3000
```

### API エンドポイント
```
http://your_domain:8000/docs      # API Documentation
http://your_domain:8000/health    # Health Check
```

### MCP Server
```
http://your_domain:8501/health    # MCP Health Check
```

## 🔒 セキュリティ考慮事項

### 外部公開時の推奨設定

1. **SSL証明書の設定**
```bash
# Let's Encrypt使用例
sudo apt install certbot
sudo certbot certonly --standalone -d yourdomain.com
```

2. **Nginx リバースプロキシ設定**
```nginx
server {
    listen 80;
    server_name yourdomain.com;
    
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

3. **ファイアウォール設定**
```bash
# UFW使用例
sudo ufw allow 22
sudo ufw allow 80
sudo ufw allow 443
sudo ufw allow 3000
sudo ufw allow 8000
sudo ufw allow 8501
sudo ufw enable
```

## 🛠️ トラブルシューティング

### よくある問題と解決策

**1. CORS エラー**
```bash
# backend/main.py と mcp-server/server_fastapi.py の
# CORS設定にあなたのドメインが含まれているか確認
```

**2. Chrome拡張機能が接続できない**
```bash
# manifest.json の host_permissions に
# あなたのドメインが含まれているか確認
```

**3. Google OAuth エラー**
```bash
# Google Cloud Console でリダイレクトURIが
# 正しく設定されているか確認
```

### ログ確認方法
```bash
# 全サービスのログ
docker compose -f docker-compose.remote.yml logs

# 特定サービスのログ
docker compose -f docker-compose.remote.yml logs backend
docker compose -f docker-compose.remote.yml logs mcp-server
docker compose -f docker-compose.remote.yml logs frontend
```

### サービス再起動
```bash
# 全サービス再起動
docker compose -f docker-compose.remote.yml restart

# 特定サービス再起動
docker compose -f docker-compose.remote.yml restart backend
```

## 🔄 更新とメンテナンス

### アプリケーション更新
```bash
# 最新コードを取得
git pull origin main

# サービス再構築
docker compose -f docker-compose.remote.yml up --build -d
```

### バックアップ
```bash
# 設定ファイルのバックアップ
cp .env .env.backup
cp docker-compose.remote.yml docker-compose.remote.yml.backup

# ボリュームデータのバックアップ
docker run --rm -v $(pwd):/backup -v extendyourmemory_config:/data alpine tar czf /backup/config-backup.tar.gz -C /data .
```

## 📞 サポート

問題が発生した場合:
1. ログを確認
2. 設定ファイルを再確認
3. GitHub Issues でサポート要求

---

**注意**: このガイドはリモート展開専用です。開発環境では通常の `docker-compose.yml` を使用してください。