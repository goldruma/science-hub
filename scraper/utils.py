# -*- coding: utf-8 -*-
"""
공통 유틸리티: 날짜 파싱, 중복 제거, 제목 키워드 기반 태그 보정(학년/계열/구분)

이 파일은 100% 규칙 기반(키워드 매칭)입니다. 복잡한 NLP가 필요할 만큼
글이 많아지면 이 로직을 임베딩/분류기로 교체해도 main.py 인터페이스는
그대로 유지됩니다.
"""
import re
import hashlib
from datetime import datetime

# ---------------------------------------------------------------------------
# 키워드 -> 태그 매핑. 필요하면 자유롭게 단어를 추가하세요.
# ---------------------------------------------------------------------------
GRADE_KEYWORDS = {
    "초등": ["초등", "초3", "초4", "초5", "초6", "elementary"],
    "중등": ["중등", "중1", "중2", "중3", "중학", "junior"],
    "고등": ["고등", "고1", "고2", "고3", "고교", "high school"],
}

FIELD_KEYWORDS = {
    "수학": ["수학", "math", "KMO", "KJMO", "올림피아드 수학"],
    "물리": ["물리", "physics", "KPhO"],
    "화학": ["화학", "chemistry", "KChO"],
    "생명과학": ["생명과학", "생물", "biology", "KBO", "의생명"],
    "지구과학": ["지구과학", "천문", "지질", "기상", "astronomy"],
    "정보/컴퓨터": ["정보", "컴퓨터", "코딩", "SW", "소프트웨어", "AI", "인공지능", "알고리즘", "KOI"],
    "공학": ["공학", "기계", "전자", "전기", "반도체", "로봇", "engineering"],
    "융합/기타": [],  # 기본값(다른 계열에 안 걸리면 여기로)
}

CATEGORY_KEYWORDS = {
    "입학/입시": ["입학", "입시", "모집요강", "전형", "원서접수", "합격자", "수시", "정시", "편입"],
    "영재교육": ["영재", "영재교육원", "GED", "영재성", "발달기록"],
    "올림피아드/대회": ["올림피아드", "경시대회", "경진대회", "챌린지", "공모전", "탐구대회", "과학전람회"],
    "연구/R&E": ["R&E", "연구원", "연구과제", "연구비", "인턴", "학술연구", "공동연구", "랩"],
    "행사/설명회": ["설명회", "박람회", "축제", "캠프", "체험", "포럼", "세미나", "특강", "강연"],
    "채용/공모": ["채용", "공고", "모집공고", "입찰", "위촉"],
    "정책/보도": ["보도자료", "정책", "업무계획", "시행계획"],
}


def guess_tags(title: str, default_tags: dict) -> dict:
    """제목 키워드로 태그를 보정한다. default_tags에 있는 값은 항상 포함되고,
    제목에서 추가로 매칭되는 키워드가 있으면 태그를 더 붙인다."""
    grade = set(default_tags.get("grade", []))
    field = set(default_tags.get("field", []))
    category = set(default_tags.get("category", []))

    for tag, keywords in GRADE_KEYWORDS.items():
        if any(kw.lower() in title.lower() for kw in keywords):
            grade.add(tag)
    for tag, keywords in FIELD_KEYWORDS.items():
        if any(kw.lower() in title.lower() for kw in keywords):
            field.add(tag)
    for tag, keywords in CATEGORY_KEYWORDS.items():
        if any(kw.lower() in title.lower() for kw in keywords):
            category.add(tag)

    if not field:
        field.add("융합/기타")
    if not grade:
        grade.add("전체")
    if not category:
        category.add("행사/설명회")

    return {
        "grade": sorted(grade),
        "field": sorted(field),
        "category": sorted(category),
    }


def make_uid(source_id: str, title: str, link: str) -> str:
    """소스+제목+링크 기준 고유 ID (중복 제거용)"""
    raw = f"{source_id}|{title.strip()}|{link.strip()}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def normalize_date(raw: str):
    """다양한 한국어 날짜 표기를 ISO(YYYY-MM-DD)로 정규화. 실패하면 None."""
    if not raw:
        return None
    raw = raw.strip()
    patterns = [
        r"(\d{4})[.\-/년]\s*(\d{1,2})[.\-/월]\s*(\d{1,2})",
        r"(\d{2})[.\-/](\d{1,2})[.\-/](\d{1,2})",
    ]
    for p in patterns:
        m = re.search(p, raw)
        if m:
            y, mo, d = m.groups()
            y = int(y)
            if y < 100:
                y += 2000
            try:
                return datetime(y, int(mo), int(d)).strftime("%Y-%m-%d")
            except ValueError:
                continue
    return None


def dedupe(items: list) -> list:
    seen = set()
    out = []
    for it in items:
        if it["uid"] in seen:
            continue
        seen.add(it["uid"])
        out.append(it)
    return out
