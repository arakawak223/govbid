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

        # If the month is far ahead of current month (e.g., 12月 when we're in 1月),
        # it's likely from last year
        if month > today.month + 2:
            year = today.year - 1
        elif month < today.month - 2:
            # If month is far behind (e.g., 1月 締切 when we're in 11月),
            # it could be next year, but for締切 it's usually past
            year = today.year
        else:
            year = today.year

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
        "観光PR", "シティプロモーション", "移住促進", "魅力発信",
        "キャンペーン", "SNS", "ウェブサイト", "ホームページ"
    ],
    "イベント": [
        "イベント", "企画運営", "催事", "フェア", "フェスティバル",
        "祭り", "展示会", "セミナー", "シンポジウム", "フォーラム",
        "式典", "記念事業", "啓発", "体験"
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
    "広告を募集します", "広告主を募集", "広告付き",
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
    "物品購入", "備品購入",
    # その他の除外
    "入札参加資格", "再生資源売却",
    # 自動販売機関連
    "自動販売機設置", "自動販売機の設置",
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

        # 締切日チェック（詳細ページのapplication_endのみ使用）
        # タイトルの日付は参加申込締切など最終締切でない場合があるため使用しない
        if bid.application_end and bid.application_end < date.today():
            excluded_by_deadline += 1
            logger.debug(f"Excluded by deadline ({bid.application_end}): {bid.title[:50]}")
            continue  # 期限切れ

        # カテゴリ分類（広報・プロモーション・イベントに該当するもののみ含める）
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
