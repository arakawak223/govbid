import re
from datetime import date, timedelta
from typing import Optional

from app.scrapers.base import BidInfo


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


def extract_deadline_from_title(title: str) -> Optional[date]:
    """Extract deadline date from title text

    Handles patterns like:
    - 【1月23日締切】
    - 【2月12日締切】
    - （締切：1月31日）
    - 締切日：令和7年1月20日
    - 提出期限：1月31日
    - 提出期限　令和7年1月31日
    """
    today = date.today()
    current_year = today.year

    # Pattern: 【X月Y日締切】 or 【X月Y日申請締切】 or 【X月Y日提出期限】
    match = re.search(r'[【\[（(](\d{1,2})月(\d{1,2})日[^】\]）)]*(締切|提出期限|期限)[】\]）)]', title)
    if match:
        month = int(match.group(1))
        day = int(match.group(2))
        year = current_year
        try:
            deadline = date(year, month, day)
            if deadline < today:
                deadline = date(year + 1, month, day)
            return deadline
        except ValueError:
            pass

    # Pattern: 締切：X月Y日 or 締切日：X月Y日 or 提出期限：X月Y日
    match = re.search(r'(?:締切[日]?|提出期限|応募期限|申込期限|受付期限)[：:\s]+(\d{1,2})月(\d{1,2})日', title)
    if match:
        month = int(match.group(1))
        day = int(match.group(2))
        year = current_year
        try:
            deadline = date(year, month, day)
            if deadline < today:
                deadline = date(year + 1, month, day)
            return deadline
        except ValueError:
            pass

    # Pattern: 提出期限 令和X年X月X日 or 締切 令和X年X月X日
    match = re.search(r'(?:締切|提出期限|応募期限|申込期限|受付期限)[：:\s]*令和(\d+)年(\d{1,2})月(\d{1,2})日', title)
    if match:
        year = int(match.group(1)) + 2018
        month = int(match.group(2))
        day = int(match.group(3))
        try:
            return date(year, month, day)
        except ValueError:
            pass

    # Pattern: 令和X年X月X日まで or 令和X年X月X日締切 (generic)
    match = re.search(r'令和(\d+)年(\d{1,2})月(\d{1,2})日(?:まで|締切|期限)?', title)
    if match:
        year = int(match.group(1)) + 2018
        month = int(match.group(2))
        day = int(match.group(3))
        try:
            return date(year, month, day)
        except ValueError:
            pass

    # Pattern: X月X日まで or ～X月X日
    match = re.search(r'(?:～|〜|まで\s*)?(\d{1,2})月(\d{1,2})日(?:まで|迄)', title)
    if match:
        month = int(match.group(1))
        day = int(match.group(2))
        year = current_year
        try:
            deadline = date(year, month, day)
            if deadline < today:
                deadline = date(year + 1, month, day)
            return deadline
        except ValueError:
            pass

    return None


def extract_start_date_from_title(title: str) -> Optional[date]:
    """Extract start/announcement date from title text

    Handles patterns like:
    - 【令和7年1月10日公開】
    - （1月15日掲載）
    - 掲載日：1月20日
    """
    today = date.today()
    current_year = today.year

    # Pattern: 令和X年X月X日 (generic date in title, likely announcement date)
    match = re.search(r'令和(\d+)年(\d{1,2})月(\d{1,2})日', title)
    if match:
        year = int(match.group(1)) + 2018
        month = int(match.group(2))
        day = int(match.group(3))
        try:
            return date(year, month, day)
        except ValueError:
            pass

    # Pattern: X月X日掲載 or 掲載日：X月X日
    match = re.search(r'(\d{1,2})月(\d{1,2})日(?:掲載|公開|公告)', title)
    if match:
        month = int(match.group(1))
        day = int(match.group(2))
        try:
            start_date = date(current_year, month, day)
            # If date is in the future, use last year
            if start_date > today:
                start_date = date(current_year - 1, month, day)
            return start_date
        except ValueError:
            pass

    return None


def is_bid_active(bid: BidInfo) -> bool:
    """Check if bid is still active (not expired)

    Args:
        bid: BidInfo object to check

    Returns:
        True if bid is active and has a valid deadline, False otherwise
    """
    today = date.today()

    # If application_end is set, check if it's in the future
    if bid.application_end:
        return bid.application_end >= today

    # Try to extract deadline from title
    deadline = extract_deadline_from_title(bid.title)
    if deadline:
        bid.application_end = deadline
        return deadline >= today

    # If no deadline found, exclude the bid (strict mode)
    return False


def is_recently_announced(bid: BidInfo, days: int = 30) -> bool:
    """Check if bid was announced within the specified number of days

    Args:
        bid: BidInfo object to check
        days: Number of days to consider as "recent" (default: 30)

    Returns:
        True if bid is recently announced, False otherwise
    """
    today = date.today()
    cutoff_date = today - timedelta(days=days)

    # If application_start is set, use it
    if bid.application_start:
        return bid.application_start >= cutoff_date

    # Try to extract start date from title
    start_date = extract_start_date_from_title(bid.title)
    if start_date:
        bid.application_start = start_date
        return start_date >= cutoff_date

    # If no start date found, set today as start date (new scrape = recent)
    bid.application_start = today
    return True


def is_qa_or_supplementary(title: str) -> bool:
    """Check if the title indicates Q&A or supplementary information (not an actual bid)

    Args:
        title: The bid title to check

    Returns:
        True if it's Q&A or supplementary info, False otherwise
    """
    # These patterns indicate the item is ONLY a Q&A document, not an actual bid
    exclusion_patterns = [
        "に関する質問と回答",
        "に係る質問と回答",
        "質問への回答について",
        "質問書に対する回答について",
        "質問に対する回答について",
        "に係る質問への回答",
        "Ｑ＆Ａについて",
        "Q&Aについて",
        "審査結果について",
        "選定結果について",
        "契約締結について",
        "落札者決定",
        "落札について",
        "決定しました",
    ]
    return any(pattern in title for pattern in exclusion_patterns)


def is_past_fiscal_year(title: str) -> bool:
    """Check if the title refers to a past fiscal year

    Args:
        title: The bid title to check

    Returns:
        True if it's a past fiscal year, False otherwise
    """
    today = date.today()
    current_year = today.year
    current_month = today.month

    # Japanese fiscal year runs from April to March
    # If we're in Jan-Mar, current fiscal year started last calendar year
    if current_month < 4:
        current_fiscal_year = current_year - 1
    else:
        current_fiscal_year = current_year

    # 令和7年度 = 2025年度, 令和8年度 = 2026年度
    current_reiwa = current_fiscal_year - 2018

    # Check for past fiscal years in title
    past_years = [
        f"令和{current_reiwa - 1}年度",  # 1 year ago
        f"令和{current_reiwa - 2}年度",  # 2 years ago
        f"令和{current_reiwa - 3}年度",  # 3 years ago
        f"令和６年度",  # Full-width 6
        f"令和５年度",  # Full-width 5
        f"令和４年度",  # Full-width 4
    ]

    return any(year in title for year in past_years)


def filter_bids(bids: list[BidInfo]) -> list[BidInfo]:
    """Filter and categorize bids based on keywords, deadline, and announcement date

    Args:
        bids: List of BidInfo objects to filter

    Returns:
        Filtered and categorized list of BidInfo objects (active and recent only)
    """
    filtered = []

    for bid in bids:
        # Skip Q&A and supplementary information
        if is_qa_or_supplementary(bid.title):
            continue

        # Skip past fiscal year bids
        if is_past_fiscal_year(bid.title):
            continue

        category = categorize_bid(bid.title)
        if category:
            bid.category = category

            # Check if bid is still active (not expired)
            if not is_bid_active(bid):
                bid.status = "募集終了"
                continue  # Skip expired bids

            # Check if bid was announced within the last month
            if not is_recently_announced(bid, days=30):
                continue  # Skip old announcements

            bid.status = "募集中"
            filtered.append(bid)

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
