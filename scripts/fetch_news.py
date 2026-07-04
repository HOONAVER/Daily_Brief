"""RSS + 네이버뉴스 오픈API 수집 스크립트.

실행하면 오늘 날짜의 원시 기사 목록을 .cache/raw_YYYY-MM-DD.json 에 저장한다.
이 파일은 generate_content.py 가 Claude API 입력으로 사용하며, data/ 아래
최종 산출물과는 별개의 중간 캐시다.
"""
import datetime
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

import feedparser

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

USER_AGENT = "Mozilla/5.0 (compatible; DailyBriefBot/1.0; +https://github.com/)"
MAX_ITEMS_PER_SOURCE = 10

# 게임/IT/AI 뉴스 섹션(news_global, news_korea_it)에 쓰일 RSS 소스.
# 디스이즈게임/인벤은 Cloudflare 봇 차단 및 RSS 미제공이 확인되어 제외.
# 접근 가능한 대체 수집 방식(공식 API, 사이트맵 등)이 확인되면 추가할 것.
RSS_SOURCES = [
    {"name": "TechCrunch", "url": "https://techcrunch.com/feed/", "category": "news_global"},
    {"name": "The Verge", "url": "https://www.theverge.com/rss/index.xml", "category": "news_global"},
    {"name": "Ars Technica", "url": "https://feeds.arstechnica.com/arstechnica/index", "category": "news_global"},
    {"name": "VentureBeat AI", "url": "https://venturebeat.com/category/ai/feed/", "category": "news_global"},
    {"name": "IGN", "url": "https://www.ign.com/rss/articles/feed", "category": "news_global"},
    {"name": "ZDNet Korea", "url": "https://feeds.feedburner.com/zdkorea", "category": "news_korea_it"},
]

# 한국 주요뉴스(news_korea_general) 섹션용 네이버뉴스 검색 쿼리.
# 오픈API는 키워드 검색만 제공하므로 주요 카테고리 키워드로 근사한다.
NAVER_QUERIES = ["정치", "경제", "사회", "국제"]
NAVER_NEWS_API = "https://openapi.naver.com/v1/search/news.json"


SUMMARY_MAX_CHARS = 400


def strip_html(text):
    text = re.sub(r"<.*?>", "", text or "").strip()
    if len(text) > SUMMARY_MAX_CHARS:
        text = text[:SUMMARY_MAX_CHARS].rsplit(" ", 1)[0] + "..."
    return text


def fetch_rss(source):
    req = urllib.request.Request(source["url"], headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=10) as resp:
        raw = resp.read()
    parsed = feedparser.parse(raw)
    articles = []
    for entry in parsed.entries[:MAX_ITEMS_PER_SOURCE]:
        articles.append({
            "source": source["name"],
            "category": source["category"],
            "title": entry.get("title", ""),
            "link": entry.get("link", ""),
            "published": entry.get("published", entry.get("updated", "")),
            "summary": strip_html(entry.get("summary", "")),
        })
    return articles


TITLE_DEDUP_THRESHOLD = 0.3


def title_bigrams(title):
    text = re.sub(r"[^\w]", "", title)
    return {text[i:i + 2] for i in range(len(text) - 1)} or {text}


def jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def dedup_by_title(articles):
    """네이버뉴스는 같은 사건을 여러 매체가 동시에 다뤄 유사 제목이 도배되는 경우가
    많다. 어순/조사가 달라도 잡아내도록 글자 2-gram 자카드 유사도로 비교한다."""
    kept = []
    kept_bigrams = []
    for article in articles:
        bigrams = title_bigrams(article["title"])
        if any(jaccard(bigrams, k) > TITLE_DEDUP_THRESHOLD for k in kept_bigrams):
            continue
        kept.append(article)
        kept_bigrams.append(bigrams)
    return kept


def fetch_naver_news(query, display=10):
    client_id = os.environ["NAVER_CLIENT_ID"]
    client_secret = os.environ["NAVER_CLIENT_SECRET"]
    params = urllib.parse.urlencode({"query": query, "display": display, "sort": "sim"})
    req = urllib.request.Request(
        f"{NAVER_NEWS_API}?{params}",
        headers={
            "X-Naver-Client-Id": client_id,
            "X-Naver-Client-Secret": client_secret,
        },
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.load(resp)
    articles = []
    for item in data.get("items", []):
        articles.append({
            "source": "네이버뉴스",
            "category": "news_korea_general",
            "title": strip_html(item.get("title", "")),
            "link": item.get("originallink") or item.get("link", ""),
            "published": item.get("pubDate", ""),
            "summary": strip_html(item.get("description", "")),
        })
    return articles


def collect():
    articles = []
    for source in RSS_SOURCES:
        try:
            fetched = fetch_rss(source)
            articles.extend(fetched)
            print(f"[OK] {source['name']}: {len(fetched)}건")
        except (urllib.error.URLError, urllib.error.HTTPError) as exc:
            print(f"[WARN] {source['name']} 수집 실패: {exc}")

    if os.environ.get("NAVER_CLIENT_ID") and os.environ.get("NAVER_CLIENT_SECRET"):
        naver_articles = []
        for query in NAVER_QUERIES:
            try:
                fetched = fetch_naver_news(query)
                naver_articles.extend(fetched)
                print(f"[OK] 네이버뉴스({query}): {len(fetched)}건")
            except (urllib.error.URLError, urllib.error.HTTPError) as exc:
                print(f"[WARN] 네이버뉴스({query}) 수집 실패: {exc}")

        deduped = dedup_by_title(naver_articles)
        print(f"[INFO] 네이버뉴스 중복 제거: {len(naver_articles)}건 -> {len(deduped)}건")
        articles.extend(deduped)
    else:
        print("[WARN] NAVER_CLIENT_ID/NAVER_CLIENT_SECRET 미설정 — 네이버뉴스 수집 생략")

    return articles


def main():
    today = datetime.date.today().isoformat()
    articles = collect()

    out_dir = os.path.join(os.path.dirname(__file__), "..", ".cache")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"raw_{today}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"date": today, "articles": articles}, f, ensure_ascii=False, indent=2)

    print(f"수집 완료: 총 {len(articles)}건 -> {out_path}")


if __name__ == "__main__":
    main()
