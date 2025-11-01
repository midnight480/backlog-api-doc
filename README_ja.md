# Backlog API MCP Server

Backlog APIドキュメントをローカルでアクセス可能にするModel Context Protocol (MCP) サーバーです。公式のBacklog APIドキュメントサイトから自動的にドキュメントを取得し、Markdown形式に変換して、MCP経由でAIアシスタントや開発ツールから簡単に利用できるようにします。

## 機能

- 🔄 **自動ドキュメント取得**: Backlog APIドキュメントをWebから自動取得
- 📝 **Markdown変換**: JINA Readerを使用してHTMLドキュメントをMarkdown形式に変換
- 🐳 **Dockerサポート**: Dockerとdocker-composeによる簡単なデプロイ
- ⚡ **高速起動**: 段階的なドキュメント読み込みにより、サーバーを即座に利用可能
- 🔍 **検索・クエリ**: APIエンドポイント、パラメータ、エラーコードの検索
- 🔁 **リトライ機能**: 指数バックオフによる堅牢なリトライメカニズム
- 📊 **ヘルスモニタリング**: 監視用のヘルスチェックエンドポイント

## クイックスタート

### 前提条件

- DockerおよびDocker Composeがインストールされていること
- JINA Reader APIキー ([こちらで取得](https://jina.ai/reader))

### セットアップ

1. **リポジトリをクローン**
```bash
git clone <repository-url>
cd backlog-api-doc
```

2. **環境変数ファイルを作成**
```bash
cp .env.example .env
```

3. **APIキーを設定**
`.env`を編集してJINA Reader APIキーを設定:
```bash
JINA_API_KEY=your_jina_api_key_here
```

4. **サーバーを起動**
```bash
docker compose up -d
```

5. **サーバーの動作確認**
```bash
curl http://localhost:58080/health
```

## 設定

### 環境変数

| 変数名 | 説明 | デフォルト |
|--------|------|-----------|
| `JINA_API_KEY` | JINA Reader APIキー（必須） | - |
| `SCRAPING_DELAY` | リクエスト間の遅延（ミリ秒） | 1000 |
| `MAX_CONCURRENT_REQUESTS` | 最大同時リクエスト数 | 3 |
| `OUTPUT_DIR` | ドキュメント出力ディレクトリ | `/app/data` |
| `LOG_LEVEL` | ログレベル | `INFO` |
| `MCP_PORT` | MCPサーバーポート | 58080 |
| `MCP_HOST` | MCPサーバーホスト | `0.0.0.0` |
| `FORCE_REFRESH` | ドキュメントの強制更新 | `false` |

## MCP APIエンドポイント

### ヘルスチェック
```bash
GET /health
```

サーバーのステータス、初期化状態、ドキュメントの利用可能性を返します。

### APIドキュメント検索
```bash
POST /mcp/search_backlog_api
Content-Type: application/json

{
  "query": "issues create",
  "category": "endpoints"  // オプション
}
```

### API仕様取得
```bash
POST /mcp/get_api_spec
Content-Type: application/json

{
  "endpoint": "GET /api/v2/issues"
}
```

### APIカテゴリ一覧取得
```bash
GET /mcp/list_api_categories
```

### エラー情報取得
```bash
POST /mcp/get_error_info
Content-Type: application/json

{
  "error_code": "40001"
}
```

## ドキュメント構造

取得されたドキュメントは以下のように整理されます:

```
data/
├── authentication/     # 認証ドキュメント
├── endpoints/         # APIエンドポイントドキュメント
│   ├── issues/       # 課題API
│   ├── projects/     # プロジェクトAPI
│   └── users/        # ユーザーAPI
├── errors/           # エラーコード
└── sdks/             # SDKドキュメント
```

## 起動フロー

サーバーは高速起動のため、段階的な読み込み戦略を実装しています:

1. **フェーズ1 (0-5秒)**: サーバーが即座に起動
2. **フェーズ2 (5-15秒)**: 重要ドキュメントページを取得（17の優先ページ）
3. **フェーズ3 (バックグラウンド)**: 残りのドキュメントをバックグラウンドで取得

### 優先ページ

以下のページが最初に取得され、即座に利用可能になります:

- 認証
- はじめに
- 課題API（概要、一覧取得、取得、作成、更新）
- プロジェクトAPI（一覧取得、取得）
- ユーザーAPI（一覧取得、取得）
- エラーコード

## MCP Client設定

このサーバーはClaude Desktop、Cursor、その他のAIアシスタントなどのMCP対応クライアントで使用できます。接続方法は2つあります:

### オプション1: HTTPベース接続（直接）

HTTPトランスポートをサポートするクライアントの場合:

```json
{
  "mcpServers": {
    "backlog-api": {
      "url": "http://localhost:58080",
      "description": "Backlog API Documentation MCP Server",
      "transport": "http"
    }
  }
}
```

完全なツール定義を含む例は `mcp-client-config.json` を参照してください。

### オプション2: stdioベース接続（推奨）

ほとんどのMCPクライアント（Claude Desktopなど）はstdioトランスポートを使用します。提供されているstdioラッパーを使用してください:

**Dockerを使用（推奨 - ローカルの依存関係不要）:**

```json
{
  "mcpServers": {
    "backlog-api": {
      "command": "docker",
      "args": [
        "exec",
        "-i",
        "backlog-api-mcp",
        "python",
        "/app/mcp-server-stdio.py"
      ],
      "env": {}
    }
  }
}
```

**ローカルPythonを使用（httpxのインストールが必要）:**

```json
{
  "mcpServers": {
    "backlog-api": {
      "command": "python3",
      "args": [
        "/absolute/path/to/backlog-api-doc/mcp-server-stdio.py"
      ],
      "env": {}
    }
  }
}
```

**注意**: stdioラッパーを起動する前に、HTTPサーバーが `http://localhost:58080` で実行されていることを確認してください。ローカルPythonの場合、依存関係をインストール: `pip install httpx`（必要に応じて`--break-system-packages`を使用）。


### Claude Desktop設定

Claude Desktopの場合、設定ファイルを編集してください:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`  
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

**推奨: Dockerを使用（ローカルのPython依存関係不要）**

```json
{
  "mcpServers": {
    "backlog-api": {
      "command": "docker",
      "args": [
        "exec",
        "-i",
        "backlog-api-mcp",
        "python",
        "/app/mcp-server-stdio.py"
      ]
    }
  }
}
```

**代替: ローカルPythonを使用（httpxが必要）**

```json
{
  "mcpServers": {
    "backlog-api": {
      "command": "python3",
      "args": [
        "/absolute/path/to/backlog-api-doc/mcp-server-stdio.py"
      ]
    }
  }
}
```

**重要**: 
- Docker方式を使用する場合、Dockerコンテナ`backlog-api-mcp`が実行中であることを確認してください
- ローカルPython方式の場合、httpxをインストール: `pip3 install httpx`（必要に応じて`--break-system-packages`フラグを使用）

設定後、Claude Desktopを再起動してください。

### Amazon Q設定

Amazon Q Developerの場合、設定ファイルを編集してください:

**macOS/Linux**: `~/.aws/amazonq/mcp.json`

**Dockerを使用:**

```json
{
  "mcpServers": {
    "backlog-api": {
      "command": "docker",
      "args": [
        "exec",
        "-i",
        "backlog-api-mcp",
        "python",
        "/app/mcp-server-stdio.py"
      ]
    }
  }
}
```

**Amazon Qのトラブルシューティング:**

「Transport closed」エラーが表示される場合:
1. Dockerコンテナが実行中であることを確認: `docker compose ps`
2. ラッパーを手動でテスト: `echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0.0"}}}' | docker exec -i backlog-api-mcp python /app/mcp-server-stdio.py`
3. ログを確認: `docker compose logs backlog-api-mcp`
4. Amazon QからDockerデーモンにアクセスできることを確認

完全な例は `mcp-config-amazon-q.json` を参照してください。

## 使用例

### curlを使用（HTTP API）

```bash
# "issues"関連のAPIを検索
curl -X POST http://localhost:58080/mcp/search_backlog_api \
  -H "Content-Type: application/json" \
  -d '{"query": "issues create"}'

# 特定のAPI仕様を取得
curl -X POST http://localhost:58080/mcp/get_api_spec \
  -H "Content-Type: application/json" \
  -d '{"endpoint": "GET /api/v2/issues"}'

# APIカテゴリ一覧を取得
curl http://localhost:58080/mcp/list_api_categories

# エラー情報を取得
curl -X POST http://localhost:58080/mcp/get_error_info \
  -H "Content-Type: application/json" \
  -d '{"error_code": "40001"}'
```

### MCP Clientを使用（stdio）

設定後、MCPクライアントでツールを直接使用できます:

- `search_backlog_api`: APIドキュメントを検索
- `get_api_spec`: 詳細なAPI仕様を取得
- `list_api_categories`: 利用可能なAPIカテゴリを一覧表示
- `get_error_info`: エラーコード情報を取得

### 強制更新

すべてのドキュメントを強制更新する場合:

```bash
docker-compose exec backlog-api-mcp python -c "
import os
os.environ['FORCE_REFRESH']='true'
exec(open('src/fetch_docs.py').read())
"
```

または`.env`で`FORCE_REFRESH=true`を設定して再起動:

```bash
docker-compose restart
```

## 開発

### プロジェクト構造

```
backlog-api-doc/
├── src/
│   ├── fetch_docs.py      # ドキュメント取得ロジック
│   ├── mcp_server.py      # MCPサーバー実装
│   ├── config.py          # 設定管理
│   └── utils/
│       ├── retry.py       # リトライユーティリティ
│       └── markdown.py    # Markdown変換
├── mcp-server-stdio.py    # MCPクライアント用stdioラッパー
├── mcp-client-config.json # MCPクライアント設定例
├── mcp-config-claude.json # Claude Desktop設定例
├── docker-compose.yml     # Docker Compose設定
├── Dockerfile             # Dockerイメージ定義
├── requirements.txt       # Python依存関係
└── README_ja.md          # このファイル
```

### ローカルビルド

```bash
# Dockerイメージをビルド
docker build -t backlog-api-doc:latest .

# コンテナを実行
docker run -d \
  --name backlog-api-mcp \
  --env-file .env \
  -p 58080:58080 \
  -v $(pwd)/data:/app/data \
  backlog-api-doc:latest
```

### テスト実行

```bash
# サーバーヘルスチェック
curl http://localhost:58080/health

# 検索機能のテスト
curl -X POST http://localhost:58080/mcp/search_backlog_api \
  -H "Content-Type: application/json" \
  -d '{"query": "authentication"}'
```

## トラブルシューティング

### サーバーが起動しない

1. `.env`で`JINA_API_KEY`が設定されているか確認
2. Dockerが実行中か確認: `docker ps`
3. ログを確認: `docker-compose logs backlog-api-mcp`

### ドキュメントが取得されない

1. JINA APIキーが有効か確認
2. ネットワーク接続を確認
3. ログで具体的なエラーを確認: `docker-compose logs -f`

### ポートが既に使用中

`.env`でポートを変更:
```bash
MCP_PORT=8081
```

## ライセンス

このプロジェクトはローカル使用のためにそのまま提供されています。Backlog APIドキュメントの利用規約に準拠していることを確認してください。

## 貢献

貢献を歓迎します！プルリクエストを自由に提出してください。

## リンク

- [Backlog APIドキュメント](https://developer.nulab.com/ja/docs/backlog/)
- [JINA Reader](https://jina.ai/reader)
- [Model Context Protocol](https://modelcontextprotocol.io/)

---

📖 [English README](README.md)
