"""JSON → HTML 변환 스크립트 (오늘자 페이지 + 아카이브 갱신).

data/*.json 전체를 읽어 docs/{date}.html, docs/index.html(최신본),
docs/archive.html, docs/search-index.json(아카이브 검색용) 을 생성한다.
"""
import glob
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SCRIPT_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "data")
DOCS_DIR = os.path.join(SCRIPT_DIR, "..", "docs")

SECTIONS = [
    ("news", "뉴스"),
    ("korea", "한국뉴스"),
    ("common-sense", "상식"),
    ("english", "영어"),
    ("review", "복습"),
]


def load_all_data():
    files = sorted(glob.glob(os.path.join(DATA_DIR, "????-??-??.json")))
    entries = []
    for path in files:
        with open(path, encoding="utf-8") as f:
            entries.append(json.load(f))
    return entries


def esc(text):
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def esc_multiline(text):
    return esc(text).replace("\n", "<br>")


def accordion_item(header, body_html):
    return f"""<div class="accordion-item">
  <button class="accordion-header">{header}</button>
  <div class="accordion-body">{body_html}</div>
</div>"""


def render_news_section(day):
    items = []
    for a in day.get("news_global", []) + day.get("news_korea_it", []):
        body = f"<p>{esc_multiline(a.get('summary_3lines'))}</p>"
        if a.get("trivia"):
            body += f'<p class="trivia">💡 {esc(a.get("trivia"))}</p>'
        items.append(accordion_item(esc(a.get("title")), body))
    return "\n".join(items) or '<p class="empty">오늘은 수집된 기사가 없습니다.</p>'


def render_korea_general_section(day):
    items = []
    for a in day.get("news_korea_general", []):
        items.append(accordion_item(esc(a.get("title")), f"<p>{esc(a.get('summary_short'))}</p>"))
    return "\n".join(items) or '<p class="empty">오늘은 수집된 뉴스가 없습니다.</p>'


def render_common_sense_section(day):
    items = []
    for c in day.get("common_sense", []):
        header = f"[{esc(c.get('category'))}] {esc(c.get('topic'))}"
        items.append(accordion_item(header, f"<p>{esc(c.get('content'))}</p>"))
    return "\n".join(items) or '<p class="empty">오늘의 상식이 없습니다.</p>'


def render_english_section(day):
    eng = day.get("english", {})
    items = []
    for e in eng.get("expressions", []):
        body = f"<p>{esc(e.get('meaning'))}</p><p class=\"example\">{esc(e.get('example'))}</p>"
        items.append(accordion_item(esc(e.get("term")), body))
    passage = eng.get("passage", {})
    if passage.get("text"):
        body = f"<p>{esc(passage.get('text'))}</p><p class=\"hint\">{esc(passage.get('translation_hint'))}</p>"
        items.append(accordion_item("오늘의 지문", body))
    return "\n".join(items) or '<p class="empty">영어 학습 콘텐츠가 없습니다.</p>'


def render_review_section(day):
    items = []
    for r in day.get("review", []):
        header = f"{esc(r.get('from_date'))} 복습"
        items.append(accordion_item(header, f"<p>{esc(r.get('content'))}</p>"))
    return "\n".join(items) or '<p class="empty">복습할 내용이 없습니다.</p>'


SECTION_RENDERERS = [
    render_news_section,
    render_korea_general_section,
    render_common_sense_section,
    render_english_section,
    render_review_section,
]


def render_page(day):
    date = day["date"]
    panels = []
    for (section_id, title), renderer in zip(SECTIONS, SECTION_RENDERERS):
        panels.append(f"""<section class="panel" id="{section_id}">
  <h2>{title}</h2>
  <div class="accordion">
{renderer(day)}
  </div>
</section>""")
    dots = "\n".join(f'<span class="dot" data-index="{i}"></span>' for i in range(len(SECTIONS)))

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Daily Brief - {date}</title>
<link rel="stylesheet" href="assets/style.css">
</head>
<body>
<header class="topbar">
  <h1>Daily Brief</h1>
  <div class="topbar-right">
    <span class="date">{date}</span>
    <button id="theme-toggle" aria-label="다크모드 전환">🌙</button>
  </div>
</header>

<main class="swipe-container" id="swipe-container">
{chr(10).join(panels)}
</main>

<div class="dots" id="dots">{dots}</div>

<footer>
  <a href="archive.html">지난 브리핑 보기</a>
</footer>

<script src="assets/app.js"></script>
</body>
</html>
"""


def render_archive_page(all_dates):
    date_links = "\n".join(f'<li><a href="{d}.html">{d}</a></li>' for d in reversed(all_dates))

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Daily Brief - 아카이브</title>
<link rel="stylesheet" href="assets/style.css">
</head>
<body>
<header class="topbar">
  <h1>지난 브리핑</h1>
  <div class="topbar-right">
    <button id="theme-toggle" aria-label="다크모드 전환">🌙</button>
  </div>
</header>

<main class="archive-main">
  <input id="search-input" type="search" placeholder="검색어 입력...">
  <div class="filter-bar">
    <button class="filter-btn active" data-filter="all">전체</button>
    <button class="filter-btn" data-filter="news">뉴스</button>
    <button class="filter-btn" data-filter="common-sense">상식</button>
    <button class="filter-btn" data-filter="english">영어</button>
  </div>
  <ul id="search-results"></ul>

  <h2>날짜별 목록</h2>
  <ul class="date-list">
{date_links}
  </ul>
</main>

<script src="assets/archive.js"></script>
</body>
</html>
"""


def build_search_index(all_days):
    index = []
    for day in all_days:
        date = day["date"]
        for a in day.get("news_global", []) + day.get("news_korea_it", []):
            index.append({"date": date, "category": "news", "title": a.get("title", ""), "snippet": a.get("summary_3lines", "")})
        for a in day.get("news_korea_general", []):
            index.append({"date": date, "category": "news", "title": a.get("title", ""), "snippet": a.get("summary_short", "")})
        for c in day.get("common_sense", []):
            index.append({"date": date, "category": "common-sense", "title": c.get("topic", ""), "snippet": c.get("content", "")})
        for e in day.get("english", {}).get("expressions", []):
            index.append({"date": date, "category": "english", "title": e.get("term", ""), "snippet": e.get("meaning", "")})
    return index


def main():
    all_days = load_all_data()
    if not all_days:
        print("[WARN] data/ 에 생성된 JSON이 없습니다. generate_content.py 를 먼저 실행하세요.")
        return

    os.makedirs(DOCS_DIR, exist_ok=True)
    all_dates = [d["date"] for d in all_days]

    for day in all_days:
        with open(os.path.join(DOCS_DIR, f"{day['date']}.html"), "w", encoding="utf-8") as f:
            f.write(render_page(day))

    with open(os.path.join(DOCS_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(render_page(all_days[-1]))

    with open(os.path.join(DOCS_DIR, "archive.html"), "w", encoding="utf-8") as f:
        f.write(render_archive_page(all_dates))

    search_index = build_search_index(all_days)
    with open(os.path.join(DOCS_DIR, "search-index.json"), "w", encoding="utf-8") as f:
        json.dump(search_index, f, ensure_ascii=False, indent=2)

    print(f"HTML 생성 완료: {len(all_days)}개 날짜 -> index.html, archive.html, search-index.json")


if __name__ == "__main__":
    main()
