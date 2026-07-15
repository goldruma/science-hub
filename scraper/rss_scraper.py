# -*- coding: utf-8 -*-
"""
RSS/Atom 피드 스크레이퍼. sources.json에서 "type": "rss" 이고
"rss_url"이 있는 소스에 사용됩니다.

정부 사이트 중에는 대한민국 정책브리핑(korea.kr)처럼 RSS를 정식 제공하는
곳이 있습니다. 다만 부처별 정확한 RSS 주소는 정책브리핑 사이트에서
'RSS서비스' 메뉴로 들어가 직접 발급/확인해야 합니다(수시로 바뀔 수 있어
이 저장소에 고정 URL로 박아두지 않았습니다). 확인한 URL을
config/sources.json 의 해당 source에 "rss_url" 필드로 추가하고
"type"을 "rss"로 바꾸면 바로 사용됩니다.
"""
import logging
import feedparser

logger = logging.getLogger("rss_scraper")
MAX_ITEMS_PER_SOURCE = 15


def scrape_rss(source: dict) -> list:
    rss_url = source.get("rss_url")
    if not rss_url:
        logger.warning("%s: rss_url이 없습니다", source["id"])
        return []

    feed = feedparser.parse(rss_url)
    if feed.bozo and not feed.entries:
        logger.warning("%s: RSS 파싱 실패 (%s)", source["id"], feed.get("bozo_exception"))
        return []

    items = []
    for entry in feed.entries[:MAX_ITEMS_PER_SOURCE]:
        title = getattr(entry, "title", "").strip()
        link = getattr(entry, "link", "").strip()
        date_raw = getattr(entry, "published", "") or getattr(entry, "updated", "")
        if not title or not link:
            continue
        items.append({"title": title, "link": link, "date_raw": date_raw})
    return items
