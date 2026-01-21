import re
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


# 除外パターン（ナビゲーション、工事関連、広告募集、結果ページ等）
EXCLUDE_PATTERNS = [
    # ナビゲーション・UI要素
    "ホームページ", "このホームページについて",
    "メニューを飛ばして", "本文へ", "Other Languages",
    "サイトマップ", "お問い合わせ", "アクセス",
    # 工事関連
    "公共工事", "工事入札", "入札・契約（工事",
    # 広告募集（案件ではなく広告枠の募集）
    "広告を募集します", "広告主を募集", "広告付き",
    # イベント参加者募集（入札案件ではない）
    "イベント・講座・募集",
    # 結果・回答（案件ではなく結果報告）
    "【審査結果】", "【入札結果】", "【選定結果】",
    "委託先が決まりました", "が決定しました",
    "質問書への回答", "質問への回答",
    # その他の除外
    "入札参加資格", "再生資源売却",
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
    """Filter and categorize bids based on keywords

    Args:
        bids: List of BidInfo objects to filter

    Returns:
        Filtered and categorized list of BidInfo objects
    """
    filtered = []

    for bid in bids:
        # 除外パターンに該当する場合はスキップ
        if should_exclude(bid.title):
            continue

        category = categorize_bid(bid.title)
        if category:
            bid.category = category
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
