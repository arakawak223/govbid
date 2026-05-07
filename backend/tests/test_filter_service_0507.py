"""0507抽出データ57件の不要案件レビューに基づくフィルタ回帰テスト

ユーザー（arakawak223）が2026-05-07の抽出データに対して付けた
「抽出不要理由」コメント（diff_0507_unique_ara追加コメント.csv）を
ベースに、フィルタが下記を満たすことを保証する：

1. 不要理由が記載された57件 → should_exclude=True で除外される
   （古い案件理由の2件のみタイトル判別不可で除外: スクレイパー側課題）
2. 不要理由が空欄の5件 → should_exclude=False で保持される
3. 元から正常抽出された115件 → should_exclude=False で保持される

実行: cd backend && python -m pytest tests/test_filter_service_0507.py -v
"""
import csv
import sys
from pathlib import Path

# backend/ を sys.path に追加（pytest／単体実行どちらでも動かす）
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.filter_service import should_exclude  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parent.parent
REVIEW_CSV = BACKEND_DIR / "diff_0507_unique_ara追加コメント.csv"
EXPORT_CSV = BACKEND_DIR / "govbid_export_2026-05-07.csv"

# タイトルから古さが判別不可で取りこぼしを許容している案件
# （別途スクレイパー側のurl/日付フィルタで対応すべき）
KNOWN_MISSED_OLD_CASES = {
    "「ふるさと・くるめ応援寄付」運営業務公募型プロポーザルの実施について",
    "【公募型プロポーザル】ゼロカーボンシティさがし啓発用動画制作及び広報業務委託",
}


def _load_review_csv():
    unnecessary = []
    keep_holdouts = []
    with open(REVIEW_CSV, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            title = row["案件タイトル"]
            reason = row.get("抽出不要理由", "").strip()
            if reason:
                unnecessary.append((title, reason))
            else:
                keep_holdouts.append(title)
    return unnecessary, keep_holdouts


def _load_normal_extracted():
    titles = set()
    with open(EXPORT_CSV, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            titles.add(row["案件タイトル"])
    return titles


def test_unnecessary_bids_are_excluded():
    """57件の不要案件のうち、タイトル判別可能な55件が除外される"""
    unnecessary, _ = _load_review_csv()
    not_excluded = [
        (t, r) for t, r in unnecessary
        if not should_exclude(t) and t not in KNOWN_MISSED_OLD_CASES
    ]
    assert not not_excluded, (
        f"以下の不要案件が除外できていません:\n"
        + "\n".join(f"  [{r[:30]}] {t[:90]}" for t, r in not_excluded)
    )


def test_held_out_bids_are_kept():
    """K列空欄（保留＝ユーザーが除外を明示していない）案件は保持される"""
    _, keep = _load_review_csv()
    wrongly_excluded = [t for t in keep if should_exclude(t)]
    assert not wrongly_excluded, (
        f"保留案件が誤って除外されています:\n"
        + "\n".join(f"  {t[:90]}" for t in wrongly_excluded)
    )


def test_legit_bids_are_kept():
    """0507に正常抽出された115件は除外されない（過剰除外なし）"""
    unnecessary, holdouts = _load_review_csv()
    unnecessary_titles = {t for t, _ in unnecessary}
    all_extracted = _load_normal_extracted()
    legit = all_extracted - unnecessary_titles - set(holdouts)

    wrongly_excluded = [t for t in legit if should_exclude(t)]
    assert not wrongly_excluded, (
        f"正常案件が誤って除外されています:\n"
        + "\n".join(f"  {t[:90]}" for t in wrongly_excluded)
    )


def test_specific_known_cases():
    """代表的なケースを個別に固定（リグレッション防止）"""
    # 不要案件
    assert should_exclude("【企画提案公募】「福岡県債権回収業務」業務委託")
    assert should_exclude("ベトナム向け活水産物の試験輸出業務の委託事業者を募集します。")
    assert should_exclude("コーチング研修及びフォローアップ研修業務委託")
    assert should_exclude("ハラスメント及びコンプライアンス等eラーニング研修業務委託")
    assert should_exclude("令和8年度沖縄未来のIT人材創造事業委託業務に係る企画提案の公募")
    assert should_exclude("【様式2】企画提案応募申請書 （Word 27.5KB）")
    assert should_exclude("別紙様式６　企画提案書提出届（Word)")
    assert should_exclude("入札・企画提案競技等結果")
    assert should_exclude("佐賀市ふるさと納税協賛事業者募集")
    assert should_exclude("【募集終了】テレワーカーの募集について【名護市テレワーク人材育成事業】")

    # 保留案件は通る
    assert not should_exclude("鹿児島県ホームページ作成支援システム一式の賃貸借に係る企画提案競技について")
    assert not should_exclude("乳幼児との触れ合い体験実施業務委託の企画提案を募集します！")

    # 正常案件は通る（脱炭素テーマの媒体PR案件など、過剰除外しない代表例）
    assert not should_exclude(
        "2026年4月23日令和8年度宮崎市脱炭素先行地域づくり事業"
        "「スポーツ×エコアクションアプリ（仮称）」構築業務委託に関する公募型プロポーザルについて"
    )


if __name__ == "__main__":
    # pytest 不在環境でも単体実行可能
    test_unnecessary_bids_are_excluded()
    test_held_out_bids_are_kept()
    test_legit_bids_are_kept()
    test_specific_known_cases()
    print("全テスト通過")
