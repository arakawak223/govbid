# 落札企業情報スクレイピング機能 要件定義案 v0.1

作成日: 2026-05-07
作成者: Claude (代筆)
ステータス: ドラフト（ユーザーレビュー待ち）

---

## 1. 背景と目的

### 1.1 背景
現行のgovbidアプリは **「募集中の入札案件」** をスクレイピングし、媒体・PR系業務に絞ってメディア企業に届けている（63自治体・約180件/日）。一方で、媒体企業の意思決定を支える上で実は **「過去の落札結果」** こそが最も価値の高い情報源である：

- **競合インテリジェンス**: 同種案件をどの代理店・媒体社が獲っているか
- **価格ベンチマーク**: 落札金額の相場感（次回入札の値付け判断材料）
- **見込み顧客発掘**: 落札企業=その自治体と繋がりを持つ事業者→協業先候補
- **市場動向把握**: 県別・カテゴリ別の市場シェア・トレンド分析
- **自社の振り返り**: 自社が参加した案件の結果トラッキング

### 1.2 目的
2026年4月度（FY2026Q1）以降、登録済み63自治体の **入札・プロポーザル結果（落札企業・落札金額・入札参加者）** をスクレイピングし、現行アプリと統合された形で提供する。

### 1.3 非目的（スコープ外）
- 国・独立行政法人・特殊法人の入札結果（地方自治体のみ）
- 工事系入札結果（媒体PRと無関係）
- 過去（2026年3月以前）の落札情報の遡及収集 — 必要に応じて別途検討
- 落札金額の予測・推奨機能（将来的なAI拡張で別議論）

---

## 2. ユーザーストーリー

| # | ロール | 〜したい | 〜のために |
|---|---|---|---|
| US-1 | 営業企画 | 月別×自治体別×カテゴリ別の落札一覧を一覧表示したい | 月次の競合動向を把握する |
| US-2 | 経営者 | 特定企業（自社/競合）の落札履歴を検索したい | 競合分析・自社実績の整理 |
| US-3 | 提案担当 | 元の公告（募集中時）と落札結果を紐づけて見たい | 「あの案件は誰が獲ったか」を追える |
| US-4 | 営業企画 | 落札一覧をCSVエクスポートしたい | 経営会議の資料に転用 |
| US-5 | 経営者 | 自社が落札した案件をハイライト/通知してほしい | 受注確度の事後確認 |
| US-6 | アナリスト | 同一カテゴリ内の落札金額分布を見たい | 価格帯のレンジ感を掴む |

---

## 3. スコープ

### 3.1 対象自治体（Phase 1）
現行スクレイパー63自治体のうち、**結果ページが整備されている上位10自治体** をMVPとする：

| Tier | 自治体 | 想定難易度 | 想定件数/月 |
|---|---|---|---|
| S | 福岡県 / 福岡市 | 中（電子入札システムあり） | 〜100 |
| S | 北九州市 | 中 | 〜50 |
| A | 沖縄県 / 大分県 | 中 | 〜80 |
| A | 鹿児島県 / 長崎県 / 熊本県 / 佐賀県 / 宮崎県 | 中 | 〜150 |

Phase 2以降で残り53自治体を追加（後述「6. 段階的リリース計画」）。

### 3.2 抽出対象データの範囲【ユーザー決定 2026-05-07】
- **入札方式**: 一般競争入札 / 指名競争入札 / 公募型プロポーザル / 随意契約（公表されている範囲で）
- **金額帯**: 全件（自治体の公表基準に従う。100万円未満は非公表の自治体多数）
- **業種**: **【Q1=B】全件取得し後処理でカテゴリ分類**。表示・通知時に媒体PR系（現行29カテゴリ）でフィルタ。カテゴリ未分類のものは「その他」として保持し、将来のキーワード追加で再分類可能とする。

### 3.3 期間【ユーザー決定 2026-05-07】
- **対象基準**: **【Q2=A】開札日（落札日）が対象月のもの**を抽出単位とする
- **MVP（Phase 1）**: 2026年4月分（4/1〜4/30開札分）の一括取得 — **サンプル的に実施し運用感を確認**
- **最終ゴール**: 毎月の開札状況を調査・とりまとめる月次自動運用（毎月15日 6:00 JST、前月分取得）
- **設計方針**: MVPの段階から「月次運用」を前提としたアーキテクチャで実装し、4月分の手動トリガーが将来の月次バッチと同じコードパスで動くようにする（再設計を発生させない）

---

## 4. 機能要件（FR）

### FR-1: 落札情報スクレイピング
- **FR-1.1** 各自治体の入札結果ページを定期巡回し、落札情報を抽出する
- **FR-1.2** 抽出項目：
  - 必須: `案件名`, `自治体`, `落札企業名`, `落札金額`, `落札日（開札日）`, `公告/結果URL`
  - 推奨: `予定価格`, `入札参加者数`, `入札方式`, `契約日`, `税込/税抜区分`
  - 任意: `入札参加者全員の社名・札入れ価格`, `業種コード`, `落札率`
- **FR-1.3** PDF公表のみの自治体は **Phase 2** で対応（pdfplumber使用）。Phase 1ではHTML系のみ。
- **FR-1.4** 既存の `EXCLUDE_PATTERNS` には影響を与えない（落札結果ページはこれまで除外していたため、新たな取得経路が必要）

### FR-2: 元案件との紐付け（マッチング）
- **FR-2.1** 落札情報を `bids` テーブルの該当案件と紐付ける（FK: `bid_id`）
- **FR-2.2** マッチング戦略（強い順）:
  1. **公告URL完全一致** — 結果ページに元公告URLが記載されているケース
  2. **案件番号一致** — 整数IDがある場合
  3. **タイトル類似度 ≥ 90%（rapidfuzz）+ 同自治体 + 公告日±30日** — 自動マッチ
  4. **タイトル類似度 80–89%** — 候補としてフラグ立て、人手レビュー対象
  5. **マッチ無し** — orphan として保存（元案件未スクレイプ・スクレイパー漏れ）
- **FR-2.3** orphan の落札情報も保存・表示する（4月以前の取りこぼし可視化のため）

### FR-3: カテゴリ分類
- **FR-3.1** 落札情報のタイトルに対しても `categorize_bid()` を適用し、現行29カテゴリに分類
- **FR-3.2** カテゴリ未分類のものは「その他」として保存（除外しない — 全体俯瞰のため）

### FR-4: 表示・検索
- **FR-4.1** 新規ページ `/results` を追加し、以下のフィルタを提供:
  - 期間（年月）
  - 自治体（複数選択）
  - カテゴリ
  - 落札企業名（部分一致検索）
  - 落札金額レンジ
- **FR-4.2** 一覧表示項目: 自治体 / 案件名 / 落札企業 / 落札金額 / 落札日 / カテゴリ / 元公告へのリンク
- **FR-4.3** 詳細画面: 全入札参加者、価格分布、関連する元公告（紐付いている場合）
- **FR-4.4** 既存の入札一覧画面から「この案件の落札結果を見る」リンクで遷移可能

### FR-5: エクスポート
- **FR-5.1** 検索結果をCSV出力（既存の `govbid_export_*.csv` と同一フォーマット系）
- **FR-5.2** Excel(xlsx) 出力もサポート（推奨：openpyxl）

### FR-6: スケジューリング
- **FR-6.1** 月次バッチ: 毎月15日 6:00 JST に前月分を取得（既存スケジューラを拡張）
- **FR-6.2** 手動トリガー: 管理画面から自治体・期間指定で再取得可能
- **FR-6.3** 初回 2026/4 月分は手動トリガーで一括投入

### FR-7: ウォッチ企業マスタ【MVP】
- **FR-7.1** ユーザーごとに「ウォッチ企業リスト」を登録可能とする（自社/競合A/競合B等のラベル付き）
- **FR-7.2** ウォッチ企業の登録・編集・削除UIを提供（ログイン必須）
- **FR-7.3** 企業名は **部分一致（LIKE）でマッチ**。MVPでは「株式会社○○」「(株)○○」「㈱○○」等の表記揺れは正規化せず、ユーザーが必要なら別エントリで複数登録（Phase 3で名寄せ実装）
- **FR-7.4** 検索画面に「ウォッチ企業のみ表示」フィルタを追加
- **FR-7.5** 既存案件詳細画面に「落札企業はウォッチ対象です」バッジ表示

### FR-8: 通知【MVP】
- **FR-8.1** **即時通知**: ウォッチ企業の落札情報がスクレイプされた時、登録ユーザーへメール送信（既存Resend基盤を流用）
- **FR-8.2** **月次サマリー**: 毎月17日6:00 JST（落札スクレイプの2日後）に全ユーザーへ送信。内容:
  - 前月の落札件数 TOP10 企業
  - 自治体別ランキング（件数・総額）
  - 自分のウォッチ企業の前月実績（落札件数・総額）
  - 媒体PR系カテゴリの落札動向ハイライト
- **FR-8.3** ユーザーが個別にON/OFF設定可能（既存の `notification_enabled` を流用、または別フラグ追加）

### FR-9: 公開アクセス【MVP】
- **FR-9.1** `/results` 一覧画面・落札情報の閲覧APIは **未ログインでもアクセス可能**
- **FR-9.2** ウォッチ企業の登録・編集、通知設定、CSVエクスポートは **ログイン必須**
- **FR-9.3** 既存の入札一覧（募集中案件）は現行通りログイン必須を維持

---

## 5. 非機能要件（NFR）

| ID | 項目 | 内容 |
|---|---|---|
| NFR-1 | 性能 | 月次バッチは2時間以内に完了（Render Free Tier考慮） |
| NFR-2 | 可用性 | 既存のスクレイパー処理に影響しない（並走または時間帯分離） |
| NFR-3 | エラー耐性 | 1自治体の失敗が全体を止めない（per-scraper try/except） |
| NFR-4 | アクセスマナー | 既存通り `request_delay_seconds` 適用、各自治体への負荷を抑制 |
| NFR-5 | データ保持 | 過去2年分はDB保持。それ以前はarchive table or CSV化 |
| NFR-6 | 監視 | 自治体別の取得件数・失敗率をログ出力。0件続発時は警告 |
| NFR-7 | 法令・倫理 | 入札結果は公開情報のため取得自体に問題なし。ただし robots.txt 遵守、会社名の表示は公表情報のみに限定 |

---

## 6. データモデル

### 6.1 新規テーブル：`bid_results`

```python
class BidResult(Base):
    __tablename__ = "bid_results"

    id: Mapped[str]                      # UUID
    bid_id: Mapped[str | None]           # FK to bids.id (nullable=True ← orphan許容)

    # 基本情報
    municipality: Mapped[str]            # 自治体名
    title: Mapped[str]                   # 結果ページに記載された案件名
    bid_method: Mapped[str | None]       # "一般競争入札"等

    # 落札情報
    winning_company: Mapped[str]         # 落札者名
    winning_company_address: Mapped[str | None]
    award_amount: Mapped[int | None]     # 落札金額（円）
    is_tax_included: Mapped[bool | None] # 税込フラグ
    reserve_price: Mapped[int | None]    # 予定価格（公表時のみ）
    award_rate: Mapped[float | None]     # 落札率（落札÷予定）

    # 日付
    award_date: Mapped[date]             # 開札日 / 落札日
    contract_date: Mapped[date | None]   # 契約日
    fiscal_year: Mapped[int | None]      # 年度

    # 分類・関連
    category: Mapped[str | None]         # 媒体カテゴリ（既存KEYWORDS）
    bidder_count: Mapped[int | None]     # 参加者数

    # トレース
    source_url: Mapped[str]              # 結果ページURL
    detail_url: Mapped[str | None]       # 元公告URL
    raw_data: Mapped[str | None]         # JSON（全bidder情報・原データ）

    # マッチング情報
    match_method: Mapped[str | None]     # "url" / "title_fuzzy_95" / "manual" / "orphan"
    match_confidence: Mapped[float | None] # 0.0-1.0

    scraped_at: Mapped[datetime]
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
```

### 6.2 新規テーブル：`watched_companies`【MVP】

```python
class WatchedCompany(Base):
    __tablename__ = "watched_companies"

    id: Mapped[str]                      # UUID
    user_id: Mapped[str]                 # FK to users.id
    company_name: Mapped[str]            # 部分一致用キー
    label: Mapped[str | None]            # "自社" / "競合A" 等の任意ラベル
    notify_on_win: Mapped[bool]          # True: 落札時即時通知ON
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]

    # ユーザーごとに同じ企業名は1つまで
    __table_args__ = (
        UniqueConstraint('user_id', 'company_name'),
    )
```

### 6.3 新規テーブル：`bid_result_bidders`（Phase 2以降）

```python
class BidResultBidder(Base):
    __tablename__ = "bid_result_bidders"

    id: Mapped[str]
    bid_result_id: Mapped[str]           # FK to bid_results.id
    company_name: Mapped[str]
    bid_amount: Mapped[int | None]
    rank: Mapped[int | None]             # 順位
    is_winner: Mapped[bool]              # True: 落札者
```

### 6.4 既存 `users` テーブルへの影響
- **変更なし**。通知ON/OFFは既存の `notification_enabled` を共用、もしくは将来 `result_notification_enabled` を追加（MVPでは共用案を推奨）

### 6.5 既存 `bids` テーブルへの影響
- **変更なし**。`bid_results.bid_id` でFK参照するのみ。
- `bids.status` は現状 "募集中" 固定だが、紐付いた `bid_results` がある場合は表示時に "落札済み" を派生表示（カラム追加せずjoinで判定）

---

## 7. アーキテクチャ・実装方針

### 7.1 ディレクトリ構成（追加）
```
backend/app/
  scrapers/
    base.py                    # 既存（変更なし）
    {自治体}.py × 63             # 既存
    results/                   # 新規
      __init__.py
      base.py                  # BaseResultScraper(BaseScraper)
      fukuoka_pref.py
      fukuoka_city.py
      kitakyushu.py
      okinawa.py
      ...
  services/
    result_scraper_service.py  # 新規（既存scraper_serviceと同じ構造）
    result_match_service.py    # 新規（マッチングロジック）
  models.py                    # BidResult追加
  schemas.py                   # BidResultRead等のPydanticモデル
  api/
    routes.py                  # /results エンドポイント追加
```

### 7.2 BaseResultScraper の責務
```python
@dataclass
class BidResultInfo:
    """Scraped bid result information"""
    municipality: str
    title: str
    winning_company: str
    award_date: date
    source_url: str
    award_amount: Optional[int] = None
    reserve_price: Optional[int] = None
    bid_method: Optional[str] = None
    contract_date: Optional[date] = None
    bidder_count: Optional[int] = None
    detail_url: Optional[str] = None
    bidders: list[dict] = field(default_factory=list)  # [{name, amount, rank}]
    raw_data: Optional[dict] = None


class BaseResultScraper(BaseScraper):
    """Base class for result scrapers — extends BaseScraper with result-specific helpers"""

    @abstractmethod
    async def scrape_results(
        self,
        date_from: date,
        date_to: date,
    ) -> list[BidResultInfo]:
        """Scrape bid results within the date range"""
        ...

    def parse_company_name(self, raw: str) -> str:
        """Normalize company name (株式会社/(株)/㈱ などの揺れを統一)"""
        ...
```

### 7.3 マッチング・サービス
```python
class ResultMatchService:
    async def match_to_bid(
        self,
        result: BidResultInfo,
        db: AsyncSession,
    ) -> tuple[Optional[Bid], MatchMethod, float]:
        """元の bid を見つける。
        Returns:
            (bid_or_none, match_method, confidence_0_to_1)
        """
        # 1. URL一致
        # 2. タイトル類似度（rapidfuzz）+ 自治体・日付近接
        # 3. 該当なし → orphan
```

### 7.4 スケジューラ拡張
```python
# scheduler.py に追加
scheduler.add_job(
    monthly_result_scrape_job,
    CronTrigger(day=15, hour=21, minute=0),  # 毎月15日 6:00 JST
    id="monthly_result_scrape",
)
```

### 7.5 リトライ・冪等性
- 1案件1レコード（`(municipality, title, award_date, winning_company)` UNIQUE制約）
- 同じデータが重複insertされないようUPSERT
- 失敗自治体は次月リトライ（status='pending'を保持）

---

## 8. 各自治体のデータソース調査計画

### 8.1 調査タスク（Phase 1着手前に必須）
各対象自治体について以下を確認するスパイクを実施：

| 確認項目 | 内容 |
|---|---|
| URL | 結果ページのURL（複数ある場合は全て） |
| 形式 | HTML表 / 個別HTMLページ / PDF / CSV / Excel / 電子入札システム |
| 更新頻度 | 月次 / 随時 / 四半期 |
| 公表項目 | 落札者名・金額・予定価格・参加者リスト等の有無 |
| 認証要否 | 一般公開 / ログイン必須 / IP制限 |
| 更新ラグ | 開札日からの公表までの日数（目安） |

### 8.2 想定URLメモ（調査前の暫定。要確認）
- 福岡県物品委託契約電子入札システム: 公表結果ページあり
- 福岡市: `/zaisei/keiyakushido/business/` 配下
- 北九州市: 物品契約・委託契約 結果一覧
- 沖縄県: `/shigoto/nyusatsukeiyaku/` 配下に「契約結果」セクション
- 鹿児島県: `/aa02/kensei/nyusatu/kekka/` 配下
- 大分県: 「契約・入札の結果」ページ
- 熊本県・佐賀県・長崎県・宮崎県: 各 `/keiyaku-kekka/` 系

---

## 9. 段階的リリース計画

### Phase 1（MVP・約3〜4週間）
**ゴール**: 主要10自治体の2026年4月落札情報を取得・公開し、ウォッチ企業通知まで動かす

**スクレイピング層**:
- データモデル追加（`bid_results` + `watched_companies`）+ Alembic マイグレーション
- BaseResultScraper 作成
- 10自治体の result_scraper 実装（HTMLのみ・落札者1社のみ）
- ResultMatchService（URL一致 + タイトル類似度マッチ）
- 月次バッチアーキテクチャで実装（毎月15日6:00 JST + 手動トリガーが同じコードパス）

**バックエンドAPI**:
- `GET /api/results` — 落札一覧（**公開**・期間/自治体/企業名/カテゴリで検索）
- `GET /api/results/{id}` — 詳細（**公開**）
- `GET /api/watch-companies` — ウォッチ企業一覧（**ログイン必須**）
- `POST /api/watch-companies` — 登録（**ログイン必須**）
- `DELETE /api/watch-companies/{id}` — 削除（**ログイン必須**）
- `GET /api/results/export.csv` — CSVエクスポート（**ログイン必須**）

**通知サービス**:
- 即時通知サービス（落札スクレイプ後にウォッチ企業マッチ→Resendメール）
- 月次サマリーバッチ（毎月17日6:00 JST + Jinja2テンプレートでメール本文生成）

**フロントエンド**:
- ヘッダーに「落札結果」タブ追加
- `/results` 一覧画面（公開アクセス対応・フィルタ・ページネーション・ウォッチ企業ハイライト）
- 既存案件詳細画面に「この案件の落札結果」セクション追加
- ウォッチ企業マスタ管理画面（`/settings/watch-companies`）
- 公開ページ用の認証バイパス（既存ガードの調整）

**運用**:
- 2026年4月分の手動取得・データ確認
- マッチ率・取得失敗率のログ確認
- 月次バッチの初回稼働（5月15日に4月分・自動）

### Phase 2（拡張・1〜2ヶ月）
- 残り53自治体のうちHTML系（〜30自治体）を追加
- PDF系（pdfplumber対応）の主要5〜10自治体
- 入札参加者全リスト取得（`bid_result_bidders` テーブル）
- 詳細画面の拡張（参加者一覧・価格分布グラフ）

### Phase 3（高度化）
- 全自治体カバー（PDF・OCR含む）
- ダッシュボード（落札ランキング・カテゴリ別シェア・自治体別動向）
- 落札企業の名寄せ（"株式会社○○" / "(株)○○" / "㈱○○" の統合）
- 落札金額の年度推移チャート
- 企業詳細ページ（個別企業の全落札履歴）

---

## 10. リスク・課題

| ID | リスク | 影響 | 対応 |
|---|---|---|---|
| R-1 | 自治体ごとに公表形式が異なる（PDFのみの自治体多数） | スクレイパー実装コスト増 | Phase分けで段階的対応。PDFのみは後回し |
| R-2 | 結果ページがOCR必要なPDF（画像PDF） | 自動取得困難 | 該当自治体は対象外として明記 |
| R-3 | 落札金額が税込・税抜混在 | データ品質低下 | `is_tax_included` フラグで管理。表示時は明示 |
| R-4 | 元案件と落札情報の紐付け失敗（orphan多発） | UX悪化 | orphan も価値ある情報として表示。マッチ率を運用指標に |
| R-5 | 企業名の表記揺れ | 検索・集計精度低下 | Phase 3で名寄せ実装。MVPでは生データ保持 |
| R-6 | 100万円未満非公表の自治体（多数） | カバレッジ低下 | 「公表案件のみ」と注記して表示。将来的にFOIA等で補完検討 |
| R-7 | 自治体サイトの構造変更 | スクレイパー破損 | per-municipality 単体テスト + 取得件数モニタリングで早期検知 |
| R-8 | スケジューラ実行時間が伸びる（既存6:00 + 結果取得） | タイムアウト | 結果スクレイプは別時間帯（毎月15日 6:00）に分離 |
| R-9 | プロポーザル選定結果は形式が独特（社名のみ・金額非公開） | データ欠損 | `award_amount=NULL` 許容。`bid_method='公募型プロポーザル'` で識別 |
| R-10 | Renderの月額無料枠を超過 | コスト増 | DB容量・実行時間を監視。将来的に有料プラン or Postgres移行検討 |

---

## 11. ユーザー決定事項（2026-05-07）

| # | 論点 | 決定 |
|---|---|---|
| Q1 | スコープのデフォルト | **(B) 全件取得・カテゴリ分類してから表示でフィルタ** |
| Q2 | "2026年4月" の解釈 | **(A) 開札日 が4月のもの** |
| Q3 | 過去分の遡及 | **4月をMVPサンプルとして実施。最終ゴールは月次運用（毎月の開札状況を調査・とりまとめ）** |
| Q4 | Phase 1の自治体選定 | **提案の10自治体（福岡県・福岡市・北九州市・沖縄県・大分県・鹿児島県・長崎県・熊本県・佐賀県・宮崎県）でOK** |
| Q5 | 入札参加者全員の取得 | **Phase 2以降に分離（MVPは落札者1社のみ）** |
| Q6 | 通知機能 | **MVPに含める（ウォッチ企業落札時メール + 月次TOP10サマリー）** |
| Q7 | UI配置 | **両方（独立タブ `/results` + 既存案件詳細への統合表示）** |
| Q8 | 表示権限 | **全ユーザー閲覧可（公開）** |
| Q9 | 外部API化 | （将来検討・MVP対象外） |
| Q10 | ウォッチ企業マスタ | **MVPに含める（User単位の登録機能）** |

---

## 12. 工数概算（Phase 1 MVP）

| 作業 | 想定工数 |
|---|---|
| データモデル追加（`bid_results` + `watched_companies`）+ Alembicマイグレーション | 1日 |
| BaseResultScraper + 共通ユーティリティ | 1日 |
| 各自治体結果ページ調査スパイク（10自治体） | 1〜2日（要訪問・HTML確認） |
| 各自治体スクレイパー実装（10自治体・HTMLのみ・落札者1社） | 3〜5日 |
| ResultMatchService（URL/タイトル類似度マッチ） | 1日 |
| 月次バッチ + 手動トリガーの統合アーキテクチャ | 1日 |
| 落札情報API（公開/認証ハイブリッド） | 1日 |
| ウォッチ企業マスタAPI（CRUD・ログイン必須） | 1日 |
| 即時通知サービス（落札スクレイプ→Resend連携） | 1日 |
| 月次サマリーバッチ + メールテンプレート | 1.5日 |
| フロントエンド `/results` 一覧（公開アクセス・フィルタ・ページネーション） | 2〜3日 |
| フロントエンド ウォッチ企業マスタ画面 | 1日 |
| 既存案件詳細への落札結果セクション統合 | 0.5日 |
| CSV/Excelエクスポート（認証付き） | 0.5日 |
| 結合テスト・バグ修正・本番投入 | 2〜3日 |
| **合計** | **17〜22人日（実働3.5〜4.5週間）** |

> **備考**: Phase 1のスコープが大きいため、内部的に2スプリントに分割するのも可:
> - **Sprint 1**: スクレイピング + 落札一覧公開ページ（〜10人日）
> - **Sprint 2**: ウォッチ企業マスタ + 通知 + 既存画面統合（〜10人日）

---

## 13. 検収条件（Phase 1 完了基準）

### 13.1 データ・スクレイピング
1. [ ] 対象10自治体について、2026年4月分（開札日4/1〜4/30）の落札情報が `bid_results` テーブルに保存されている
2. [ ] うち **70%以上** が元の `bids` レコードと正しく紐付いている（残りは orphan として表示）
3. [ ] 自治体別の取得件数・失敗率がログに記録される
4. [ ] 月次スケジュール（毎月15日6:00 JST）が登録され、5月15日に自動実行される
5. [ ] 既存スクレイパーの動作に影響がない（リグレッションテスト）

### 13.2 機能
6. [ ] `/results` 画面が **未ログインで閲覧可能** で、月・自治体・カテゴリ・企業名検索ができる
7. [ ] 既存案件詳細画面に紐づく落札結果が表示される
8. [ ] ログインユーザーが自分のウォッチ企業を登録・編集・削除できる
9. [ ] ログインユーザーがCSV/Excelエクスポートできる

### 13.3 通知
10. [ ] ウォッチ企業の落札情報がスクレイプされた際、登録ユーザーへメールが届く
11. [ ] 月次サマリーメールが毎月17日に送信される（次回6/17）
12. [ ] 通知ON/OFF設定がユーザーごとに有効

### 13.4 運用品質
13. [ ] サンプル運用（4月分）後にユーザーレビューを実施し、改善点を Phase 2 に反映する

---

## 付録 A: 用語集
- **落札（らくさつ）**: 入札で最も有利な条件（通常最低価格）を提示し、契約相手に決定すること
- **開札（かいさつ）**: 入札書を開封し、内容を公表する行為
- **予定価格**: 発注者があらかじめ設定する契約金額の上限
- **落札率**: 落札金額 ÷ 予定価格。談合等の検知指標として使われる
- **公募型プロポーザル**: 価格ではなく企画提案内容で選ぶ方式（媒体PR系で多用）
- **随意契約**: 競争入札によらず特定者と契約する方式
- **orphan**: 落札情報があるが元の募集案件がDBに存在しない状態
