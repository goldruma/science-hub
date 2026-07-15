# 과학·공학 활동 인덱스

KAIST·서울대·POSTECH·UNIST·GIST·DGIST·연세대·고려대 입학처, 한국과학창의재단·한국연구재단·교육부·과학기술정보통신부,
영재교육종합데이터베이스(GED)·시도교육청 영재교육원, 한국과학영재학교·서울과학고·경기북과학고·대전과학고,
수학/물리/화학/생물/정보 올림피아드까지 — 흩어져 있는 공지사항·행사안내를 한 곳에 모아 **학년 / 계열 / 교육·연구 구분**으로
필터링해서 볼 수 있는 사이트입니다.

## 이게 정말 "실시간"으로 자동 수집되나요?

**네, 다만 정확히는 "실시간"이 아니라 "주기적 자동 수집"입니다.** 아래처럼 3단계로 동작합니다.

1. `scraper/main.py` 가 `config/sources.json` 에 등록된 28개 기관 페이지를 돌면서 공지 제목/링크/날짜를 긁어옵니다.
2. 결과를 `data/notices.json` 에 저장합니다.
3. **GitHub Actions**(`.github/workflows/scrape.yml`)가 정해진 주기(기본 3시간마다)로 1~2번을 자동 실행하고,
   바뀐 내용을 저장소에 자동 커밋합니다.
4. `index.html`(GitHub Pages로 배포)이 `data/notices.json`을 읽어서 화면에 보여줍니다.

즉 "누군가 브라우저를 열어두면 실시간으로 크롤링"하는 방식이 아니라, **GitHub의 무료 스케줄러가 몇 시간 간격으로 갱신**하는
방식입니다. 사이트 자체는 정적 페이지라 서버 비용이 들지 않고, GitHub 계정만 있으면 무료로 계속 돌릴 수 있습니다.

## 5분 배포 가이드

1. 이 폴더 전체를 새 GitHub 저장소에 올립니다.
   ```bash
   cd science-hub
   git init
   git add .
   git commit -m "init"
   git branch -M main
   git remote add origin https://github.com/<내계정>/science-hub.git
   git push -u origin main
   ```
2. 저장소 **Settings → Actions → General → Workflow permissions** 에서
   "Read and write permissions"를 선택하세요. (Actions가 `data/notices.json`을 커밋하려면 필요합니다.)
3. 저장소 **Settings → Pages** 에서 Source를 "Deploy from a branch", Branch를 `main` / `/(root)` 로 설정하세요.
   몇 분 뒤 `https://<내계정>.github.io/science-hub/` 에서 사이트가 열립니다.
4. **Actions** 탭 → "공지사항 자동 수집" → **Run workflow** 를 눌러 한 번 수동 실행해 보세요.
   `data/notices.json`이 갱신되고 자동 커밋되는지 확인할 수 있습니다. 이후에는 cron 설정대로 자동 반복됩니다.

배포 전까지는 `index.html`을 그냥 더블클릭해서 열어도 됩니다. `data/notices.json`을 못 읽는 환경(로컬 파일,
또는 이 대화의 미리보기처럼 fetch가 제한된 곳)에서는 **HTML에 내장된 시드 데이터**(2026-07-15 기준 실제 조사 데이터
27건)로 자동 대체됩니다.

## 폴더 구조

```
science-hub/
├── index.html              # 프론트엔드 (필터 UI). GitHub Pages가 이 파일을 서빙
├── config/
│   └── sources.json         # 수집 대상 기관 28곳 + 태그 규칙
├── scraper/
│   ├── main.py               # 전체 실행 / 개별 소스 테스트 CLI
│   ├── html_scraper.py       # 범용 게시판 스크레이퍼 (table/list/loose-link 패턴)
│   ├── rss_scraper.py        # RSS 지원 (type: "rss" 소스용)
│   ├── utils.py               # 태그 자동 분류, 날짜 정규화, 중복 제거
│   └── requirements.txt
├── data/
│   └── notices.json          # 스크레이퍼 결과물 (Actions가 주기적으로 갱신)
└── .github/workflows/
    └── scrape.yml             # 자동 수집 스케줄러
```

## ⚠️ 배포 전에 꼭 해야 할 일: 셀렉터 점검

한국 기관 홈페이지들은 게시판 구조가 사이트마다 다르고 예고 없이 개편됩니다. 이 저장소의 `html_scraper.py`는
**표(table) / 목록(ul·li) / 느슨한 링크 패턴**을 순서대로 시도하는 범용 파서라서 상당수 사이트에서 바로 동작하지만,
100% 보장은 없습니다. 배포 후 아래 명령으로 소스별로 꼭 확인하세요.

```bash
cd scraper
pip install -r requirements.txt
python main.py --list                # 등록된 28개 소스 확인
python main.py --test kaist_ug        # 소스 하나만 테스트 (파일 저장 안 함)
```

`--test` 결과가 0건이거나 이상한 텍스트가 섞여 나오면, 브라우저 개발자도구로 해당 페이지의 게시판 HTML 구조를 보고
`config/sources.json`의 해당 항목에 `selectors` 필드를 추가해서 정확히 지정해 주세요.

```jsonc
{
  "id": "example",
  "...": "...",
  "selectors": {
    "row": "table.board-list tbody tr",   // 각 공지 한 줄
    "title": "td.subject a",              // 제목 링크
    "link": "td.subject a",               // 보통 title과 동일
    "date": "td.date"                     // 날짜 칸 (없으면 생략 가능)
  }
}
```

## 소스 추가하기 (17개 시도교육청 영재교육원, 다른 과학고 등)

`config/sources.json`에 지금은 서울시교육청 융합과학교육원 1곳만 예시로 들어 있습니다. 나머지 16개 시도(경기·인천·부산·
대구·광주·대전·울산·세종·강원·충북·충남·전북·전남·경북·경남·제주) 영재교육원은 각 시도교육청 홈페이지에서
"영재교육원" 또는 "융합과학교육원"을 검색해 공지사항 URL을 찾은 뒤 같은 형식으로 추가하면 됩니다. 대부분
[GED(영재교육종합데이터베이스)](https://ged.kedi.re.kr)를 통해 선발 공고를 올리므로, GED 소스 하나만으로도
상당수 지역 공고를 커버할 수 있습니다.

다른 과학고(경기과학고·세종과학고·인천과학예술영재학교 등)도 동일한 패턴으로 `org_type: "gifted_school"`
소스를 추가하면 됩니다.

## RSS 소스 추가하기

대한민국 정책브리핑(korea.kr)은 부처별 RSS를 공식 제공합니다. 사이트 내 "RSS서비스" 메뉴에서 교육부/과학기술정보통신부
RSS 주소를 직접 발급받은 뒤, `sources.json`에서 해당 소스의 `"type"`을 `"rss"`로 바꾸고 `"rss_url"` 필드를
추가하면 `rss_scraper.py`가 자동으로 처리합니다. (RSS 주소는 개편으로 바뀔 수 있어 이 저장소에는 고정 URL을
박아두지 않았습니다.)

## 필터 태그 체계

- **학년**: 초등 / 중등 / 고등 / 전체
- **계열**: 수학 / 물리 / 화학 / 생명과학 / 지구과학 / 정보·컴퓨터 / 공학 / 융합·기타
- **교육&연구 구분**: 입학/입시 · 영재교육 · 올림피아드/대회 · 연구/R&E · 행사/설명회 · 채용/공모 · 정책/보도

각 소스는 기본 태그(`default_tags`)를 갖고, `scraper/utils.py`의 `guess_tags()`가 제목의 키워드(예: "고등부",
"올림피아드", "R&E" 등)를 보고 태그를 추가로 보정합니다. 키워드 사전은 `utils.py` 상단의 `GRADE_KEYWORDS` /
`FIELD_KEYWORDS` / `CATEGORY_KEYWORDS` 에서 자유롭게 수정할 수 있습니다.

## 크롤링 예의 / 법적 참고사항

- 모두 **공개된 공지사항 게시판**만 수집 대상으로 하며, 로그인이 필요한 페이지나 개인정보가 담긴 게시판은 다루지 않습니다.
- `html_scraper.py`는 요청 사이마다 최소 1초씩 쉬어서 서버에 부담을 주지 않도록 했습니다. 소스를 늘릴 때도
  과도하게 자주 요청하지 않는 게 좋습니다(스케줄 주기를 3시간보다 더 촘촘하게 줄이지 않는 것을 권장합니다).
- 이 도구는 어디까지나 "제목 + 링크 + 날짜" 같은 사실 정보만 모아 원문으로 안내하는 인덱스입니다. 공지 본문을
  통째로 긁어와 재게시하지 않으며, 최종 확인은 항상 출처 링크에서 하도록 설계했습니다.
- 일부 사이트는 `robots.txt`나 이용약관에서 자동 수집을 제한할 수 있습니다. 기관별로 다르므로, 상업적 목적이 아닌
  개인/학습 목적이라도 배포 전에 대상 사이트의 `robots.txt`와 이용약관을 한 번씩 확인하시길 권합니다.

## 알려진 한계

- 일부 사이트(특히 JS로 게시판을 그리는 곳)는 `requests`만으로는 내용을 못 가져올 수 있습니다. 이런 경우
  `html_scraper.py`의 `fetch()` 함수를 Selenium/Playwright 기반으로 교체해야 합니다(현재는 포함돼 있지 않습니다).
- 날짜 형식이 특이한 사이트는 `utils.normalize_date()`가 못 알아볼 수 있습니다. 이때는 `date` 필드가 `null`로
  나오고 화면에는 "날짜 미상"으로 표시됩니다.
- 이 저장소를 만든 시점(2026-07-15)에는 각 기관의 정확한 게시판 URL을 실제 검색으로 확인했지만, 사이트 개편으로
  링크가 바뀌었을 수 있습니다. `--test` 명령으로 주기적으로 점검해 주세요.
