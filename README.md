# GovBid - 九州・山口 入札情報収集システム

九州・山口地域の自治体から「広報」「プロモーション」「イベント企画運営」に関連する公募・入札案件を自動収集し、一覧表示するWebアプリケーションです。

## 機能

- 12自治体（9県庁 + 3政令市）の入札・公募情報を自動収集
- キーワードフィルタリング（広報/プロモーション/イベント）
- 案件一覧表示・検索・フィルタリング
- CSVエクスポート
- **落札企業抽出**（自治体サイトの結果ページを巡回し、落札企業を抽出・一覧表示）
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

### 落札企業抽出

公募ページは入札後に削除されることが多く（実測で404が半数前後）、落札情報は別の「結果ページ」
（`〇〇_kekka.html` / 結果PDF / 契約結果一覧 等）に公表される。この機能は案件URLの親ディレクトリ・
サイトルート・入札公募ハブページを起点に**同一ドメイン内を巡回**して結果ページを見つけ、落札企業を抽出する。

画面の「落札結果」タブから実行・閲覧できるほか、APIでも実行できる：

```bash
# 抽出対象の件数を事前確認（未確認・上限金額が WINNER_MIN_AMOUNT 以上・公告URLあり）
curl "http://localhost:8000/api/winner-extract/targets"

# 落札企業抽出を実行（バックグラウンド）
curl -X POST http://localhost:8000/api/winner-extract \
  -H "Content-Type: application/json" \
  -d '{"municipality": "福岡県", "min_amount": 5000000}'

# 進捗確認
curl http://localhost:8000/api/winner-extract/status

# 結果一覧（落札企業名は前株/後株・（株）等の表記揺れを吸収して検索できる）
curl "http://localhost:8000/api/results?company=九州広告&per_page=20"
```

毎月15日 6:00 JST に自動実行される（手動トリガーと同じコードパス）。

**抽出の設計方針（誤検出対策）:**

- 「落札者 / 受託者 / 契約の相手方」等の**勝者ラベル直後**の企業名だけを採る。次点・参加業者リスト、
  募集要項の共同企業体ルール文は除外する
- 採用するのは3経路のみ ①`title`/`h1`-`h4` に案件名がある（ページ主題）②表のヘッダに勝者列がある場合の
  当該行セル ③同一ブロック(`tr`/`li`/`p`)内に案件名と勝者ラベルが共存。
  ページ全文からの緩い抽出は、ナビの新着リストに案件名が載るだけで別案件の落札者を拾うため行わない
- 案件名の部分一致は core の60%以上（最低12文字）を要求し、案件名に年度がある場合は本文に同じ年度を要求する
  （令和6年度の案件で令和5年度の旧ページを拾う事故を防ぐ）
- 落札金額は「落札金額 / 契約金額」等の明示ラベルがある場合のみ取得する（推測しない）
- 重複除去は「案件名core＋企業名」と「結果URL＋企業名」の両方で行う（同一URLの別表記案件の二重計上を防ぐ）
- 元案件に紐付かないもの（orphan）も保存・表示する

**既知の制約:**

- 検索エンジン（DuckDuckGo/Bing/Google/Yahoo）はボット判定・レート制限で実用にならないため使用していない
- 多くの自治体サイトはデータセンターIP/UAに404を返すため、クラウド実行時は取得率が下がる
- `kiji00xxxxx/index.html` 型CMSやID型URLのサイトは親ディレクトリが手がかりにならず検出率が低い
- 結果がPDFのみの自治体は PyMuPDF（requirements.txt に同梱）で本文を読む。未導入環境ではPDFをスキップする

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
| WINNER_MIN_AMOUNT | 落札企業抽出の対象とする上限金額の下限 | 5000000 |
| WINNER_CRAWL_DELAY_SECONDS | 結果ページ巡回の間隔（同一ドメイン） | 0.7 |
| WINNER_MAX_PAGES_PER_DOMAIN | 1ドメインあたりの取得ページ上限 | 250 |
| WINNER_MAX_DOMAINS_CONCURRENT | 同時に巡回するドメイン数 | 8 |
| WINNER_CACHE_DIR | 取得ページのキャッシュ先（空ならメモリのみ） | (空) |

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
│   │       ├── filter_service.py    # カテゴリ分類・除外フィルタ
│   │       ├── scraper_service.py   # 入札案件スクレイピング
│   │       ├── winner_extract.py    # 落札企業の抽出コア（勝者ラベル・企業名正規化）
│   │       ├── winner_crawler.py    # 結果ページのサイト内クロール
│   │       └── winner_service.py    # 落札企業抽出のオーケストレーション
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
