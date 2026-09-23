# -*- coding: utf-8 -*-
"""落札企業の抽出コア。

スクレイピング運用で積み上げた知見をそのまま実装に落としたモジュール:

- 勝者ラベル（落札者 / 受託者 / 契約の相手方 …）の直後に来る企業名だけを採る
- 前株（株式会社◯◯）／後株（◯◯株式会社）の両対応、法人格直後のスペースも許容
- （株）㈱ 等の略記は抽出前に正式表記へ正規化する（prep_text）
- 「次点 / 次順位 / 参加業者」および募集要項の共同企業体ルール文は除外する
- 案件名の照合は core 正規化 + 60%以上（最低12文字）の部分一致まで
- 案件名に年度がある場合は本文にも同じ年度が必要（旧年度ページの誤採用防止）
"""
import re
from typing import Optional

# --------------------------------------------------------------------------
# 企業名の認識
# --------------------------------------------------------------------------
CORP = (r'株式会社|有限会社|合同会社|合資会社|合名会社|一般社団法人|公益社団法人|一般財団法人|'
        r'公益財団法人|社会福祉法人|特定非営利活動法人|ＮＰＯ法人|NPO法人|労働者協同組合|'
        r'農業協同組合|事業協同組合|協同組合|共同企業体|㈱|㈲')
_NC = r'一-鿿ァ-ヶぁ-んＡ-Ｚａ-ｚA-Za-z０-９0-9・ー々＆&'   # 名称に使える文字
_HEAD = r'一-鿿ァ-ヶＡ-Ｚａ-ｚA-Za-z々'                      # 名称の先頭に許す文字
# 後株: 名前(先頭は非ひらがな, 非貪欲)+法人格 / 前株: 法人格(+空白)+名前
_POST = r'[' + _HEAD + r'][' + _NC + r' ]{1,26}?(?:' + CORP + r')'
_PRE = r'(?:' + CORP + r')[ 　]?[' + _NC + r'][' + _NC + r' ]{1,28}'
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

_ABBREV = [
    ('（株）', '株式会社'), ('(株)', '株式会社'), ('㈱', '株式会社'),
    ('（有）', '有限会社'), ('(有)', '有限会社'), ('㈲', '有限会社'),
    ('（一社）', '一般社団法人'), ('（公社）', '公益社団法人'),
    ('（一財）', '一般財団法人'), ('（公財）', '公益財団法人'),
    ('（NPO）', '特定非営利活動法人'), ('（合同）', '合同会社'),
]


def prep_text(t: str) -> str:
    """略記の法人格を正式表記に正規化（（株）→株式会社 等）。抽出前に必ず適用する。"""
    for a, b in _ABBREV:
        t = t.replace(a, b)
    return t


def clean_name(name: str) -> str:
    name = name.strip(' 　:：・|\n')
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


# 勝者を示すラベル（この直後に企業名が来る）
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
# ラベル直後の文が募集要項の条件文なら除外（「共同企業体でも応募できる」等）
NEG_TAIL = re.compile(r'(応募|参加でき|とする|場合|資格|要件|なければ|求め|想定|でも可|に限る|の構成)')


def find_winner(text: str, anchor: int = 0, radius: Optional[int] = None):
    """text の anchor 近傍で「勝者ラベル→企業名」を抽出する。

    Returns:
        (label, company, evidence) または None
    """
    if radius is None:
        radius = len(text)
    lo, hi = max(0, anchor - 150), min(len(text), anchor + radius)
    seg = text[lo:hi]
    cands = []  # (anchored, gap, dist, label, name, pos)
    for lab in WIN_LABEL:
        for m in re.finditer(re.escape(lab), seg):
            pre = seg[max(0, m.start() - 4):m.start()]
            if NEG_PREFIX.search(pre):
                continue
            win0 = seg[m.end(): m.end() + 90]
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
            tail = win[nm.end(): nm.end() + 16]
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
    # アンカー一致 → ギャップ小 → 近接 の順で最良を選択
    cands.sort(key=lambda c: (c[0], c[1], c[2]))
    base = cands[0]
    best = base
    for c in cands:
        n, b = c[4], base[4]
        if c[0] == base[0] and (n.startswith(b) or b.startswith(n)) and len(n) > len(best[4]):
            best = c
    _, _, _, lab, name, pos = best
    ev = text[max(0, pos - 20): pos + 70].replace('\n', ' ')
    return (lab, name, ev)


# --------------------------------------------------------------------------
# 落札金額（明示ラベルがある場合のみ。推測はしない）
# --------------------------------------------------------------------------
AMOUNT_LABEL = re.compile(r'(落札金額|落札価格|落札額|契約金額|契約額|委託料|提案価格|契約価格)'
                          r'[^0-9０-９]{0,12}([0-9０-９,，]{3,20})\s*(千円|万円|円)')
_Z2H_NUM = str.maketrans('０１２３４５６７８９', '0123456789')


def find_amount(text: str) -> Optional[int]:
    """「落札金額 12,345,678円」のように明示されている場合のみ金額(円)を返す。"""
    m = AMOUNT_LABEL.search(text)
    if not m:
        return None
    digits = m.group(2).translate(_Z2H_NUM).replace(',', '').replace('，', '')
    if not digits.isdigit():
        return None
    value = int(digits)
    unit = m.group(3)
    if unit == '千円':
        value *= 1000
    elif unit == '万円':
        value *= 10000
    if value <= 0 or value > 100_000_000_000:
        return None
    return value


# --------------------------------------------------------------------------
# 案件名の正規化・照合
# --------------------------------------------------------------------------
def norm(s) -> str:
    return re.sub(r'[\s　、。・,\.\-ー（）\(\)「」『』【】／/！!？?]+', '', str(s or ''))


def norm_map(text: str):
    """正規化テキストと「正規化位置→原文位置」の対応表を返す。"""
    drop = set(' 　\t\n\r、。・,.-ー（）()「」『』【】／/！!？?')
    buf, idx = [], []
    for i, ch in enumerate(text):
        if ch in drop:
            continue
        buf.append(ch)
        idx.append(i)
    return ''.join(buf), idx


def title_core(title: str) -> str:
    """案件名から年度・括弧書き・定型語尾を落とした照合キー。"""
    t = re.sub(r'^令和[０-９\d]+年度|^令和[０-９\d]+～[０-９\d]+年度|^R[０-９\d]+年度|^\d{4}年度|^【.*?】', '', str(title))
    t = re.sub(r'（.*?）|\(.*?\)', '', t)
    t = t.replace('「', '').replace('」', '')
    t = re.sub(r'(に係る企画提案競技.*$|に係る公募型プロポーザル.*$|に係る提案競技.*$|に関する提案競技.*$|'
               r'の実施について$|について$|業務委託$|委託業務$|業務$|委託$|事業$|等$)', '', t)
    return norm(t)


def title_pos(core: str, ntext: str) -> int:
    """案件名 core の出現位置。完全一致優先、部分一致は core の60%以上(最低12文字)を要求。"""
    if not core or len(core) < 6:
        return -1
    if core in ntext:
        return ntext.find(core)
    length = max(12, int(len(core) * 0.6))
    if len(core) < length:
        return -1
    for i in range(0, len(core) - length + 1):
        p = ntext.find(core[i:i + length])
        if p >= 0:
            return p
    return -1


YEAR = re.compile(r'令和([０-９\d]+)年度|R([０-９\d]+)年度|(20[0-9]{2})年度')


def year_of(title: str):
    m = YEAR.search(str(title).translate(_Z2H_NUM))
    if not m:
        return None
    if m.group(1):
        return ('R', int(m.group(1)))
    if m.group(2):
        return ('R', int(m.group(2)))
    return ('W', int(m.group(3)))


def year_ok(case_title: str, text: str) -> bool:
    """案件名に年度がある場合、本文にも同じ年度表記があることを要求する。"""
    y = year_of(case_title)
    if not y:
        return True
    t = text.translate(_Z2H_NUM)
    if y[0] == 'R':
        west = 2018 + y[1]
        return (f'令和{y[1]}年' in t) or (f'R{y[1]}年' in t) or (f'{west}年' in t)
    return (f'{y[1]}年' in t) or (f'令和{y[1] - 2018}年' in t)


# --------------------------------------------------------------------------
# 企業名の名寄せキー（重複除去用）
# --------------------------------------------------------------------------
_CORP_STRIP = re.compile(r'(株式会社|有限会社|合同会社|合資会社|合名会社|一般社団法人|公益社団法人|'
                         r'一般財団法人|公益財団法人|社会福祉法人|特定非営利活動法人|ＮＰＯ法人|NPO法人|'
                         r'労働者協同組合|農業協同組合|事業協同組合|協同組合|共同企業体)')
_Z2H_ALNUM = str.maketrans(
    'ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ０１２３４５６７８９',
    'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789')


def company_key(name: str) -> str:
    """前株/後株・略記・記号の揺れを吸収した企業名キー。重複除去と検索に使う。"""
    s = prep_text(str(name or '')).translate(_Z2H_ALNUM)
    s = _CORP_STRIP.sub('', s)
    return norm(s).upper()
