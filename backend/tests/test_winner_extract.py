"""落札企業抽出の回帰テスト

スクレイピング運用で判明した誤検出パターンを固定する:
1. 勝者ラベル直後の企業名だけを採る（次点・参加業者は採らない）
2. 前株/後株・（株）等の略記を正しく扱う
3. 募集要項の「共同企業体でも応募できる」等の条件文を採らない
4. ページ全文からの緩い抽出は禁止 — 見出し/表の勝者列/同一ブロックの3経路のみ
5. 案件名に年度がある場合、本文の年度が違えば不採用
6. 重複除去は「案件core＋企業名」と「結果URL＋企業名」の両方で効く

実行: cd backend && python -m pytest tests/test_winner_extract.py -v
"""
import sys
from pathlib import Path

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.winner_crawler import CaseTarget, WinnerCrawler  # noqa: E402
from app.services.winner_extract import (  # noqa: E402
    company_key,
    find_amount,
    find_winner,
    prep_text,
    title_core,
    title_pos,
    year_ok,
)


# ---------------------------------------------------------------- 抽出コア
def extract(text):
    """本番と同じく prep_text を通してから抽出する"""
    return find_winner(prep_text(text))


def test_後株を抽出する():
    r = extract("選定結果　受託者　九州広告株式会社")
    assert r is not None and r[1] == "九州広告株式会社"


def test_前株を抽出する():
    r = extract("契約の相手方　株式会社福岡プロモーション")
    assert r is not None and r[1] == "株式会社福岡プロモーション"


def test_略記の法人格を正式表記に正規化する():
    r = extract("落札者　（株）テスト企画")
    assert r is not None and r[1] == "株式会社テスト企画"


def test_法人格直後のスペースを許容する():
    r = extract("受託者：株式会社 みらい総研")
    assert r is not None and r[1].replace(" ", "") == "株式会社みらい総研"


def test_次点は採らない():
    r = extract("受託者　株式会社アルファ　次点者　株式会社ベータ")
    assert r is not None and r[1] == "株式会社アルファ"


def test_次点しかない場合は抽出しない():
    assert extract("次点者　株式会社ベータ") is None


def test_参加業者リストは採らない():
    assert extract("参加事業者　株式会社ガンマ　株式会社デルタ") is None


def test_募集要項の共同企業体ルール文は採らない():
    assert extract("共同企業体でも応募できるものとする") is None


def test_ラベルがなければ抽出しない():
    assert extract("本業務は株式会社イプシロンが過去に受注した実績があります。") is None


def test_明示ラベルのある金額のみ取る():
    assert find_amount("落札金額 12,345,678円") == 12345678
    assert find_amount("契約金額 1,200千円") == 1200000
    assert find_amount("予算額は10,000,000円程度を想定") is None


# ------------------------------------------------------------ 案件名の照合
def test_案件名coreは年度と定型語尾を落とす():
    assert title_core("令和6年度　観光プロモーション業務委託") == title_core("観光プロモーション")


def test_部分一致は6割以上を要求する():
    core = title_core("福岡県観光プロモーション動画制作業務")
    assert title_pos(core, core) == 0
    assert title_pos(core, "全く関係のない別の案件名です") < 0


def test_年度が違うページは不採用():
    assert year_ok("令和6年度観光PR業務", "令和6年度観光PR業務の選定結果") is True
    assert year_ok("令和6年度観光PR業務", "令和5年度観光PR業務の選定結果") is False
    assert year_ok("観光PR業務", "年度表記のない本文") is True


# ------------------------------------------------------------ 名寄せ・重複
def test_前株後株と略記を同一キーに寄せる():
    assert company_key("株式会社テスト広告社") == company_key("テスト広告社(株)")
    assert company_key("㈱テスト広告社") == company_key("株式会社テスト広告社")
    assert company_key("株式会社テスト広告社") != company_key("株式会社テスト印刷")


# ------------------------------------------------- ページ照合の3経路と誤検出
def _match(html, case_title, url="https://example.lg.jp/kekka.html"):
    crawler = WinnerCrawler(delay=0)
    soup = BeautifulSoup(html, "html.parser")
    text = prep_text(soup.get_text("\n"))
    case = CaseTarget(key="k1", title=case_title, url=url, municipality="テスト市")
    hits = {}
    crawler.match_cases(text, url, [case], hits, soup=soup)
    return hits.get("k1")


def test_経路1_見出しに案件名があればページ全体から抽出する():
    html = """<html><head><title>観光プロモーション動画制作業務の選定結果</title></head>
    <body><h1>観光プロモーション動画制作業務の選定結果</h1>
    <p>受託者　株式会社ゼータ映像</p></body></html>"""
    hit = _match(html, "観光プロモーション動画制作業務")
    assert hit is not None
    assert hit.company == "株式会社ゼータ映像"
    assert hit.source == "crawl:heading"


def test_経路2_表の勝者列から抽出する():
    html = """<html><head><title>委託業務の契約結果一覧</title></head><body>
    <table>
      <tr><th>案件名</th><th>受託者</th></tr>
      <tr><td>観光プロモーション動画制作業務</td><td>株式会社イータ広告</td></tr>
      <tr><td>別の全く違う案件</td><td>株式会社シータ</td></tr>
    </table></body></html>"""
    hit = _match(html, "観光プロモーション動画制作業務")
    assert hit is not None
    assert hit.company == "株式会社イータ広告"
    assert hit.source == "crawl:table"


def test_経路3_同一ブロック内の案件名と勝者ラベル():
    html = """<html><head><title>入札・契約情報</title></head><body>
    <ul><li>観光プロモーション動画制作業務　受託者　株式会社カッパ企画</li>
        <li>別の案件　受託者　株式会社ラムダ</li></ul></body></html>"""
    hit = _match(html, "観光プロモーション動画制作業務")
    assert hit is not None
    assert hit.company == "株式会社カッパ企画"
    assert hit.source == "crawl:block"


def test_新着リストに案件名が載るだけのページからは抽出しない():
    """ナビの新着一覧に案件名が出ているだけで、別案件の落札者を拾ってはいけない"""
    html = """<html><head><title>市からのお知らせ</title></head><body>
    <nav><ul><li><a href="/x.html">観光プロモーション動画制作業務の公募について</a></li></ul></nav>
    <div><h2>庁舎清掃業務の入札結果</h2><p>落札者　株式会社ミュー総合</p></div>
    </body></html>"""
    assert _match(html, "観光プロモーション動画制作業務") is None


def test_年度違いの旧ページからは抽出しない():
    html = """<html><head><title>令和5年度観光プロモーション動画制作業務の選定結果</title></head>
    <body><h1>令和5年度観光プロモーション動画制作業務の選定結果</h1>
    <p>受託者　株式会社ニュー映像</p></body></html>"""
    assert _match(html, "令和6年度観光プロモーション動画制作業務") is None


def test_表の次点列からは抽出しない():
    html = """<html><head><title>選定結果一覧</title></head><body>
    <table>
      <tr><th>案件名</th><th>次点者</th></tr>
      <tr><td>観光プロモーション動画制作業務</td><td>株式会社クサイ</td></tr>
    </table></body></html>"""
    assert _match(html, "観光プロモーション動画制作業務") is None
