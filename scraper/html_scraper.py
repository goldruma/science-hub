# -*- coding: utf-8 -*-
"""
범용 게시판(공지사항) 스크레이퍼.

한국 기관 홈페이지 게시판은 대부분 아래 셋 중 하나의 뼈대를 씁니다.
  1) <table><tbody><tr><td><a>제목</a></td>...<td>날짜</td></tr>...
  2) <ul><li><a>제목</a>...<span>날짜</span></li>...
  3) 그 외 커스텀 CMS: <a href="...View.do?...">제목</a> 형태로 흩어져 있음

이 스크레이퍼는 위 세 패턴을 순서대로 시도하고, config에 selectors가
명시돼 있으면 그것을 최우선으로 사용합니다.

⚠️ 주의: 사이트 구조는 예고 없이 바뀝니다. 새 소스를 추가하거나 결과가
비어 있으면 `python main.py --test <source_id>` 로 먼저 점검하세요.
"""
import re
import time
import logging
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger("html_scraper")

HEADERS = {
    # 일부 학교/기관 서버는 브라우저 UA가 없으면 차단하거나 빈 페이지를 준다.
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 "
        "ScienceActivityHubBot/1.0 (+educational, non-commercial aggregator)"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.5",
}

REQUEST_TIMEOUT = 12
DATE_RE = re.compile(r"(20\d{2}|\d{2})[.\-/]\s?\d{1,2}[.\-/]\s?\d{1,2}")
MIN_TITLE_LEN = 6
MAX_TITLE_LEN = 140
MAX_ITEMS_PER_SOURCE = 15

# 메뉴/푸터/광고 등 공지가 아닐 확률이 높은 텍스트를 걸러내기 위한 블랙리스트
NOISE_WORDS = ["로그인", "회원가입", "sitemap", "quick menu", "바로가기", "이전", "다음",
               "처음", "끝으로", "개인정보", "이용약관", "copyright"]


def fetch(url: str) -> BeautifulSoup | None:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or resp.encoding
        return BeautifulSoup(resp.text, "html.parser")
    except requests.RequestException as e:
        logger.warning("요청 실패 %s : %s", url, e)
        return None


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _looks_like_noise(title: str) -> bool:
    low = title.lower()
    return any(w in low for w in NOISE_WORDS) or len(title) < MIN_TITLE_LEN


def _extract_with_custom_selectors(soup: BeautifulSoup, base_url: str, selectors: dict):
    rows = soup.select(selectors["row"])
    out = []
    for row in rows:
        title_el = row.select_one(selectors.get("title", "a"))
        link_el = row.select_one(selectors.get("link", "a"))
        date_el = row.select_one(selectors.get("date")) if selectors.get("date") else None
        if not title_el or not link_el:
            continue
        title = _clean(title_el.get_text())
        href = link_el.get("href", "")
        if not title or not href:
            continue
        out.append({
            "title": title,
            "link": urljoin(base_url, href),
            "date_raw": _clean(date_el.get_text()) if date_el else "",
        })
    return out


def _extract_table_rows(soup: BeautifulSoup, base_url: str):
    out = []
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        for tr in rows:
            a = tr.find("a")
            if not a:
                continue
            title = _clean(a.get_text())
            href = a.get("href", "")
            if not title or not href or _looks_like_noise(title):
                continue
            if len(title) > MAX_TITLE_LEN:
                continue
            date_raw = ""
            for td in tr.find_all("td"):
                txt = _clean(td.get_text())
                if DATE_RE.search(txt):
                    date_raw = DATE_RE.search(txt).group(0)
                    break
            out.append({"title": title, "link": urljoin(base_url, href), "date_raw": date_raw})
    return out


def _extract_list_items(soup: BeautifulSoup, base_url: str):
    out = []
    for ul in soup.find_all(["ul", "ol"]):
        for li in ul.find_all("li", recursive=False):
            a = li.find("a")
            if not a:
                continue
            title = _clean(a.get_text())
            href = a.get("href", "")
            if not title or not href or _looks_like_noise(title):
                continue
            if len(title) > MAX_TITLE_LEN:
                continue
            date_match = DATE_RE.search(_clean(li.get_text()))
            out.append({
                "title": title,
                "link": urljoin(base_url, href),
                "date_raw": date_match.group(0) if date_match else "",
            })
    return out


def _extract_loose_links(soup: BeautifulSoup, base_url: str):
    """최후의 수단: view.do / bbs / board / notice / seq= 등 게시글 상세로
    보이는 href 패턴을 가진 <a> 태그를 모두 훑는다."""
    view_pattern = re.compile(r"(view|detail|read|bbs|board|notice|seq|no=)", re.I)
    out = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not view_pattern.search(href):
            continue
        title = _clean(a.get_text())
        if not title or _looks_like_noise(title) or len(title) > MAX_TITLE_LEN:
            continue
        out.append({"title": title, "link": urljoin(base_url, href), "date_raw": ""})
    return out


def scrape_source(source: dict) -> list:
    """source(config dict)를 받아 [{title, link, date_raw}, ...] 반환.
    실패하거나 결과가 없으면 빈 리스트를 반환한다(전체 파이프라인을 죽이지 않음)."""
    url = source["notice_url"]
    base_url = source.get("base_url", url)
    soup = fetch(url)
    if soup is None:
        return []

    items = []
    if "selectors" in source:
        items = _extract_with_custom_selectors(soup, base_url, source["selectors"])
    if not items:
        items = _extract_table_rows(soup, base_url)
    if not items:
        items = _extract_list_items(soup, base_url)
    if not items:
        items = _extract_loose_links(soup, base_url)

    # 같은 링크 중복 제거 + 개수 제한
    seen_links = set()
    deduped = []
    for it in items:
        if it["link"] in seen_links:
            continue
        seen_links.add(it["link"])
        deduped.append(it)
        if len(deduped) >= MAX_ITEMS_PER_SOURCE:
            break

    time.sleep(1)  # 서버 부담을 주지 않기 위한 최소한의 예의
    return deduped
