# -*- coding: utf-8 -*-
"""落札企業抽出ロジック（前株/後株対応・勝者ラベル限定）。scrape系から共通利用。"""
import re

CORP = (r'株式会社|有限会社|合同会社|合資会社|合名会社|一般社団法人|公益社団法人|一般財団法人|'
        r'公益財団法人|社会福祉法人|特定非営利活動法人|ＮＰＯ法人|NPO法人|労働者協同組合|'
        r'農業協同組合|事業協同組合|協同組合|共同企業体|㈱|㈲')
# 後株: 名前(かな含む)+法人格 / 前株: 法人格+名前(かな除く先頭)
_NC   = r'一-鿿ァ-ヶぁ-んＡ-Ｚａ-ｚA-Za-z０-９0-9・ー々＆&'  # 名称に使える文字
_HEAD = r'一-鿿ァ-ヶＡ-Ｚａ-ｚA-Za-z々'  # 名称の先頭に許す文字（ひらがな/数字/空白は除外）
# 後株: 名前(先頭は非ひらがな, 非貪欲)+法人格。前株: 法人格(+空白)+名前(貪欲、後でクリーン)
_POST = r'[' + _HEAD + r'][' + _NC + r' ]{1,26}?(?:' + CORP + r')'
_PRE  = r'(?:' + CORP + r')[ 　]?[' + _NC + r'][' + _NC + r' ]{1,28}'
NAME = re.compile(r'(?:' + _PRE + r'|' + _POST + r')')
# ラベル直後の接続句を除去して名称先頭に寄せる
LEAD = re.compile(
    r'^[のはをがとして、。・：:\s　（(）)「『【\|]*'
    r'(?:(?:の|は)?(?:商号|称号)(?:又は|または)?名称|の名称|事業者名|団体名|会社名|商号|'
    r'として決定した者|に決定した者|候補者|の商号|又は名称|または名称)?'
    r'[のはをがとして、。・：:\s　（(）)「『【\|]*')
# 名称の途中で切る停止トークン（法人格を含む部分は残す）
STOP_TOK = re.compile(r'(令和|平成|所在地|代表者|代表取締役|代表者職|住所|得点|評価|提案者|審査|'
                      r'点数|順位|商号又は|称号又は|又は名称|提案|参加|次点|次順位|様方|殿|[0-9０-９]|、|。|（|\(|【|「)')

_LEADTOK = re.compile(r'^(?:商号(?:又は|または)?名称|称号(?:又は|または)?名称|又は名称|または名称|'
                      r'の名称|名称|事業者名|会社名|団体名|商号|所在地|住所|代表者(?:職氏名)?)[ 　:：・]*')
_INVALID = re.compile(r'^(?:県が|市が|町が|村が|本業務|当該|同社|なお|また|その他)')

def prep_text(t):
    """略記の法人格を正式表記に正規化（（株）→株式会社 等）。抽出前に適用。"""
    for a, b in [('（株）', '株式会社'), ('(株)', '株式会社'), ('㈱', '株式会社'),
                 ('（有）', '有限会社'), ('(有)', '有限会社'), ('㈲', '有限会社'),
                 ('（一社）', '一般社団法人'), ('（公社）', '公益社団法人'),
                 ('（一財）', '一般財団法人'), ('（公財）', '公益財団法人'),
                 ('（NPO）', '特定非営利活動法人'), ('（合同）', '合同会社')]:
        t = t.replace(a, b)
    return t

def clean_name(name):
    name = name.strip(' 　:：・|\n　')
    # 名称先頭に残る属性ラベルを除去（最大2回）
    for _ in range(2):
        n2 = _LEADTOK.sub('', name)
        if n2 == name:
            break
        name = n2.strip(' 　:：・')
    m = STOP_TOK.search(name, 3)
    if m and m.start() >= 3 and re.search(CORP, name[:m.start()]):
        name = name[:m.start()]
    name = name.strip(' 　・|\n:：')
    if _INVALID.match(name):
        return ''  # 説明文由来の誤検出
    return name

# 勝者を示すラベル（この直後に企業名）
WIN_LABEL = [
    '落札者', '落札業者', '落札企業', '落札事業者', '落札候補者', '落札決定者',
    '受託者', '受託事業者', '受託候補者', '受託予定者', '委託先', '委託事業者',
    '委託候補事業者', '委託候補者', '契約の相手方', '契約相手方', '契約締結先',
    '選定事業者', '選定した事業者', '特定事業者', '最優秀提案者', '最優秀受託候補者',
    '最優秀者', '優先交渉権者', '第一交渉権者', '採択事業者', '受注者', '受注候補者',
    '決定した者', '決定しました', '特定しました', '選定しました',
]
# ラベル直前がこれらなら「敗者/参加者リスト」→除外
NEG_PREFIX = re.compile(r'(次点|次順位|次々点|参加|応募|落選|補欠|第[二三四2-4]|次席)$')
NEG_TAIL = re.compile(r'(応募|参加でき|とする|場合|資格|要件|なければ|求め|想定|でも可|に限る|の構成)')

def find_winner(text, anchor=0, radius=None):
    """textのanchor近傍で勝者ラベル→企業名を抽出。(label,name,evidence)またはNone。"""
    if radius is None:
        radius = len(text)
    lo, hi = max(0, anchor - 150), min(len(text), anchor + radius)
    seg = text[lo:hi]
    cands = []  # (dist_to_anchor, label, name, pos)
    for lab in WIN_LABEL:
        for m in re.finditer(re.escape(lab), seg):
            pre = seg[max(0, m.start()-4):m.start()]
            if NEG_PREFIX.search(pre):
                continue
            win0 = seg[m.end(): m.end()+90]
            win = LEAD.sub('', win0)  # 接続句を除去して名称先頭に寄せる
            # ラベル直後に企業名が来る（アンカー一致）を優先。分断時のみ探索。
            nm = NAME.match(win)
            anchored = 0 if nm else 1
            if not nm:
                nm = NAME.search(win[:75])
            if not nm:
                continue
            name = clean_name(nm.group(0))
            if not name:
                continue
            tail = win[nm.end(): nm.end()+16]
            if NEG_TAIL.search(tail):
                continue
            if not (4 <= len(name) <= 46):
                continue
            # 探索一致時、企業名先頭までのスキップ量が大きい（間にラベル文）なら減点
            gap = win.find(nm.group(0)) if anchored else win[:75].find(nm.group(0))
            dist = abs(m.start() - (anchor - lo))
            cands.append((anchored, gap, dist, lab, name, lo + m.start()))
    if not cands:
        return None
    # アンカー一致→ギャップ小→近接 の順で最良を選択。
    cands.sort(key=lambda c: (c[0], c[1], c[2]))
    base = cands[0]
    best = base
    for c in cands:
        n, b = c[4], base[4]
        if c[0] == base[0] and (n.startswith(b) or b.startswith(n)) and len(n) > len(best[4]):
            best = c
    _, _, _, lab, name, pos = best
    ev = text[max(0, pos-20): pos+70].replace('\n', ' ')
    return (lab, name, ev)
