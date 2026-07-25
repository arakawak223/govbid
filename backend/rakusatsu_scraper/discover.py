# -*- coding: utf-8 -*-
"""結果ページ発見モジュール: 検索エンジンで案件の結果ページを特定し落札企業を抽出する。"""
import re, sys, time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, unquote, urlparse
import fitz
sys.path.insert(0, '/tmp/claude-1000/-workspaces-govbid/ef35a61d-f5dd-4eb5-9dfb-6338a9ff2e0d/scratchpad')
from extract import find_winner, prep_text

H = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36'}
RESULT_HINT = ('kekka', 'sentei', 'senntei', 'senntei', 'shinsa', 'shinnsa', 'kohyo', 'result', '結果', '選定')

def norm(s):
    return re.sub(r'[\s　、。・,\.\-ー（）\(\)「」『』【】／/！!？?]+', '', str(s or ''))

def title_core(title):
    t = re.sub(r'^令和[０-９\d]+年度|^令和[０-９\d]+～[０-９\d]+年度|^R[０-９\d]+年度|^【.*?】', '', str(title))
    t = re.sub(r'（.*?）|\(.*?\)', '', t)
    t = re.sub(r'(に係る企画提案競技.*$|業務委託$|委託業務$|業務$|委託$|事業$|等$)', '', t)
    return norm(t)

def ddg_search(query, timeout=20):
    """DuckDuckGo HTML検索。結果URLのリストを返す。"""
    urls = []
    for ep in ('https://html.duckduckgo.com/html/', 'https://lite.duckduckgo.com/lite/'):
        try:
            r = requests.post(ep, data={'q': query}, headers=H, timeout=timeout)
            if r.status_code != 200:
                continue
            for m in re.findall(r'uddg=([^"&]+)', r.text):
                u = unquote(m)
                if u.startswith('http') and 'duckduckgo' not in u:
                    urls.append(u)
            if not urls:
                for u in re.findall(r'href="(https?://[^"]+)"', r.text):
                    if 'duckduckgo' not in u and 'google' not in u:
                        urls.append(u)
            if urls:
                break
        except Exception:
            continue
    # 重複除去（順序維持）
    seen, out = set(), []
    for u in urls:
        if u not in seen:
            seen.add(u); out.append(u)
    return out

def decode(raw):
    m = re.search(rb'charset=["\']?\s*([\w\-]+)', raw[:3000], re.I)
    encs = []
    if m:
        try: encs.append(m.group(1).decode('ascii'))
        except: pass
    for e in encs + ['utf-8', 'cp932', 'euc-jp']:
        try: return raw.decode(e, errors='strict')
        except (UnicodeDecodeError, LookupError): continue
    return raw.decode('utf-8', errors='ignore')

def page_text(raw):
    s = BeautifulSoup(decode(raw), 'html.parser')
    for t in s(['script', 'style']): t.decompose()
    txt = re.sub(r'[ \t　]+', ' ', s.get_text('\n'))
    return prep_text(re.sub(r'\n\s*\n+', '\n', txt))

def pdf_text(raw):
    try:
        d = fitz.open(stream=raw, filetype='pdf')
        return prep_text('\n'.join(p.get_text() for p in d[:6]))
    except Exception:
        return ''

def title_pos(core, textn):
    if len(core) < 6:
        return textn.find(core) if core else -1
    if core in textn:
        return textn.find(core)
    L = min(12, len(core))
    for i in range(0, len(core) - L + 1, 2):
        p = textn.find(core[i:i+L])
        if p >= 0:
            return p
    return -1

def discover_winner(name, orig_url='', pref='', timeout=18, pause=0.0):
    """検索で結果ページを探し、案件タイトル一致を確認して落札企業を抽出。"""
    core = title_core(name)
    dom = urlparse(orig_url).netloc if orig_url else ''
    # 検索クエリ（案件名を短縮しすぎない）
    q_name = re.sub(r'^令和[０-９\d]+年度|^R[０-９\d]+年度', '', str(name)).strip()
    queries = [f'{q_name} 結果', f'{q_name} 受託者 OR 落札 OR 選定結果']
    if pref:
        queries[0] = f'{q_name} 結果 {pref}'
    cands = []
    for q in queries:
        cands += ddg_search(q)
        if pause: time.sleep(pause)
        if len(cands) >= 12:
            break
    # ランク付け: 同一ドメイン優先 + 結果ヒント語 + タイトル一致
    scored = []
    seen = set()
    for u in cands:
        if u in seen: continue
        seen.add(u)
        sc = 0
        if dom and urlparse(u).netloc == dom: sc += 3
        ul = u.lower()
        if any(h in ul for h in RESULT_HINT): sc += 2
        # タイトル語がURL(パス)に含まれれば加点は難しいので低め
        scored.append((sc, u))
    scored.sort(reverse=True)
    for sc, u in scored[:8]:
        try:
            r = requests.get(u, headers=H, timeout=timeout)
            if r.status_code != 200:
                continue
            ct = r.headers.get('Content-Type', '')
            txt = pdf_text(r.content) if (u.lower().endswith('.pdf') or 'pdf' in ct) else page_text(r.content)
            tn = norm(txt)
            pos = title_pos(core, tn)
            if pos < 0:
                continue  # 案件が載っていないページは除外（誤検出防止）
            p3 = txt.find(core[:8])
            w = find_winner(txt, anchor=p3 if p3 >= 0 else 0, radius=len(txt))
            if w:
                ev = w[2]
                return {'winner': w[1], 'label': w[0], 'result_url': u, 'evidence': ev, 'source': 'search'}
        except Exception:
            continue
    return None
