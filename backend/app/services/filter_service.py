import re
from datetime import date
from typing import Optional

from app.scrapers.base import BidInfo


def extract_deadline_from_title(title: str) -> Optional[date]:
    """Extract deadline date from title if present

    Patterns like: 【1月19日締切】, 【12月26参加申込締切】, 〇月〇日締切
    """
    # Convert full-width numbers to half-width
    full_to_half = str.maketrans('０１２３４５６７８９', '0123456789')
    title = title.translate(full_to_half)

    # Pattern: X月Y日 followed by optional text and 締切
    # Matches: 1月19日締切, 12月26参加申込締切, 12月19日締切
    match = re.search(r'(\d{1,2})月(\d{1,2})日?[^】]{0,10}締切', title)
    if match:
        month = int(match.group(1))
        day = int(match.group(2))

        # Determine year based on current date
        today = date.today()

        # Calculate month difference (positive = future, negative = past)
        month_diff = month - today.month

        year = today.year
        if month_diff > 2:
            # Month is significantly ahead (e.g., 12月 when we're in 1月)
            # This is likely a deadline from the previous year
            year = today.year - 1
        elif month_diff < 0 or (month_diff == 0 and day < today.day):
            # Month has passed, or same month but day has passed
            # Keep current year (deadline has passed this year)
            pass

        try:
            return date(year, month, day)
        except ValueError:
            pass

    return None


def is_deadline_passed_from_title(title: str) -> bool:
    """Check if deadline in title has already passed"""
    deadline = extract_deadline_from_title(title)
    if deadline:
        return deadline < date.today()
    return False


# Keywords for filtering relevant bids
KEYWORDS = {
    "広報": [
        "広報", "PR", "メディア", "報道", "情報発信", "周知", "広告",
        "パブリシティ", "プレスリリース", "ニュースレター", "情報誌"
    ],
    "プロモーション": [
        "プロモーション", "promotion", "宣伝", "販促", "ブランディング",
        "シティプロモーション", "移住促進", "魅力発信",
        "キャンペーン", "SNS", "ウェブサイト", "ホームページ"
    ],
    "イベント": [
        "イベント", "企画運営", "催事", "フェア", "フェスティバル",
        "祭り", "まつり", "展示会", "セミナー", "シンポジウム", "フォーラム",
        "式典", "記念事業", "啓発", "体験",
        "普及啓発", "企画提案", "企画・運営"
    ],
    "ふるさと納税": [
        "ふるさと納税", "ふるさとチョイス", "さとふる", "地域応援",
        "寄付", "寄附", "返礼品", "お礼の品", "ポータルサイト"
    ],
    "マラソン": [
        "マラソン", "ランニング", "駅伝", "ロードレース", "ハーフマラソン",
        "フルマラソン", "市民マラソン", "シティマラソン", "リレーマラソン"
    ],
    "ボートレース": [
        "ボートレース", "競艇", "ボート場", "競走場", "モーターボート"
    ],
    "観光": [
        "観光", "ツーリズム", "tourism", "観光PR", "観光振興", "観光誘客",
        "インバウンド", "訪日", "旅行", "周遊", "観光案内", "観光情報"
    ],
    "特産品": [
        "特産品", "特産物", "名産品", "地場産品", "地域産品", "物産",
        "農産物", "水産物", "地元産", "ブランド産品"
    ],
    # 以下、DL漏れ.xlsx（90件）の分析で追加した新規カテゴリ
    "動画・映像": [
        "動画制作", "動画配信", "映像制作", "番組制作", "放送",
        "CM制作", "CMあじさい", "CM放送"
    ],
    "就業・就労": [
        "就業", "就労", "働き方", "両立支援", "就農", "人材採用",
        "採用支援", "就業促進", "就業意欲"
    ],
    "人材育成・研修": [
        "人材育成", "研修", "インターンシップ", "リーダー育成",
        "育成プログラム", "育成事業", "育成支援",
        "健康教育", "英語授業", "英語４技能", "英語4技能", "英語発信力",
        "交流プログラム"
    ],
    "スタートアップ": [
        "スタートアップ", "起業", "社会起業家", "創業", "ベンチャー"
    ],
    "婚活・結婚": [
        "婚活", "出会い", "結婚支援", "結婚総合", "多子世帯",
        "恋叶", "めたコン", "やまコン"
    ],
    "業務改革・BPR": [
        "BPR", "業務改革", "業務改善"
    ],
    "健康・医療": [
        "がん検診", "フェムケア", "プレコンセプションケア",
        "ピンクリボン", "健康課題"
    ],
    "販路拡大・海外展開": [
        "販路拡大", "海外展開", "トレードショー", "商談会",
        "ポップアップ", "ビジネス交流会", "交流会"
    ],
    "環境・エコ": [
        "節水", "3R", "3Ｒ", "GX", "脱炭素", "うちエコ",
        "プラスチックごみ", "省エネ", "ごみ削減"
    ],
    "学習・生活支援": [
        "学習支援", "生活支援", "学習・生活"
    ],
    "アンケート・調査": [
        "アンケート調査", "アンケート"
    ],
    "eラーニング": [
        "eラーニング", "Eラーニング", "ｅラーニング",
        "ハラスメント", "コンプライアンス"
    ],
    "スポーツ": [
        "スポーツサポート", "スポーツセンター", "国スポ", "障スポ"
    ],
    "商品開発・知財": [
        "商品開発", "知財", "クリエイティブ"
    ],
    "コンテスト": [
        "コンテスト"
    ],
    "移住・Uターン": [
        "U・Iターン", "Uターン", "Iターン", "移住促進", "移住就農", "移住"
    ],
    "企業誘致": [
        "企業誘致", "誘致活動", "立地促進", "オフィス誘致", "サテライトオフィス誘致"
    ],
    "デジタル・DX": [
        "デジタル城下町", "デジタル推進", "DX推進", "デジタル化推進", "スマートシティ"
    ],
    "地域活性・まちづくり": [
        "地域とコネクト", "地域活性", "まちづくり", "沿道利活用", "利活用促進",
        "駅周辺", "中心市街地", "にぎわい創出"
    ],
    "ブランディング・未来構想": [
        "未来デザイン", "未来構想", "ブランディング", "シティプロモーション",
        "ブランド戦略"
    ],
    "国際・グローバル": [
        "グローバル", "ジュニアドリーム", "国際交流", "海外派遣", "海外研修"
    ],
    "産業支援": [
        "リーディングカンパニー", "経営力", "経営支援", "中小企業支援",
        "産業振興", "創出支援"
    ],
    "イメージアップ・PR": [
        "イメージアップ", "魅力発信", "PR事業", "広報活動"
    ],
    "文化芸術": [
        "アーティスト", "アート", "文化芸術", "芸術祭", "文化振興"
    ],
    "記念事業": [
        "記念プロジェクト", "生誕", "没後", "周年記念", "周年事業"
    ]
}


def categorize_bid(title: str) -> Optional[str]:
    """Categorize a bid based on its title

    Args:
        title: The bid title to categorize

    Returns:
        Category name if matched, None otherwise
    """
    title_lower = title.lower()

    for category, keywords in KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in title_lower:
                return category

    return None


def is_relevant_bid(title: str) -> bool:
    """Check if a bid title matches any of the relevant keywords

    Args:
        title: The bid title to check

    Returns:
        True if the bid is relevant, False otherwise
    """
    return categorize_bid(title) is not None


# 除外パターン（ナビゲーション、工事関連、広告募集、結果ページ等）
EXCLUDE_PATTERNS = [
    # ナビゲーション・UI要素（案件タイトルではないもの）
    "このホームページについて",
    "メニューを飛ばして", "本文へ", "Other Languages",
    "サイトマップ", "お問い合わせ一覧", "アクセスマップ",
    "入札公告掲示板", "入札情報一覧", "入札・契約情報",
    # 部署・課のページ（案件ではない）
    "の入札情報", "課の入札", "部の入札",
    # 工事関連
    "公共工事", "工事入札", "入札・契約（工事",
    # 広告募集（案件ではなく広告枠の募集）
    "広告を募集します", "広告主を募集",
    # 結果・回答（案件ではなく結果報告）
    "【審査結果】", "【入札結果】", "【選定結果】",
    "委託先が決まりました", "が決定しました",
    "質問書への回答", "質問への回答",
    "プロポーザル結果", "審査結果", "選定結果",
    # 意見募集・パブリックコメント
    "意見募集", "パブリック・コメント", "パブリックコメント",
    # 職員募集関連
    "職員募集", "職員採用", "会計年度任用職員", "採用試験",
    "パート募集", "アルバイト募集", "嘱託職員",
    # テナント・物品購入関連
    "テナント募集", "の購入に係る", "の購入にかかる",
    "物品購入", "備品購入", "物品契約", "物品調達",
    "物品売買", "物品借入", "物品納入", "物品の調達",
    # その他の除外
    "入札参加資格", "再生資源売却",
    # 自動販売機関連
    "自動販売機設置", "自動販売機の設置",

    # === 2026-05-07 追加: 0507抽出データ57件の不要案件レビューに基づく除外 ===
    # メディア企業から離れた専門業務
    "債権回収", "喀痰吸引", "喀痰吸引等研修",
    "障害福祉サービス事業所",
    "活水産物の試験輸出", "輸出業務",
    # 脱炭素関連の支援/構築業務（脱炭素テーマ自体は媒体PRとして対象維持）
    "脱炭素推進支援",
    # 測量・調査系の専門業務
    "賦存量調査", "温泉賦存量",
    # 物資保管・物流・什器整備
    "備蓄物資保管", "物資保管業務", "出荷発送管理",
    "什器等整備", "什器整備",
    # 建設・整備系
    "キャンプ場再整備",
    # 交通・運輸系
    "地域公共交通確保維持改善", "運送予定者選定",
    "交通体系基本計画", "次世代交通ビジョン",
    # 人材派遣・労働者派遣
    "労働者派遣", "人材派遣事業", "ICT支援員派遣",
    "支援員派遣業務",
    # IT/デジタル専門業務（IT企業優位案件）
    "デジタル人材派遣", "IT人材創造", "ICTビジネス高度化",
    "デジタルコンテンツ産業", "デジタルリテラシー強化",
    "海外IT交流",
    "システム構築・運用保守", "アプリケーション構築・運用保守",
    "チャットボット構築", "アプリケーション等の構築",
    # メディア対象外と明示された専門研修
    "コーチング研修",
    "ハラスメント及びコンプライアンス",
    "マネジメント研修",
    "保育所等職員研修", "子育て支援員研修",
    "児童育成支援拠点",
    "農業雇用改善研修",
    "業務継続計画（BCP", "業務継続計画(BCP",
    # 業者募集（出展者・出演者・協賛事業者・テレワーカー・代表者）
    "出演者募集",
    "出展を希望する事業者", "出展事業者を募集", "出展希望事業者",
    "協賛事業者募集", "ふるさと納税協賛",
    "テレワーカーの募集", "テレワーカー募集",
    "代表青年を募集",
    # 研修参加者・受講者募集（受託ではなく聴講）
    "集団研修（オンライン研修）",
    "研修会（オンライン開催）参加",
    # フォーム・様式（案件本体ではなく付属書類）
    "別紙様式", "【様式",
    # 結果・回答ページ（既存に追加）
    "採択結果を公表", "結果を公表します",
    "委託候補者を決定",
    "質問書に対する回答",
    "【質問書の回答を掲載しました】",
    "入札・企画提案競技等結果",
    "企画提案競技等結果",
    # 募集終了
    "【募集終了】", "募集は終了しました", "【終了しました】",
    # 補助金募集（事業者向けの補助金申請）
    "補助金の募集", "人材育成事業等補助金",
    # 旅行業（中学生体験学習等）
    "中学生「国内」体験学習", "「国内」体験学習",
    # ショップ・センター運営
    "アンテナショップ",
    # 観光人材の確保・定着支援（媒体業務でない）
    "観光人材確保・定着支援", "人材確保・定着支援",
    # 地域商業活性化モデル（地元企業優位）
    "地域商業活性化モデル",
    # 物品調達系（GIGAスクール端末等）
    "GIGAスクール", "学習者用端末",
]


def should_exclude(title: str) -> bool:
    """Check if a bid should be excluded based on title patterns

    Args:
        title: The bid title to check

    Returns:
        True if the bid should be excluded, False otherwise
    """
    for pattern in EXCLUDE_PATTERNS:
        if pattern in title:
            return True
    return False


def filter_bids(bids: list[BidInfo]) -> list[BidInfo]:
    """Filter and categorize bids

    Args:
        bids: List of BidInfo objects to filter

    Returns:
        Filtered and categorized list of BidInfo objects
    """
    import logging
    logger = logging.getLogger(__name__)

    filtered = []
    excluded_by_pattern = 0
    excluded_by_deadline = 0
    excluded_by_keyword = 0

    for bid in bids:
        # 除外パターンに該当する場合はスキップ
        if should_exclude(bid.title):
            excluded_by_pattern += 1
            logger.debug(f"Excluded by pattern: {bid.title[:50]}")
            continue

        # 締切日チェック
        # 1. 詳細ページのapplication_endを優先
        # 2. application_endがない場合はタイトルの締切日をフォールバックとして使用
        if bid.application_end and bid.application_end < date.today():
            excluded_by_deadline += 1
            logger.debug(f"Excluded by application_end ({bid.application_end}): {bid.title[:50]}")
            continue  # 期限切れ

        # タイトルから締切日を抽出（application_endがない場合のフォールバック）
        if not bid.application_end and is_deadline_passed_from_title(bid.title):
            title_deadline = extract_deadline_from_title(bid.title)
            excluded_by_deadline += 1
            logger.debug(f"Excluded by title deadline ({title_deadline}): {bid.title[:50]}")
            continue  # タイトルの締切日が過ぎている

        # カテゴリ分類（対象カテゴリに該当するもののみ含める）
        category = categorize_bid(bid.title)
        if category:
            bid.category = category
            filtered.append(bid)
            logger.debug(f"Included ({category}): {bid.title[:50]}")
        else:
            excluded_by_keyword += 1
            logger.debug(f"Excluded by keyword mismatch: {bid.title[:50]}")

    logger.info(
        f"Filter results: {len(filtered)} included, "
        f"{excluded_by_pattern} excluded by pattern, "
        f"{excluded_by_deadline} excluded by deadline, "
        f"{excluded_by_keyword} excluded by keyword mismatch"
    )

    return filtered


def get_all_keywords() -> list[str]:
    """Get all keywords as a flat list

    Returns:
        List of all keywords
    """
    keywords = []
    for category_keywords in KEYWORDS.values():
        keywords.extend(category_keywords)
    return list(set(keywords))
