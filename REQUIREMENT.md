# 要件定義

## 概要
Backlog APIドキュメントをWebページからMarkdown形式でダウンロードし、ローカルでDockerを使用してMCP（Model Context Protocol）経由でアクセス可能にするシステム

## 機能要件

### 1. Webページ取得機能
- Backlog API公式ドキュメント（https://developer.nulab.com/ja/docs/backlog/）からコンテンツを取得
- JINA Readerのような機能でWebページをMarkdown形式に変換
- 複数ページの一括取得対応

### 2. データ変換機能
- HTMLからMarkdown形式への変換
- APIドキュメント構造の保持
- コードサンプルの適切な整形

### 3. ローカル環境構築
- Dockerコンテナでの実行環境
- MCP（Model Context Protocol）対応
- ローカルでのドキュメント検索・参照機能

## 技術要件

### アーキテクチャ
- Docker環境での実行
- MCP対応のサーバー実装
- Markdown形式でのデータ保存

### 参考実装
- JINA Reader（https://jina.ai/ja/reader/）の機能を参考
- WebページからMarkdownへの変換機能

## 制約事項
- Backlog APIドキュメントの利用規約に準拠
- ローカル環境での実行に限定

## 詳細仕様

### 1. 対象ドキュメント範囲
- **取得対象**: Backlog API全ドキュメント（https://developer.nulab.com/ja/docs/backlog/）
- **含む内容**:
  - 全APIエンドポイント仕様
  - リクエスト/レスポンス例
  - 認証方法
  - エラーコード一覧
  - SDKドキュメント
- **除外**: 一般的な説明ページ、ナビゲーション要素

### 2. データ構造設計
```
backlog-api-docs/
├── authentication/          # 認証関連
├── endpoints/              # APIエンドポイント別
│   ├── issues/            # 課題API
│   ├── projects/          # プロジェクトAPI
│   ├── users/             # ユーザーAPI
│   └── ...
├── errors/                # エラーコード
├── sdks/                  # SDK情報
└── metadata.json          # 更新情報、インデックス
```

### 3. MCP機能仕様（開発者向け）
- **検索機能**: APIエンドポイント、パラメータ、エラーコードの検索
- **参照機能**: 特定APIの詳細仕様取得
- **一覧機能**: カテゴリ別API一覧表示
- **例示機能**: リクエスト/レスポンス例の取得
- **関連機能**: 関連APIの提案

### 4. 開発者ユースケース
- API仕様の確認: `GET /api/v2/issues` の仕様を知りたい
- パラメータ確認: 課題作成時の必須パラメータを知りたい
- エラー対応: エラーコード `40001` の意味を知りたい
- 実装例確認: 認証ヘッダーの設定方法を知りたい

### 6. MCPツール定義
```json
{
  "tools": [
    {
      "name": "search_backlog_api",
      "description": "Backlog APIドキュメントを検索",
      "parameters": {
        "query": "検索クエリ（エンドポイント名、機能名等）",
        "category": "カテゴリフィルタ（optional）"
      }
    },
    {
      "name": "get_api_spec",
      "description": "特定APIの詳細仕様を取得",
      "parameters": {
        "endpoint": "APIエンドポイント（例: GET /api/v2/issues）"
      }
    },
    {
      "name": "list_api_categories",
      "description": "APIカテゴリ一覧を取得"
    },
    {
      "name": "get_error_info",
      "description": "エラーコード情報を取得",
      "parameters": {
        "error_code": "エラーコード"
      }
    }
  ]
}
```

### 7. ファイル形式仕様
- **Markdownファイル**: 
  - フロントマター（YAML）でメタデータ
  - 構造化されたMarkdown本文
  - コードブロックでJSON例
- **インデックスファイル**: JSON形式で検索用メタデータ
- **設定ファイル**: Docker環境変数 + config.json

### 9. 環境設定仕様

#### .env ファイル構成
```bash
# JINA Reader API
JINA_API_KEY=your_jina_api_key_here

# オプション設定
SCRAPING_DELAY=1000          # リクエスト間隔（ms）
MAX_CONCURRENT_REQUESTS=3    # 同時リクエスト数
OUTPUT_DIR=/app/docs         # 出力ディレクトリ
LOG_LEVEL=INFO              # ログレベル

# MCP サーバー設定
MCP_PORT=58080               # MCPサーバーポート
MCP_HOST=0.0.0.0           # バインドアドレス
```

#### Docker 環境構成
```dockerfile
# .env ファイルをコンテナ内にコピー
COPY .env /app/.env

# 環境変数として読み込み
ENV $(cat /app/.env | xargs)
```

#### セキュリティ仕様
- **.env ファイル**: `.gitignore` に追加（リポジトリにコミットしない）
- **.env.example**: テンプレートファイルとして提供
- **APIキー検証**: 起動時にAPIキーの有効性をチェック
- **権限設定**: コンテナ内は非rootユーザーで実行

### 10. セットアップフロー
```bash
# 1. .env ファイル作成
cp .env.example .env
# APIキーを設定

# 2. Docker起動（一発セットアップ）
docker-compose up -d

# 3. 初回データ取得
docker-compose exec app python fetch_docs.py

# 4. MCP サーバー起動確認
curl http://localhost:58080/health
```

### 12. 起動時データ取得仕様

#### 自動取得フロー
```
MCP サーバー起動
    ↓
ローカルデータ存在チェック
    ↓
存在しない場合 → Webページから取得開始
    ↓
各ページに対してリトライ処理
    ↓
取得完了 → MCPサーバー開始
```

#### リトライ仕様
- **リトライ回数**: 最大3回
- **リトライ間隔**: 1秒、2秒、4秒（指数バックオフ）
- **タイムアウト**: 30秒/リクエスト
- **対象エラー**: 
  - HTTP 5xx エラー
  - タイムアウト
  - ネットワークエラー
- **非対象エラー**: HTTP 4xx（設定ミス等）

#### 進捗表示仕様
```bash
# 起動時の表示例
[INFO] Starting MCP server...
[INFO] Scanning Backlog API documentation structure...
[INFO] Found 47 pages to fetch
[INFO] Fetching documentation: [1/47] Authentication
[INFO] Fetching documentation: [2/47] Getting Started
[INFO] Fetching documentation: [3/47] Issues API - Overview
[INFO] Fetching documentation: [4/47] Issues API - Get Issue List
...
[INFO] Fetching documentation: [45/47] Error Codes
[INFO] Fetching documentation: [46/47] SDK - Python
[INFO] Fetching documentation: [47/47] SDK - JavaScript
[INFO] Documentation fetch completed (47/47 pages)
[INFO] MCP server ready on port 58080

# エラー発生時の表示例
[INFO] Fetching documentation: [23/47] Webhooks API
[WARN] Failed to fetch [23/47] Webhooks API (attempt 1/3): Timeout
[WARN] Failed to fetch [23/47] Webhooks API (attempt 2/3): Timeout  
[WARN] Failed to fetch [23/47] Webhooks API (attempt 3/3): Timeout
[ERROR] ✗ Skipped [23/47] Webhooks API after 3 failed attempts
[INFO] Fetching documentation: [24/47] Git API
...
[INFO] Documentation fetch completed (46/47 pages, 1 failed)
[INFO] MCP server ready on port 58080
```

#### 進捗管理
- **事前スキャン**: 全対象ページ数を事前に取得
- **リアルタイム表示**: `[現在/総数]` 形式で進捗表示
- **ページタイトル表示**: 取得中のページ名を表示
- **最終サマリー**: 成功/失敗の総数を表示

### 13. データ管理仕様

#### キャッシュ戦略
- **初回起動**: 必ずWebから取得
- **2回目以降**: ローカルデータを使用
- **強制更新**: 環境変数 `FORCE_REFRESH=true` で制御
- **データ有効期限**: 設定なし（手動更新のみ）

#### ファイル構成
```
/app/data/
├── .fetch_status.json     # 取得状況記録
├── authentication/        # 取得済みドキュメント
├── endpoints/
└── errors/
```

### 14. 更新されたセットアップフロー
```bash
# 1. .env ファイル作成
cp .env.example .env
# APIキーを設定

# 2. MCP サーバー起動（自動でデータ取得）
docker-compose up -d
# → 初回起動時に自動でWebページから取得開始
# → 取得完了後にMCPサーバー開始

# 3. 動作確認
curl http://localhost:58080/health

# 4. 強制更新（必要時のみ）
docker-compose exec app python -c "
import os; os.environ['FORCE_REFRESH']='true'
exec(open('src/fetch_docs.py').read())
"
```

### 15. 最終ファイル構成
```
backlog-api-doc/
├── .env.example           # 環境変数テンプレート
├── .env                   # 実際の環境変数（git ignore）
├── .gitignore            # .env を除外
├── docker-compose.yml    # Docker設定
├── Dockerfile           # コンテナ定義
├── requirements.txt     # Python依存関係
├── README.md            # セットアップ手順
├── REQUIREMENT.md       # 本仕様書
└── src/
    ├── fetch_docs.py    # ドキュメント取得（リトライ機能付き）
    ├── mcp_server.py    # MCPサーバー（起動時自動取得）
    ├── config.py        # 設定管理
    └── utils/
        ├── retry.py     # リトライ処理
        └── markdown.py  # Markdown変換
```

### 17. MCP Client 統合仕様

#### Docker実行コマンド
```bash
# MCP Client設定用の単一コマンド
docker run -d \
  --name backlog-api-mcp \
  --env-file .env \
  -p 58080:58080 \
  -v $(pwd)/data:/app/data \
  backlog-api-doc:latest

# または docker-compose での実行
docker-compose up -d backlog-api-mcp
```

#### MCP Client 設定例
```json
{
  "mcpServers": {
    "backlog-api": {
      "command": "docker",
      "args": [
        "run", "--rm",
        "--env-file", ".env",
        "-p", "58080:58080",
        "-v", "${PWD}/data:/app/data",
        "backlog-api-doc:latest"
      ],
      "env": {
        "DOCKER_HOST": "unix:///var/run/docker.sock"
      }
    }
  }
}
```

#### 簡易起動スクリプト
```bash
#!/bin/bash
# start-backlog-mcp.sh

# .env ファイル存在チェック
if [ ! -f .env ]; then
    echo "Error: .env file not found. Please copy .env.example to .env and configure."
    exit 1
fi

# データディレクトリ作成
mkdir -p ./data

# Docker コンテナ起動
docker run -d \
  --name backlog-api-mcp \
  --env-file .env \
  -p 58080:58080 \
  -v $(pwd)/data:/app/data \
  --restart unless-stopped \
  backlog-api-doc:latest

echo "Backlog API MCP server starting..."
echo "Check logs: docker logs -f backlog-api-mcp"
echo "Health check: curl http://localhost:58080/health"
```

### 18. 配布・セットアップ仕様

#### 配布方法
- **Docker Hub**: `backlog-api-doc:latest` として公開
- **GitHub Releases**: 設定ファイル一式をzip配布
- **ワンライナー**: 簡単セットアップ用のスクリプト提供

#### ワンライナーセットアップ
```bash
# 完全自動セットアップ
curl -sSL https://raw.githubusercontent.com/user/backlog-api-doc/main/install.sh | bash
```

#### install.sh の内容
```bash
#!/bin/bash
echo "Setting up Backlog API MCP Server..."

# 1. 設定ファイルダウンロード
curl -O https://raw.githubusercontent.com/user/backlog-api-doc/main/.env.example
curl -O https://raw.githubusercontent.com/user/backlog-api-doc/main/docker-compose.yml
curl -O https://raw.githubusercontent.com/user/backlog-api-doc/main/start-backlog-mcp.sh

# 2. 実行権限付与
chmod +x start-backlog-mcp.sh

# 3. 環境設定案内
echo "Setup completed!"
echo "1. Copy .env.example to .env and configure your API keys"
echo "2. Run: ./start-backlog-mcp.sh"
echo "3. Connect your MCP client to localhost:58080"
```

### 20. 高速起動のための代替アプローチ

#### オプション1: 事前ビルド済みデータ
```bash
# Dockerイメージに事前取得済みデータを含める
FROM python:3.11-slim
COPY pre-fetched-docs/ /app/data/  # 事前取得済み
COPY src/ /app/src/
# → 起動時間: 5秒以内
```

#### オプション2: バックグラウンド取得
```bash
# MCPサーバーを即座に起動、データは並行取得
[INFO] MCP server ready on port 58080 (0/47 pages available)
[INFO] Background fetch: [1/47] Authentication
[INFO] Background fetch: [5/47] Issues API
...
[INFO] Background fetch completed (47/47 pages available)
```

#### オプション3: 段階的取得
```bash
# 重要なページのみ優先取得（10秒以内）
Priority 1: Authentication, Getting Started (2 pages)
Priority 2: Issues, Projects, Users API (15 pages) 
Priority 3: その他のAPI (30 pages)

# 起動フロー
[INFO] MCP server starting...
[INFO] Fetching priority docs: [1/2] Authentication
[INFO] Fetching priority docs: [2/2] Getting Started  
[INFO] MCP server ready (2/47 pages, fetching remaining in background)
```

#### 推奨アプローチ: オプション2 + 3の組み合わせ
```bash
# 1. 即座にMCPサーバー起動
# 2. 重要ページを優先取得（10-15秒）
# 3. 残りをバックグラウンドで取得

[INFO] Starting MCP server...
[INFO] MCP server ready on port 58080
[INFO] Fetching essential docs: [1/17] Authentication
[INFO] Fetching essential docs: [2/17] Getting Started
...
[INFO] Essential docs ready (17/47 pages available)
[INFO] Background fetch: [18/47] Advanced APIs
...
[INFO] All documentation ready (47/47 pages available)
```

### 21. 確定仕様: 高速起動（即座起動 + 段階的取得）

#### 起動フロー
```bash
# Phase 1: 即座起動（5秒以内）
[INFO] Starting Backlog API MCP Server...
[INFO] MCP server ready on port 58080
[INFO] Status: 0/47 pages available (fetching essential docs...)

# Phase 2: 優先ページ取得（10-15秒）
[INFO] Priority fetch: [1/17] Authentication
[INFO] Priority fetch: [2/17] Getting Started  
[INFO] Priority fetch: [3/17] Issues API - Overview
[INFO] Priority fetch: [4/17] Issues API - Get List
[INFO] Priority fetch: [5/17] Issues API - Create
...
[INFO] Priority fetch: [17/17] Users API - Get User
[INFO] Essential documentation ready (17/47 pages available)

# Phase 3: バックグラウンド取得（並行実行）
[INFO] Background fetch: [18/47] Webhooks API
[INFO] Background fetch: [19/47] Git API
...
[INFO] All documentation ready (47/47 pages available)
```

#### 優先ページ定義
```python
PRIORITY_PAGES = [
    "authentication",           # 認証
    "getting-started",         # 開始方法
    "issues/overview",         # 課題API概要
    "issues/get-issue-list",   # 課題一覧取得
    "issues/get-issue",        # 課題取得
    "issues/add-issue",        # 課題作成
    "issues/update-issue",     # 課題更新
    "projects/get-project-list", # プロジェクト一覧
    "projects/get-project",    # プロジェクト取得
    "users/get-user-list",     # ユーザー一覧
    "users/get-user",          # ユーザー取得
    "error-codes",             # エラーコード
    # 基本的な開発で必要な17ページ
]
```

#### MCPツールの動作
```bash
# 優先ページ取得中
$ search_backlog_api("issues create")
→ "Fetching in progress... Found partial results (3/5 matches)"

# 全取得完了後  
$ search_backlog_api("issues create")
→ "Found 5 matches in documentation"
```

#### 運用時の想定動作
- **MCP接続**: 5秒以内で可能
- **基本開発作業**: 15秒後から全機能利用可能
- **完全機能**: 2-3分後に全ドキュメント利用可能
- **2回目以降**: 5秒以内で全機能利用可能（キャッシュ済み）
