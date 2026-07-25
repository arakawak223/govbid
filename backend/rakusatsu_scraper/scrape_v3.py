#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生存URL対象・案件タイトル照合型の落札企業抽出（誤検出対策版）。"""
import re, csv, json, sys
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
import fitz
sys.path.insert(0, '/tmp/claude-1000/-workspaces-govbid/ef35a61d-f5dd-4eb5-9dfb-6338a9ff2e0d/scratchpad')
from extract import find_winner, prep_text

HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; ResearchBot/1.0)'}
SP = '/tmp/claude-1000/-workspaces-govbid/ef35a61d-f5dd-4eb5-9dfb-6338a9ff2e0d/scratchpad'

WIN_LABEL = ['落札者', '落札業者', '落札企業', '落札事業者', '落札候補者', '落札決定者', '落札(候補)者',
             '受託者', '受託事業者', '受託候補者', '受託予定者', '受託業者', '委託先', '委託業者', '委託事業者',
             '契約の相手方', '契約相手方', '契約者', '契約締結先', '選定事業者', '選定業者', '選定者', '特定者',
             '特定事業者', '最優秀提案者', '最優秀者', '最優秀', '優先交渉権者', '第一交渉権者', '交渉権者',
             '採択事業者', '採択者', '採択団体', '提案者', '事業者名', '業者名', '会社名', '団体名',
             '受注者', '選定した事業者', '特定しました', '決定しました']
# 企業名の後に続くと「募集要項の文」を示す語（偽陽性）
NEG_CTX = re.compile(r'(応募|参加|できる|とする|場合|資格|要件|なければ|求め|想定|でも可|とみなす|に限る|の構成|旨と|を代表)')
LINK_KW = ['結果', '落札', '選定', '選考', '審査結果', '受託', '採択', '相手方', '公表', '特定']
NAME = re.compile(
    r'(?:株式会社|有限会社|合同会社|一般社団法人|公益社団法人|一般財団法人|公益財団法人|'
    r'特定非営利活動法人|ＮＰＯ法人|NPO法人|㈱|㈲)?'
    r'[぀-ヿ一-鿿A-Za-zＡ-Ｚａ-ｚ0-9０-９・ー\-&＆]{1,32}?'
    r'(?:株式会社|有限会社|合同会社|合資会社|一般社団法人|公益社団法人|一般財団法人|公益財団法人|'
    r'特定非営利活動法人|ＮＰＯ法人|NPO法人|協同組合|農業協同組合|共同企業体|事業協同組合|㈱|㈲)'
    r'[一-鿿ァ-ヶＡ-Ｚａ-ｚA-Za-z0-9０-９・ー]{0,20}')
STOP_SUFFIX = re.compile(r'(に係る企画提案競技.*$|に係る公募型プロポーザル.*$|に関する.*$|業務委託$|委託業務$|業務$|委託$|事業$|の実施$|等$)')

def norm(s):
    return re.sub(r'[\s　、。・,\.\-ー（）\(\)「」『』【】／/]+', '', s or '')

def title_core(title):
    t = re.sub(r'^令和[０-９\d]+年度|^令和[０-９\d]+～[０-９\d]+年度|^R[０-９\d]+年度|^\d{4}年度|^【.*?】', '', title)
    t = re.sub(r'（.*?）|\(.*?\)', '', t)
    t = STOP_SUFFIX.sub('', t)
    return norm(t)

def title_in_text(core, textn):
    """案件タイトル(core)がテキストに含まれるか。長い場合は部分一致を許容。位置を返す。"""
    if len(core) < 6:
        return textn.find(core) if core else -1
    if core in textn:
        return textn.find(core)
    # 部分一致: coreの連続10文字スライスがあるか
    L = min(12, len(core))
    for i in range(0, len(core) - L + 1, 2):
        sl = core[i:i+L]
        p = textn.find(sl)
        if p >= 0:
            return p
    return -1

def winner_near(text, pos, radius=500):
    """textのpos近傍で、落札ラベルの後にある企業名を抽出。"""
    lo, hi = max(0, pos - 120), min(len(text), pos + radius)
    seg = text[lo:hi]
    best = None
    for lab in WIN_LABEL:
        for m in re.finditer(re.escape(lab), seg):
            win = seg[m.end(): m.end()+70]
            nm = NAME.search(win)
            if nm:
                name = nm.group(0).strip(' 　:：・|')
                # 企業名直後が募集要項文なら偽陽性として除外
                tail = win[nm.end(): nm.end()+18]
                if NEG_CTX.search(name) or NEG_CTX.search(tail):
                    continue
                if 4 <= len(name) <= 42:
                    d = abs(m.start() - (pos - lo))
                    if best is None or d < best[2]:
                        best = (lab, name, d)
    return (best[0], best[1]) if best else None

def decode(raw):
    m = re.search(rb'charset=["\']?\s*([\w\-]+)', raw[:3000], re.I)
    encs = []
    if m:
        try: encs.append(m.group(1).decode('ascii'))
        except: pass
    encs += ['utf-8', 'cp932', 'euc-jp']
    for e in encs:
        try: return raw.decode(e, errors='strict')
        except (UnicodeDecodeError, LookupError): continue
    return raw.decode('utf-8', errors='ignore')

def page_text(content):
    soup = BeautifulSoup(decode(content), 'html.parser')
    for t in soup(['script', 'style']): t.decompose()
    txt = re.sub(r'[ \t　]+', ' ', soup.get_text('\n'))
    return prep_text(re.sub(r'\n\s*\n+', '\n', txt)), soup

def pdf_text(content):
    try:
        doc = fitz.open(stream=content, filetype='pdf')
        return '\n'.join(p.get_text() for p in doc[:6])
    except Exception:
        return ''

def get(url, timeout=25):
    return requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)

def analyze(row):
    url = row['URL']; core = title_core(row['イベント名'])
    res = {'row': row['row'], '都道府県': row['都道府県'], 'イベント名': row['イベント名'],
           '委託料上限': row['委託料上限'], 'URL': url, 'result_url': '',
           'winner': '', 'label': '', 'source': '', 'evidence': '', 'note': ''}
    try:
        r = get(url)
        if r.status_code != 200:
            res['note'] = f'HTTP {r.status_code}'; return res
        text, soup = page_text(r.content)
        textn = norm(text)
        # 案件ページ本体: タイトル位置近傍で抽出（タイトルが見つからなければ全体探索）
        posn = title_in_text(core, textn)
        head = core[:8]
        p2 = text.find(head) if head else -1
        w = None
        if p2 >= 0:
            w = find_winner(text, anchor=p2, radius=900)
        if not w:
            w = find_winner(text, 0)  # 単一案件ページ想定
        if w:
            res.update(winner=w[1], label=w[0], source='page', result_url=url, evidence=w[2])
            return res
        # 別ページ/PDF追跡: 案件タイトル語を含む結果系リンクのみ
        cand = []
        for a in soup.find_all('a', href=True):
            at = a.get_text().strip(); atn = norm(at)
            href = urljoin(url, a['href'])
            has_res = any(k in at for k in LINK_KW) or href.lower().endswith('.pdf')
            if not has_res:
                continue
            # タイトル一致度
            ov = 0
            if len(core) >= 6:
                for i in range(0, max(1, len(core)-7), 2):
                    if core[i:i+8] in atn: ov += 1
            elif core and core in atn:
                ov = 3
            if ov >= 1:
                cand.append((ov, href, at[:30]))
        cand.sort(reverse=True)
        for ov, href, at in cand[:5]:
            try:
                rr = get(href)
                if rr.status_code != 200: continue
                ct = rr.headers.get('Content-Type','')
                if href.lower().endswith('.pdf') or 'pdf' in ct:
                    txt = pdf_text(rr.content); src='pdf'
                else:
                    txt, _ = page_text(rr.content); src='link'
                tn = norm(txt)
                pos = title_in_text(core, tn)
                if pos < 0:
                    continue  # このページに案件が無ければスキップ（誤検出防止）
                p3 = txt.find(core[:8])
                w = find_winner(txt, anchor=p3 if p3>=0 else 0, radius=900)
                if w:
                    res.update(winner=w[1], label=w[0], source=src, result_url=href, evidence=w[2])
                    return res
            except Exception:
                continue
        res['note'] = 'no winner (alive)'
    except Exception as e:
        res['note'] = f'{type(e).__name__}: {str(e)[:50]}'
    return res

def main():
    rows = list(csv.DictReader(open(f'{SP}/targets.csv', encoding='utf-8')))
    status = json.load(open(f'{SP}/status.json'))
    alive = [r for r in rows if str(status.get(r['URL'])) == '200']
    print(f'alive: {len(alive)}', file=sys.stderr)
    out = []
    with ThreadPoolExecutor(max_workers=10) as ex:
        futs = {ex.submit(analyze, r): r for r in alive}
        for i, f in enumerate(as_completed(futs), 1):
            out.append(f.result())
            if i % 40 == 0: print(f'  {i}/{len(alive)}', file=sys.stderr)
    out.sort(key=lambda x: int(x['row']))
    json.dump(out, open(f'{SP}/scrape_v3.json','w'), ensure_ascii=False, indent=1)
    found = [o for o in out if o['winner']]
    from collections import Counter
    cnt = Counter(o['source'] for o in found)
    print(f'\n検出 {len(found)}/{len(alive)}  src={dict(cnt)}', file=sys.stderr)
    for o in found:
        print(f"  [{o['source']}] {o['都道府県']} | {o['イベント名'][:24]} -> {o['winner']}  «{o['label']}»")

if __name__ == '__main__':
    main()
