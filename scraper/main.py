# -*- coding: utf-8 -*-
"""
과학/공학 활동 허브 - 스크레이퍼 오케스트레이터

사용법
------
전체 소스 수집 후 data/notices.json 갱신:
    python main.py

특정 소스 하나만 테스트(파일 저장 안 함, 콘솔에 결과만 출력):
    python main.py --test kaist_ug

소스 목록 보기:
    python main.py --list
"""
import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from html_scraper import scrape_source
from rss_scraper import scrape_rss
from utils import guess_tags, make_uid, normalize_date, dedupe

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "sources.json"
DATA_PATH = ROOT / "data" / "notices.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")


def load_sources():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)["sources"]


def run_one(source: dict) -> list:
    if source.get("type") == "rss":
        raw_items = scrape_rss(source)
    else:
        raw_items = scrape_source(source)

    results = []
    for it in raw_items:
        tags = guess_tags(it["title"], source["default_tags"])
        results.append({
            "uid": make_uid(source["id"], it["title"], it["link"]),
            "source_id": source["id"],
            "org": source["org"],
            "org_type": source["org_type"],
            "title": it["title"],
            "link": it["link"],
            "date": normalize_date(it.get("date_raw", "")),
            "grade": tags["grade"],
            "field": tags["field"],
            "category": tags["category"],
            "collected_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        })
    return results


def run_all():
    sources = load_sources()
    all_items = []
    ok, failed = 0, []

    for source in sources:
        logger.info("수집 중: [%s] %s", source["org"], source["name"])
        try:
            items = run_one(source)
        except Exception as e:  # 한 소스가 죽어도 전체는 계속 진행
            logger.error("실패: %s (%s)", source["id"], e)
            failed.append(source["id"])
            continue
        if not items:
            logger.warning("  -> 0건 (selector 점검 필요할 수 있음: --test %s)", source["id"])
            failed.append(source["id"])
        else:
            logger.info("  -> %d건", len(items))
            ok += 1
        all_items.extend(items)

    # 기존 데이터와 합쳐서 중복 제거(사이트가 지난 공지를 리스트에서 내려도
    # 최근 며칠간 모은 데이터는 남도록 seed/이전 회차 데이터를 보존)
    existing = []
    if DATA_PATH.exists():
        try:
            existing = json.loads(DATA_PATH.read_text(encoding="utf-8")).get("items", [])
        except json.JSONDecodeError:
            existing = []

    merged = dedupe(all_items + existing)
    merged.sort(key=lambda x: (x.get("date") or "0000-00-00"), reverse=True)
    # 무한정 커지지 않도록 최근 400건만 보관
    merged = merged[:400]

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_count": len(sources),
        "ok_count": ok,
        "failed_sources": failed,
        "item_count": len(merged),
        "items": merged,
    }
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("완료: %d건 저장 (%s), 실패/0건 소스: %s", len(merged), DATA_PATH, failed or "없음")


def test_one(source_id: str):
    sources = {s["id"]: s for s in load_sources()}
    if source_id not in sources:
        print(f"'{source_id}' 를 찾을 수 없습니다. --list 로 확인하세요.")
        sys.exit(1)
    items = run_one(sources[source_id])
    print(json.dumps(items, ensure_ascii=False, indent=2))
    print(f"\n총 {len(items)}건")


def list_sources():
    for s in load_sources():
        print(f"{s['id']:16s} [{s['org_type']:14s}] {s['org']} - {s['name']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="과학/공학 활동 허브 스크레이퍼")
    parser.add_argument("--test", metavar="SOURCE_ID", help="소스 하나만 테스트 실행")
    parser.add_argument("--list", action="store_true", help="등록된 소스 목록 출력")
    args = parser.parse_args()

    if args.list:
        list_sources()
    elif args.test:
        test_one(args.test)
    else:
        run_all()
