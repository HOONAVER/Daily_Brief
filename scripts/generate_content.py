"""Claude API 호출 → 구조화된 JSON 생성 스크립트.

fetch_news.py 가 만든 .cache/raw_YYYY-MM-DD.json 과 data/ 폴더의 최근 1-2일치
데이터(복습용 컨텍스트)를 입력으로 Claude API를 호출해 data/YYYY-MM-DD.json 을 생성한다.
"""
import datetime
import glob
import json
import os
import sys

from anthropic import Anthropic

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5")
SCRIPT_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "data")
CACHE_DIR = os.path.join(SCRIPT_DIR, "..", ".cache")

SYSTEM_PROMPT = """당신은 개인용 일일 지식 브리핑을 작성하는 에디터입니다.
반드시 아래 JSON 스키마와 정확히 일치하는 JSON만 출력하세요. 설명, 코드펜스, 그 외 텍스트는 절대 포함하지 마세요.

스키마:
{
  "date": "YYYY-MM-DD",
  "news_global": [{"title": "", "summary_3lines": "", "trivia": "", "link": ""}],
  "news_korea_it": [{"title": "", "summary_3lines": "", "trivia": "", "link": ""}],
  "news_korea_general": [{"title": "", "summary_short": "", "link": ""}],
  "common_sense": [{"topic": "", "category": "", "content": ""}],
  "english": {
    "expressions": [{"term": "", "meaning": "", "example": ""}],
    "passage": {"text": "", "translation_hint": ""}
  },
  "review": [{"from_date": "", "content": ""}]
}

작성 지침:
- news_global / news_korea_it / news_korea_general: link 필드에는 입력으로 제공된 해당 기사 원본의 link 값을 그대로 복사해서 넣는다(직접 만들어내지 않는다).
- news_global / news_korea_it: 제공된 기사 중 흥미롭고 중요한 것 위주로 골라 각각 3줄 요약과 토막지식(용어/기업/기술 배경) 1개씩 작성.
- news_korea_general: 제공된 한국 주요뉴스 기사 중 헤드라인과 1~2줄 간단 요약.
- common_sense: 역사/과학/경제/문화 등 카테고리를 고정 로테이션하지 말고 그때그때 다양하게 6~8개 구성.
- english: 오늘 수집된 기사 원문에서 가능하면 단어/표현 7~8개(뜻+예문)를 추출하고, 짧은 지문 1개와 해석 힌트를 작성. 영어 표현에는 원문 링크를 넣지 않는다.
- review: 함께 제공되는 최근 며칠치 데이터에서 상식/영어 표현 2~3개를 가볍게 재소환(그대로 복사하지 말고 자연스럽게 재구성). 최근 데이터가 없으면 빈 배열로 둔다.
"""


def load_raw_articles(today):
    path = os.path.join(CACHE_DIR, f"raw_{today}.json")
    if not os.path.exists(path):
        raise FileNotFoundError(f"{path} 가 없습니다. 먼저 fetch_news.py 를 실행하세요.")
    with open(path, encoding="utf-8") as f:
        return json.load(f)["articles"]


def load_recent_context(today, limit=2):
    files = sorted(glob.glob(os.path.join(DATA_DIR, "????-??-??.json")))
    files = [f for f in files if os.path.basename(f) != f"{today}.json"]
    context = []
    for path in files[-limit:]:
        with open(path, encoding="utf-8") as f:
            context.append(json.load(f))
    return context


def build_user_prompt(today, articles, recent_context):
    return json.dumps(
        {"today": today, "articles": articles, "recent_days_for_review": recent_context},
        ensure_ascii=False,
    )


def extract_json(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
    return json.loads(text)


def generate(today):
    articles = load_raw_articles(today)
    recent_context = load_recent_context(today)
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    response = client.messages.create(
        model=MODEL,
        max_tokens=8000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": build_user_prompt(today, articles, recent_context)}],
    )
    text = "".join(block.text for block in response.content if block.type == "text")
    return extract_json(text)


def main():
    today = datetime.date.today().isoformat()
    result = generate(today)
    result["date"] = today

    os.makedirs(DATA_DIR, exist_ok=True)
    out_path = os.path.join(DATA_DIR, f"{today}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"생성 완료 -> {out_path}")


if __name__ == "__main__":
    main()
