# GovBid - 九州・山口 入札情報収集システム

九州・山口地域の自治体から「広報」「プロモーション」「イベント企画運営」に関連する公募・入札案件を自動収集し、一覧表示するWebアプリケーションです。

## 機能

- 12自治体（9県庁 + 3政令市）の入札・公募情報を自動収集
- キーワードフィルタリング（広報/プロモーション/イベント）
- 案件一覧表示・検索・フィルタリング
- CSVエクスポート
- 新着案件のメール通知
- ユーザー認証（登録・ログイン）

## 対象自治体

**県庁:**
- 福岡県、佐賀県、長崎県、熊本県、大分県、宮崎県、鹿児島県、沖縄県、山口県

**政令市:**
- 福岡市、北九州市、熊本市

## 技術スタック

### バックエンド
- Python 3.11+
- FastAPI
- SQLAlchemy (SQLite)
- httpx + BeautifulSoup (スクレイピング)
- APScheduler (定期実行)

### フロントエンド
- Next.js 14 (App Router)
- TypeScript
- Tailwind CSS
- React Query

## セットアップ

### 必要なもの
- Docker & Docker Compose
- または Node.js 20+ と Python 3.11+

### Docker を使用する場合

```bash
# コンテナの起動
docker-compose up -d

# フロントエンド: http://localhost:3000
# バックエンドAPI: http://localhost:8000
# API ドキュメント: http://localhost:8000/docs
```

### ローカル開発

**バックエンド:**

```bash
cd backend

# 仮想環境の作成
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存関係のインストール
pip install -r requirements.txt

# 環境変数の設定
cp .env.example .env
# .env を編集

# 開発サーバーの起動
uvicorn app.main:app --reload
```

**フロントエンド:**

```bash
cd frontend

# 依存関係のインストール
npm install

# 開発サーバーの起動
npm run dev
```

## 使い方

1. http://localhost:3000 にアクセス
2. 新規登録またはログイン
3. 案件一覧が表示されます
4. フィルターや検索で絞り込み
5. CSVエクスポートでデータをダウンロード

### 手動スクレイピング

API経由で手動スクレイピングを実行できます：

```bash
# 全自治体をスクレイピング
curl -X POST http://localhost:8000/api/scrape \
  -H "Authorization: Bearer YOUR_TOKEN"

# 特定の自治体のみ
curl -X POST "http://localhost:8000/api/scrape?municipality=福岡県" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 環境変数

**バックエンド (.env):**

| 変数名 | 説明 | デフォルト |
|--------|------|----------|
| SECRET_KEY | JWT署名用シークレットキー | (必須) |
| DATABASE_URL | データベース接続URL | sqlite+aiosqlite:///./govbid.db |
| RESEND_API_KEY | メール送信用APIキー | (任意) |
| EMAIL_FROM | 送信元メールアドレス | noreply@govbid.local |
| CORS_ORIGINS | 許可するオリジン | ["http://localhost:3000"] |
| SCRAPE_INTERVAL_HOURS | 自動スクレイピング間隔 | 24 |

**フロントエンド (.env.local):**

| 変数名 | 説明 | デフォルト |
|--------|------|----------|
| NEXT_PUBLIC_API_URL | バックエンドAPIのURL | http://localhost:8000 |

## ディレクトリ構造

```
govbid/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPIエントリーポイント
│   │   ├── config.py         # 設定
│   │   ├── database.py       # DB接続
│   │   ├── models.py         # SQLAlchemyモデル
│   │   ├── schemas.py        # Pydanticスキーマ
│   │   ├── scheduler.py      # 定期実行スケジューラ
│   │   ├── api/
│   │   │   ├── routes.py     # APIエンドポイント
│   │   │   └── deps.py       # 依存性注入
│   │   ├── scrapers/         # 各自治体のスクレイパー
│   │   └── services/         # ビジネスロジック
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/              # Next.js App Router
│   │   ├── components/       # Reactコンポーネント
│   │   ├── lib/              # ユーティリティ
│   │   └── types/            # TypeScript型定義
│   └── package.json
└── docker-compose.yml
```

## 注意事項

- 各自治体サイトの構造変更により、スクレイピングが失敗する可能性があります
- 過度なアクセスを避けるため、リクエスト間隔を設けています
- 本番運用時は、適切なセキュリティ設定を行ってください

## ライセンス

MIT
