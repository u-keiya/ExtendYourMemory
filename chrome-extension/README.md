# Extend Your Memory - Chrome Extension

この Chrome 拡張機能は、Extend Your Memory システムが Chrome の履歴と ChatGPT の会話履歴に安全にアクセスするためのブリッジ機能を提供します。

## 🎯 目的

Chrome の履歴データと ChatGPT の会話データに直接 SQLite ファイルアクセスするのではなく、Chrome Extension API と DOM アクセスを使用してセキュアで適切な方法で情報を取得します。

## 🏗️ アーキテクチャ

### Components

1. **Background Script** (`background.js`)
   - Chrome History API の呼び出し
   - MCP サーバーとの通信
   - メッセージルーティング

2. **Content Script** (`content.js`)
   - ウェブページと拡張機能の仲介
   - セキュアなメッセージ転送

3. **History Bridge** (`history-bridge.js`)
   - ウェブページに注入されるスクリプト
   - JavaScript API の提供

4. **ChatGPT Bridge** (`chatgpt-bridge.js`)
   - ChatGPT ページに特化したコンテンツスクリプト
   - 会話履歴の抽出と送信
   - localStorage と DOM からのデータ取得

5. **Popup Interface** (`popup.html`, `popup.js`)
   - 拡張機能の状態表示
   - テスト機能

## 🔧 インストール方法

### 1. 拡張機能のロード

```bash
# Chrome ブラウザを開く
# chrome://extensions/ にアクセス
# 「デベロッパー モード」を有効化
# 「パッケージ化されていない拡張機能を読み込む」をクリック
# chrome-extension フォルダを選択
```

### 2. 権限の確認

拡張機能は以下の権限を要求します：

- `history`: Chrome 履歴へのアクセス
- `storage`: 設定の保存
- `alarms`: 定期実行タスク
- `idle`: アイドル状態検知
- `https://chat.openai.com/*`: ChatGPT サイトへのアクセス

### 3. サーバーURLの設定

リモートの MCP サーバーを利用する場合は、ブラウザのコンソールで以下を実行して
サーバー URL を保存します。

```javascript
chrome.storage.local.set({ serverUrl: 'https://your-server.example' });
```

HTTPS サーバーを指定する場合は、証明書が有効であることを確認してください。

## 🚀 使用方法

### JavaScript API

ウェブページから以下のAPIを使用できます：

```javascript
// 履歴検索
const results = await window.ExtendYourMemoryBridge.searchHistory(
  ['AI', 'Python'],  // キーワード
  {
    days: 30,         // 検索対象日数
    maxResults: 50    // 最大結果数
  }
);

// 最近の履歴取得
const recent = await window.ExtendYourMemoryBridge.getRecentHistory({
  hours: 24,          // 取得対象時間
  maxResults: 100     // 最大結果数
});

// 履歴データの送信を明示的にトリガー
await window.ExtendYourMemoryBridge.refreshHistory();

// 拡張機能の利用可能性チェック
const available = window.ExtendYourMemoryBridge.isExtensionAvailable();
```

### イベントリスナー

```javascript
// ブリッジの準備完了イベント
window.addEventListener('ExtendYourMemoryBridgeReady', (event) => {
  console.log('Bridge ready:', event.detail);
});
```

## 🔒 セキュリティ

### Permission Model

- Chrome Extension API を使用することで、ブラウザのセキュリティモデルに準拠
- 直接的なファイルアクセスを回避
- ユーザーの明示的な許可が必要

### Communication Security

- Origin validation で不正なアクセスを防止
- Allowed origins: `http://localhost:8501`, `http://localhost:8000`
- Message-based secure communication

## 📊 データ形式

### 検索結果

```json
{
  "url": "https://example.com",
  "title": "Page Title",
  "visit_time": "2024-01-01T12:00:00.000Z",
  "visit_count": 5,
  "content": "Title: Page Title\\nURL: https://example.com\\nVisit Date: 2024-01-01 12:00:00",
  "metadata": {
    "source": "chrome_history_extension",
    "url": "https://example.com",
    "title": "Page Title",
    "visit_time": "2024-01-01T12:00:00.000Z",
    "visit_count": 5,
    "typed_count": 2
  }
}
```

## 🔄 MCP Server Integration

MCP サーバーは以下の方法で拡張機能と連携します：

1. **Extension Detection**: 拡張機能の利用可能性をチェック
2. **Fallback Strategy**: 拡張機能が利用できない場合は SQLite フォールバック
3. **Unified API**: 同一のインターフェースで複数のアクセス方法をサポート

## 🛠️ 開発者向け情報

### ビルド

```bash
# 拡張機能のパッケージ化（本番用）
# Chrome で chrome://extensions/ にアクセス
# 「拡張機能をパッケージ化」を選択
```

### デバッグ

```bash
# Background script のデバッグ
# Chrome で chrome://extensions/ にアクセス
# 拡張機能の「詳細」→「background page を検査」

# Content script のデバッグ
# ウェブページで F12 → Console タブ
```

### ログ

拡張機能は以下のログを出力します：

- Background script: Chrome DevTools Console
- Content script: ウェブページの Console
- History Bridge: ウェブページの Console

## 🚧 制限事項

### Current Limitations

1. **Manual Installation**: Chrome Web Store への公開は未実装
2. **Remote Usage**: サーバー URL を `chrome.storage.local` に設定することでリモート環境でも利用可能
3. **HTTPS Recommended**: セキュアな通信のため公開環境では HTTPS を使用

### Future Enhancements

1. **Native Messaging**: より高度な通信プロトコル
2. **Real-time Sync**: 履歴変更のリアルタイム同期
3. **Enhanced Security**: より強固なセキュリティ機能

## 📋 トラブルシューティング

### 一般的な問題

1. **拡張機能が動作しない**
   - デベロッパーモードが有効か確認
   - 拡張機能がインストールされているか確認
   - Browser restart

2. **履歴にアクセスできない**
   - History permission が許可されているか確認
   - Chrome のプライベートモードでは動作しません

3. **MCP サーバーと通信できない**
   - localhost:8501 が起動しているか確認
   - CORS settings の確認

### ログの確認

```bash
# Background script logs
chrome://extensions/ → 拡張機能詳細 → background page を検査

# Content script logs  
ウェブページで F12 → Console
```

## 📚 API Reference

### Background Script Events

- `chrome.runtime.onMessage`: 内部メッセージの処理
- `chrome.runtime.onMessageExternal`: 外部アプリケーションからのメッセージ
- `chrome.history.onVisited`: 新しいページ訪問の検出
- `chrome.history.onVisitRemoved`: 履歴削除の検出

### Available Methods

- `searchHistory(keywords, options)`: キーワードベースの履歴検索
- `getRecentHistory(options)`: 最近の履歴取得
- `getVisitDetails(url)`: 特定URLの詳細情報取得
- `refreshHistory()`: 履歴データをサーバーへ即時送信

---

この拡張機能により、Extend Your Memory システムは Chrome の公式 API を使用して安全かつ適切に履歴データにアクセスできます。


# Chrome Extension Configuration Guide

Extend Your Memory Chrome拡張機能の設定・管理ガイドです。

## 🚀 クイックスタート

### ローカル開発環境
```bash
# 既存の設定で動作（変更不要）
# localhost:8501, localhost:8000, localhost:3000
```

### リモートサーバー環境
```bash
cd chrome-extension/

# 方法1: 対話式設定
./configure-remote.sh

# 方法2: 環境変数ファイル使用
cp .env.chrome.template .env.chrome
# .env.chrome を編集してから
./configure-remote.sh
```

## 📋 設定スクリプト

### `configure-remote.sh`
- **用途**: リモートサーバー用に拡張機能を設定
- **機能**: 
  - 対話式設定入力
  - 環境変数ファイル読み込み
  - manifest.json, popup.js の自動生成
  - HTTPS対応

**使用例:**
```bash
# 対話式設定
./configure-remote.sh

# Tailscale環境での設定例
REMOTE_DOMAIN=yourdomain.com ./configure-remote.sh

# 環境変数ファイル使用
echo "REMOTE_DOMAIN=yourdomain.com" > .env.chrome
echo "USE_HTTPS=true" >> .env.chrome
./configure-remote.sh
```

### `reset-to-local.sh`
- **用途**: ローカル開発環境設定に戻す
- **機能**:
  - manifest.json, popup.js をローカル用に復元
  - 拡張機能の保存設定をクリア

**使用例:**
```bash
./reset-to-local.sh
```

## 🔧 環境変数設定

### `.env.chrome.template`
拡張機能設定用のテンプレートファイル:

```bash
# 基本設定
REMOTE_DOMAIN=yourdomain.com  # サーバーIP/ドメイン
MCP_PORT=8501                # MCP Server ポート
BACKEND_PORT=8000            # Backend API ポート  
FRONTEND_PORT=3000           # Frontend ポート

# HTTPS設定
USE_HTTPS=false              # HTTPS使用有無
HTTPS_PORT=443               # HTTPS ポート

# スクリプト制御
SKIP_CONFIRMATION=false      # 確認をスキップ
CREATE_BACKUP=true           # バックアップ作成
```

### 設定例

**Tailscale環境:**
```bash
REMOTE_DOMAIN=yourdomain.com
MCP_PORT=8501
BACKEND_PORT=8000
FRONTEND_PORT=3000
USE_HTTPS=false
```

**本番HTTPS環境:**
```bash
REMOTE_DOMAIN=yourdomain.com
MCP_PORT=8501
BACKEND_PORT=8000
FRONTEND_PORT=3000
USE_HTTPS=true
HTTPS_PORT=443
```

## 📁 ファイル構成

### テンプレートファイル (git追跡対象)
- `manifest.remote.json` - リモート用マニフェスト
- `popup.remote.js` - リモート用ポップアップ
- `options.html` - 設定画面HTML
- `options.js` - 設定画面JavaScript

### 生成ファイル (git追跡除外)
- `manifest.json` - 実際に使用されるマニフェスト
- `popup.js` - 実際に使用されるポップアップ
- `.env.chrome` - 環境変数設定

## 🔄 使用ワークフロー

### 開発→本番デプロイ
```bash
# 1. ローカル開発
git clone <repo>
cd chrome-extension/
# 既存設定で開発

# 2. リモート用設定
./configure-remote.sh
# 設定入力

# 3. Chrome拡張機能読み込み
# chrome://extensions/ で読み込み

# 4. 開発に戻る場合
./reset-to-local.sh
```

### 環境変数ベース展開
```bash
# 1. 設定ファイル準備
cat > .env.chrome << EOF
REMOTE_DOMAIN=yourdomain
BACKEND_PORT=8000
EOF

# 2. 自動設定
./configure-remote.sh

# 3. Chrome読み込み
```

## 🛠️ トラブルシューティング

### よくある問題

**1. 拡張機能が接続できない**
```bash
# host_permissions確認
cat manifest.json | grep -A 10 host_permissions

# サーバー接続確認
curl http://yourdomain.com:8000/health
```

**2. 設定が反映されない**
```bash
# Chrome拡張機能を再読み込み
# chrome://extensions/ → 再読み込みボタン

# 設定をリセット
./reset-to-local.sh
./configure-remote.sh
```

**3. スクリプト実行権限エラー**
```bash
chmod +x configure-remote.sh
chmod +x reset-to-local.sh
```

### ログ確認

**拡張機能ログ:**
1. `chrome://extensions/` を開く
2. 拡張機能の「詳細」をクリック
3. 「拡張機能エラー」または「ビュー」→「バックグラウンド」

**ネットワーク確認:**
```bash
# ヘルスチェック
curl http://yourdomain.com:8501/health  # MCP Server
curl http://yourdomain.com:8000/health  # Backend API
```

## 🔒 セキュリティ考慮事項

### 設定ファイル管理
- `.env.chrome` は git追跡除外済み
- 本番環境の設定情報は適切に管理

### 権限管理
- `host_permissions` は必要最小限に制限
- リモートサーバーのみ追加許可

### HTTPS対応
```bash
# HTTPS環境での設定
USE_HTTPS=true
REMOTE_DOMAIN=yourdomain.com
```

## 🆘 サポート

問題が発生した場合:
1. トラブルシューティングセクションを確認
2. ログを確認
3. 設定をリセットして再試行
4. GitHub Issues でサポート要求

---

**注意**: この拡張機能はローカル・リモート両環境対応済みです。環境に応じて適切な設定スクリプトを使用してください。