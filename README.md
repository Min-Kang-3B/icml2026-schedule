# ICML 2026 일정 사이트 (Seoul · COEX)

icml.cc 가상 사이트에서 화요일(7/7)~토요일(7/11) 일정을 수집해 만든
**한국어/영어 전환 가능한** 정적 일정 웹사이트입니다.

## 실행

```bash
cd icml2026
python3 -m http.server 8642
# → http://localhost:8642
```

`index.html`을 브라우저로 직접 열어도 동작합니다(모든 데이터가 `<script>` 태그로 로드되어 `file://`에서도 OK).

## 기능

- **화~토 5일 탭** — 시간대별 타임라인 (모든 시간 KST)
- **한국어 ↔ English 전환** — 우측 상단 토글 (이벤트 제목·설명·연사 소개·논문 제목 번역)
- **유형 필터** — 오럴 / 포스터 / 초청·특별 / 워크숍 / 소셜·어피니티 / 운영·휴식
- **검색** — 이벤트 검색 + 전체 논문 6,035편 제목·저자 검색(최초 1회 로딩)
- **상세 모달** — 초록(한/영), 연사 약력, 오럴 발표 시간, 포스터 위치 번호(#), OpenReview 링크
- **딥링크** — `?day=3&lang=en&open=<eventId>&q=<검색어>&theme=dark`
- 다크 모드, 모바일 대응

## 데이터

| 항목 | 규모 |
|---|---|
| 일정(이벤트) | 137건 (화~토) |
| 오럴 발표 | 168편 (42개 세션) |
| 포스터 | 5,867편 (8개 세션) |
| 워크숍 | 44개 |
| 상세 설명(초록) 번역 | 이벤트 단위 한국어 번역 |
| 논문 제목 번역 | 전체 한국어 번역 (codex CLI 배치 번역) |
| 논문 초록 | 영어 원문 제공 |

출처: https://icml.cc/virtual/2026/calendar 및 각 상세 페이지 (2026-07-06 수집)

## 재수집 파이프라인 (`scripts/`)

```bash
python3 -m venv venv && ./venv/bin/pip install beautifulsoup4 lxml requests
# 작업 디렉토리에 calendar.html(캘린더 페이지)과 papers.json(orals-posters JSON)을 받은 뒤:
./venv/bin/python scripts/parse_calendar.py     # → schedule_raw.json
./venv/bin/python scripts/scrape_all.py         # 상세 페이지 크롤링 → abstracts.jsonl, eventpages/
./venv/bin/python scripts/parse_events.py       # → events_detail.json
./venv/bin/python scripts/prep_translation.py   # → tr_in_*.json
./venv/bin/python scripts/translate_codex.py titles|misc|abstracts|bios   # codex CLI 번역 → ko_*.json
./venv/bin/python scripts/build_site.py <site-dir>  # → data/ 생성
```
