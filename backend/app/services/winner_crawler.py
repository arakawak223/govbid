# -*- coding: utf-8 -*-
"""結果ページのサイト内クロール。

知見:
- 落札情報は公募URLとは別の「結果ページ」(`〇〇_kekka.html` / 結果PDF 等)に公表され、
  公募ページ自体は入札後に削除される（実測で404が半数前後）。よって公募URLを見るだけでは足りない。
- 検索エンジン（DDG/Bing/Google/Yahoo）はボット判定・429で実用にならない。
  代わりに案件URLの親ディレクトリ・サイトルート・入札公募ハブページを起点に
  同一ドメイン内を礼儀正しく巡回する。
- 誤検出対策が肝。ページ全文からの緩い抽出は、ナビの新着リストに案件名が載るだけで
  別案件の落札者を拾うため禁止。採用するのは次の3経路のみ:
    1. title / h1-h4 に案件名がある（＝ページの主題）→ ページ全体から抽出
    2. 表のヘッダに勝者列がある場合の、案件行の該当セル
    3. 同一ブロック(tr/li/p 等)内に案件名と勝者ラベルが共存
"""
import asyncio
import hashlib
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from app.config import get_settings
from app.services.winner_extract import (
    find_amount,
    find_winner,
    norm,
    norm_map,
    prep_text,
    title_core,
    title_pos,
    year_ok,
)

settings = get_settings()
logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"),
    "Accept-Language": "ja,en;q=0.9",
}

RES_KW = ('結果', '選定', '選考', '審査', '受託者', '落札', '決定', '採択', '公表', '契約', '相手方',
          '特定', '優先交渉', 'プロポーザル', '企画提案', '入札', '公募')
RES_URL = ('kekka', 'kekk', 'sentei', 'senntei', 'senko', 'senkou', 'shinsa', 'sinsa', 'sinnsa',
           'kohyo', 'result', 'propo', 'nyusatsu', 'nyuusatsu', 'keiyaku', 'kettei', 'koubo', 'kobo',
           'bid', 'chotatsu', 'jigyousha', 'business')

# 各サイトの入札・公募・結果一覧ハブ。クロールの起点に追加すると到達率が上がる。
HUB = {
    'www.pref.fukuoka.lg.jp': ['/soshiki/list8-1.html', '/life/10/71/380/', '/bid/', '/life/8/63/'],
    'www.pref.kumamoto.jp': ['/soshiki/list1-8.html', '/life/sub/5/'],
    'www.city.kumamoto.jp': ['/list04195.html', '/list04401.html'],
    'www.pref.oita.jp': ['/site/nyusatu-koubo/', '/site/nyusatu-koubo/list22380-29038.html',
                         '/soshiki/list14-1.html', '/life/sub/3/38/118/'],
    'www.pref.kagoshima.jp': ['/kensei/nyusatu/nyusatujoho/index.html', '/kensei/nyusatu/index.html'],
    'www.pref.okinawa.jp': ['/shigoto/nyusatsukeiyaku/1015342/1025064/1037584/',
                            '/shigoto/nyusatsukeiyaku/1015342/1025064/', '/shigoto/nyusatsukeiyaku/'],
    'www.pref.okinawa.lg.jp': ['/shigoto/nyusatsukeiyaku/', '/site/nyusatsu/'],
    'www.pref.nagasaki.jp': ['/nyusatsu-docs/', '/object/nyusatsu-chotatsujoho/gyomuitakukekka/index.html',
                             '/bunrui/kenseijoho/nyusatsu-chotatsujoho/'],
    'www.pref.yamaguchi.lg.jp': ['/soshiki/list8-1.html', '/life/sub/5/',
                                 '/cms/a10600/proposal/shinsakekka.html', '/soshiki/177/156742.html'],
    'www.pref.saga.lg.jp': ['/list00631.html', '/list02043.html', '/list03583.html'],
    'www.pref.miyazaki.lg.jp': ['/kense/chotatsu/', '/site/nyusatsu/'],
}

PAGING = re.compile(r'(list\d|/list|ichiran|[?&](p|page|pageno|start|offset)=)', re.I)
SKIP_EXT = re.compile(r'\.(jpg|jpeg|png|gif|svg|webp|zip|lzh|xls|xlsx|doc|docx|ppt|pptx|csv|mp4|mp3|ics|rss|xml)$', re.I)

WIN_HEAD = re.compile(r'(落札者|落札業者|落札事業者|受託者|受託事業者|受託候補者|受注者|受注候補者|'
                      r'契約の相手方|契約相手方|相手方|選定事業者|選定業者|選定者|最優秀提案者|最優秀者|'
                      r'優先交渉権者|委託先|委託事業者|決定者|特定事業者)')
NEG_HEAD = re.compile(r'(次点|次順位|参加|応募|落選|補欠)')
CORP_RE = re.compile(r'(株式会社|有限会社|合同会社|合資会社|一般社団法人|公益社団法人|一般財団法人|'
                     r'公益財団法人|社会福祉法人|特定非営利活動法人|ＮＰＯ法人|NPO法人|協同組合|'
                     r'共同企業体|企業体|㈱|㈲|会社|法人|組合|事務所|研究所|センター|新聞社|放送)')


@dataclass
class CaseTarget:
    """落札企業を探す対象の案件"""
    key: str            # bids.id
    title: str
    url: str            # 公告URL
    municipality: str
    core: str = ""

    def __post_init__(self):
        if not self.core:
            self.core = title_core(self.title)


@dataclass
class WinnerHit:
    """検出した落札企業"""
    key: str
    company: str
    label: str
    result_url: str
    evidence: str
    source: str                     # announcement / crawl:heading / crawl:table / crawl:block
    amount: Optional[int] = None


@dataclass
class CrawlStats:
    fetched: int = 0
    domains: int = 0
    errors: list[str] = field(default_factory=list)


def _decode(raw: bytes) -> str:
    m = re.search(rb'charset=["\']?\s*([\w\-]+)', raw[:4000], re.I)
    encs = []
    if m:
        try:
            encs.append(m.group(1).decode('ascii'))
        except Exception:
            pass
    for e in encs + ['utf-8', 'cp932', 'euc-jp']:
        try:
            return raw.decode(e, errors='strict')
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode('utf-8', errors='ignore')


def _pdf_text(raw: bytes) -> str:
    """PDF公表分。PyMuPDF未導入の環境ではスキップする。"""
    try:
        import fitz  # type: ignore
    except ImportError:
        return ''
    try:
        doc = fitz.open(stream=raw, filetype='pdf')
        return prep_text('\n'.join(p.get_text() for p in doc[:10]))
    except Exception:
        return ''


def _txt(el) -> str:
    return prep_text(re.sub(r'[ \t　]+', ' ', el.get_text(' ', strip=True)))


class WinnerCrawler:
    """1ドメインずつ礼儀正しく巡回し、案件名照合で落札企業を抽出する。"""

    def __init__(
        self,
        delay: float | None = None,
        max_pages_per_domain: int | None = None,
        cache_dir: str | None = None,
    ):
        self.delay = delay if delay is not None else settings.winner_crawl_delay_seconds
        self.max_pages = max_pages_per_domain or settings.winner_max_pages_per_domain
        self.cache_dir = cache_dir if cache_dir is not None else settings.winner_cache_dir
        if self.cache_dir:
            os.makedirs(self.cache_dir, exist_ok=True)
        self.stats = CrawlStats()
        self._mem_cache: dict[str, bytes | None] = {}

    # ---------------------------------------------------------------- fetch
    async def _get(self, client: httpx.AsyncClient, url: str) -> tuple[Optional[bytes], bool]:
        """(content, was_cached) を返す。取得失敗時は (None, cached?)。"""
        if url in self._mem_cache:
            return self._mem_cache[url], True

        path = None
        if self.cache_dir:
            path = os.path.join(self.cache_dir, 'c_' + hashlib.md5(url.encode()).hexdigest())
            if os.path.exists(path):
                with open(path, 'rb') as f:
                    raw = f.read()
                self._mem_cache[url] = raw
                return raw, True

        try:
            r = await client.get(url, headers=HEADERS, timeout=25.0, follow_redirects=True)
        except Exception as e:
            logger.debug(f"fetch failed {url}: {e}")
            self._mem_cache[url] = None
            return None, False
        if r.status_code != 200 or len(r.content) > 12_000_000:
            self._mem_cache[url] = None
            return None, False
        raw = r.content
        self._mem_cache[url] = raw
        if path:
            tmp = f'{path}.{os.getpid()}.tmp'
            try:
                with open(tmp, 'wb') as f:
                    f.write(raw)
                os.replace(tmp, path)
            except OSError:
                pass
        return raw, False

    # ---------------------------------------------------------------- match
    def match_cases(
        self,
        text: str,
        url: str,
        cases: list[CaseTarget],
        hits: dict[str, WinnerHit],
        soup: Optional[BeautifulSoup] = None,
    ) -> None:
        """ページ内で案件を照合する。採用するのは見出し／表の勝者列／同一ブロックの3経路のみ。"""
        ntext, idx = norm_map(text)
        if len(ntext) < 30 and soup is None:
            return

        # --- 経路1: ページ主題（title/h1-h4）に案件名 → ページ全体から抽出
        heads = ''
        if soup is not None:
            hs = [soup.title.get_text(' ', strip=True) if soup.title else '']
            hs += [h.get_text(' ', strip=True) for h in soup.find_all(['h1', 'h2', 'h3', 'h4'])]
            heads = norm(prep_text(' '.join(hs)))
        for c in cases:
            if c.key in hits:
                continue
            if heads and title_pos(c.core, heads) >= 0:
                p = title_pos(c.core, ntext)
                anchor = idx[p] if 0 <= p < len(idx) else 0
                w = find_winner(text, anchor=anchor, radius=len(text))
                if w and year_ok(c.title, text):
                    hits[c.key] = WinnerHit(c.key, w[1], w[0], url, w[2], 'crawl:heading',
                                            find_amount(text))
        if soup is None:
            return

        # --- 経路2: 表（ヘッダに勝者列がある場合、案件行の該当セル）
        for tbl in soup.find_all('table'):
            rows = tbl.find_all('tr')
            if len(rows) < 2:
                continue
            hdr = [_txt(td) for td in rows[0].find_all(['th', 'td'])]
            wcol = None
            for j, h in enumerate(hdr):
                if WIN_HEAD.search(h) and not NEG_HEAD.search(h):
                    wcol = j
                    break
            if wcol is None:
                continue
            for tr in rows[1:]:
                tds = tr.find_all(['th', 'td'])
                if len(tds) <= wcol:
                    continue
                row_text = _txt(tr)
                rown = norm(row_text)
                for c in cases:
                    if c.key in hits:
                        continue
                    if title_pos(c.core, rown) < 0:
                        continue
                    cand = _txt(tds[wcol]).strip(' 　:：・|')
                    if not (3 <= len(cand) <= 60) or not CORP_RE.search(cand):
                        continue
                    if not year_ok(c.title, row_text + ' ' + text[:2000]):
                        continue
                    hits[c.key] = WinnerHit(c.key, cand, hdr[wcol][:20], url, row_text[:160],
                                            'crawl:table', find_amount(row_text))

        # --- 経路3: 行・リスト・段落内で案件名と勝者ラベルが同一ブロックに存在
        for el in soup.find_all(['tr', 'li', 'p', 'dd', 'dl', 'div', 'section']):
            if el.find(['tr', 'li', 'table']):
                continue
            bt = _txt(el)
            if len(bt) < 12 or len(bt) > 1200:
                continue
            btn = norm(bt)
            for c in cases:
                if c.key in hits:
                    continue
                if title_pos(c.core, btn) < 0:
                    continue
                w = find_winner(bt, anchor=0, radius=len(bt))
                if w and year_ok(c.title, bt + ' ' + text[:2000]):
                    hits[c.key] = WinnerHit(c.key, w[1], w[0], url, bt[:160], 'crawl:block',
                                            find_amount(bt))

    # ---------------------------------------------------------------- crawl
    def _seeds(self, domain: str, cases: list[CaseTarget]) -> list[tuple[int, str]]:
        """起点URL。公告URL自体 → 親ディレクトリ → サイトルート → ハブページ。"""
        seeds: list[tuple[int, str]] = []
        seen: set[str] = set()

        def add(prio: int, url: str):
            if url and url not in seen:
                seen.add(url)
                seeds.append((prio, url))

        for path in HUB.get(domain, []):
            add(-5, f'https://{domain}{path}')
        for c in cases:
            pu = urlparse(c.url)
            base = f'{pu.scheme}://{pu.netloc}'
            add(-20, c.url)  # 公募ページに結果が追記されているケース
            parts = [p for p in pu.path.split('/') if p]
            for k in range(len(parts) - 1, max(-1, len(parts) - 4), -1):
                add(-1, base + '/' + '/'.join(parts[:k]) + ('/' if k else ''))
            add(0, base + '/')
        return seeds

    async def crawl_domain(
        self,
        client: httpx.AsyncClient,
        domain: str,
        cases: list[CaseTarget],
        max_pages: int | None = None,
    ) -> dict[str, WinnerHit]:
        hits: dict[str, WinnerHit] = {}
        cap = max_pages or self.max_pages
        queue = self._seeds(domain, cases)
        seen = {u for _, u in queue}
        fetched = 0

        while queue and fetched < cap and len(hits) < len(cases):
            queue.sort(key=lambda x: x[0])
            _, url = queue.pop(0)
            raw, was_cached = await self._get(client, url)
            if not was_cached:
                fetched += 1
                self.stats.fetched += 1
                await asyncio.sleep(self.delay)
            if not raw:
                continue

            if raw[:5] == b'%PDF-' or url.lower().endswith('.pdf'):
                txt = _pdf_text(raw)
                if txt:
                    self.match_cases(txt, url, cases, hits)
                continue

            html = _decode(raw)
            try:
                soup = BeautifulSoup(html, 'lxml')
            except Exception:
                soup = BeautifulSoup(html, 'html.parser')
            for t in soup(['script', 'style']):
                t.decompose()
            text = prep_text(re.sub(r'\n\s*\n+', '\n', re.sub(r'[ \t　]+', ' ', soup.get_text('\n'))))
            self.match_cases(text, url, cases, hits, soup=soup)
            if len(hits) >= len(cases):
                break

            # リンク展開: 案件タイトル一致 > 結果系キーワード > 一覧/ページング > 結果系URL語
            for a in soup.find_all('a', href=True):
                href = urljoin(url, a['href'].strip()).split('#')[0]
                if not href.startswith('http'):
                    continue
                if urlparse(href).netloc != domain:
                    continue
                if SKIP_EXT.search(href) or href in seen:
                    continue
                at = a.get_text(' ', strip=True)
                atn = norm(at)
                score = None
                for c in cases:
                    if c.key in hits:
                        continue
                    cc = c.core
                    if len(cc) >= 8 and (cc[:10] in atn or (len(atn) >= 8 and atn[:8] in cc)):
                        score = -10
                        break
                if score is None:
                    if any(k in at for k in RES_KW):
                        score = -3
                    elif PAGING.search(href):
                        score = -2
                    elif any(k in href.lower() for k in RES_URL):
                        score = -1
                if score is None:
                    continue
                if href.lower().endswith('.pdf') and score > -10 and '結果' not in at:
                    continue
                seen.add(href)
                queue.append((score, href))

        logger.info(f"[{domain}] cases={len(cases)} fetched={fetched} hits={len(hits)}")
        return hits

    async def crawl(
        self,
        cases: list[CaseTarget],
        max_concurrent_domains: int | None = None,
    ) -> list[WinnerHit]:
        """案件をドメインごとに束ねて並列クロールする（ドメイン内は逐次＝負荷を抑える）。"""
        by_domain: dict[str, list[CaseTarget]] = {}
        for c in cases:
            dom = urlparse(c.url).netloc
            if dom:
                by_domain.setdefault(dom, []).append(c)
        self.stats.domains = len(by_domain)
        order = sorted(by_domain.items(), key=lambda kv: -len(kv[1]))
        limit = max_concurrent_domains or settings.winner_max_domains_concurrent
        sem = asyncio.Semaphore(limit)

        async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=25.0) as client:
            async def run(domain: str, group: list[CaseTarget]):
                n = len(group)
                cap = min(self.max_pages, 600 if n > 40 else (400 if n > 20 else max(150, 40 * n)))
                async with sem:
                    try:
                        return await self.crawl_domain(client, domain, group, max_pages=cap)
                    except Exception as e:
                        msg = f"{domain}: {type(e).__name__} {str(e)[:80]}"
                        logger.error(f"crawl error {msg}")
                        self.stats.errors.append(msg)
                        return {}

            results = await asyncio.gather(*[run(d, g) for d, g in order])

        hits: list[WinnerHit] = []
        for r in results:
            hits.extend(r.values())
        return hits
