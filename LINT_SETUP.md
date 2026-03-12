# Python Lint セットアップガイド

このドキュメントでは、Backlog API MCPサーバープロジェクトでのPython Lintシステムのセットアップ方法を説明します。

## 概要

このプロジェクトでは以下のLintツールを使用しています：

- **Ruff**: 高速なPython linter/formatter（Rust製）
- **Mypy**: 静的型チェッカー
- **Bandit**: セキュリティ脆弱性チェッカー
- **Pre-commit**: Git hookによる自動実行

## クイックスタート

### 1. 開発用依存関係のインストール

```bash
# 開発用パッケージをインストール
pip install -r requirements-dev.txt

# Pre-commit hookをインストール
pre-commit install
```

### 2. 基本的なLintコマンド

```bash
# すべてのLintチェックを実行
make lint

# コードフォーマットのみ実行
make format

# 型チェックのみ実行
make type-check

# セキュリティチェックのみ実行
make security
```

### 3. 自動修正

```bash
# 自動修正可能な問題を修正
make lint-fix

# または個別に実行
ruff check src/ --fix
ruff format src/
```

## 詳細セットアップ

### 仮想環境の使用（推奨）

```bash
# 仮想環境を作成
python -m venv venv

# 仮想環境を有効化
# macOS/Linux:
source venv/bin/activate
# Windows:
venv\\Scripts\\activate

# 依存関係をインストール
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Docker環境での使用

```bash
# Docker環境でLintを実行
make docker-lint

# または直接実行
docker run --rm -v $(pwd):/app -w /app python:3.11-slim bash -c "
  pip install -r requirements-dev.txt && 
  ruff check src/ && 
  ruff format --check src/ && 
  mypy src/
"
```

## 設定ファイル

### pyproject.toml
メインの設定ファイル。Ruff、Mypy、Banditの設定が含まれています。

### mypy.ini
Mypyの詳細設定。段階的な型チェック導入のための設定が含まれています。

### .pre-commit-config.yaml
Pre-commit hookの設定。コミット前に自動的にLintチェックが実行されます。

### .editorconfig
エディタ間での一貫した設定（インデント、改行コードなど）。

## IDE統合

### VS Code

1. Ruff拡張機能をインストール：
   ```
   code --install-extension charliermarsh.ruff
   ```

2. 設定ファイル（`.vscode/settings.json`）を作成：
   ```json
   {
     "python.defaultInterpreterPath": "./venv/bin/python",
     "ruff.enable": true,
     "ruff.organizeImports": true,
     "editor.formatOnSave": true,
     "editor.codeActionsOnSave": {
       "source.organizeImports": true,
       "source.fixAll.ruff": true
     }
   }
   ```

### その他のエディタ

- **PyCharm**: Ruffプラグインを使用
- **Vim/Neovim**: ALE、coc.nvim、またはnvim-lspconfig
- **Emacs**: flycheck-ruff

## Agent Hook統合

Kiro Agent Hookでの自動実行用スクリプト：

```bash
# ファイル変更時に自動実行
./scripts/lint.sh

# Docker環境での実行
./scripts/docker-lint.sh
```

## トラブルシューティング

### よくある問題

#### 1. Ruffが見つからない
```bash
# 解決方法: 開発用依存関係を再インストール
pip install -r requirements-dev.txt
```

#### 2. Pre-commit hookが動作しない
```bash
# 解決方法: Pre-commit hookを再インストール
pre-commit uninstall
pre-commit install
```

#### 3. 型チェックエラーが多すぎる
```bash
# 解決方法: 段階的導入のため、一時的に無視
# mypy.iniで disallow_untyped_defs = false に設定済み
```

#### 4. Docker環境でのパーミッションエラー
```bash
# 解決方法: ユーザーIDを指定してDockerを実行
docker run --rm -v $(pwd):/app -w /app --user $(id -u):$(id -g) python:3.11-slim bash -c "..."
```

### ログの確認

```bash
# Lintエラーの詳細を確認
ruff check src/ --verbose

# 型チェックの詳細を確認
mypy src/ --verbose

# セキュリティチェックの詳細を確認
bandit -r src/ -v
```

## カスタマイズ

### ルールの追加・除外

`pyproject.toml`の`[tool.ruff]`セクションで設定：

```toml
[tool.ruff]
select = ["E", "F", "W", "I", "N", "UP", "B", "A", "C4", "T20"]
ignore = ["E501", "B008"]  # 除外するルール
```

### 型チェックの厳格化

段階的に型チェックを厳格化する場合：

1. `mypy.ini`で`disallow_untyped_defs = true`に変更
2. `disallow_incomplete_defs = true`に変更
3. `strict = true`に変更

## 継続的な品質管理

### 定期的なメンテナンス

```bash
# 設定ファイルの更新確認
pre-commit autoupdate

# 依存関係の更新
pip list --outdated
```

### チーム開発での注意点

1. **設定ファイルの共有**: すべての設定ファイルをバージョン管理に含める
2. **段階的導入**: 厳格なルールは段階的に導入する
3. **ドキュメント更新**: ルール変更時はこのドキュメントも更新する

## 参考リンク

- [Ruff公式ドキュメント](https://docs.astral.sh/ruff/)
- [Mypy公式ドキュメント](https://mypy.readthedocs.io/)
- [Pre-commit公式ドキュメント](https://pre-commit.com/)
- [Bandit公式ドキュメント](https://bandit.readthedocs.io/)

## サポート

問題が発生した場合は、以下を確認してください：

1. このドキュメントのトラブルシューティングセクション
2. 各ツールの公式ドキュメント
3. プロジェクトのIssueトラッカー