"""
관세직 7급 무역학 일일 학습
1) Gemini로 콘텐츠 생성 → lessons/<id>.json 으로 보관 (지난 학습 누적)
2) 학습마다 docs/<id>.html, 전체 목록 docs/index.html 생성 (GitHub Pages)
3) 카카오톡에는 그날 학습 페이지(<id>.html)로 연결되는 카드 전송
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import webbrowser
from datetime import date, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel, Field

load_dotenv()

ROOT = Path(__file__).resolve().parent
DOCS_DIR = ROOT / "docs"
LESSONS_DIR = ROOT / "lessons"
CONTENT_JSON = ROOT / "content.json"
INDEX_HTML = DOCS_DIR / "index.html"

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
KAKAO_REST_API_KEY = os.environ.get("KAKAO_REST_API_KEY", "")
KAKAO_CLIENT_SECRET = os.environ.get("KAKAO_CLIENT_SECRET", "")
KAKAO_REFRESH_TOKEN = os.environ.get("KAKAO_REFRESH_TOKEN", "")
KAKAO_ACCESS_TOKEN = os.environ.get("KAKAO_ACCESS_TOKEN", "")
# 학습 페이지가 올라가는 GitHub Pages 주소 (예: https://USERNAME.github.io/muyukhak/)
CONTENT_BASE_URL = os.environ.get("CONTENT_BASE_URL", "").rstrip("/")

KAKAO_TOKEN_URL = "https://kauth.kakao.com/oauth/token"
KAKAO_MEMO_SEND_URL = "https://kapi.kakao.com/v2/api/talk/memo/default/send"

SEOUL = ZoneInfo("Asia/Seoul")
WEEKDAYS = "월화수목금토일"
LESSON_ID_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})(?:-(\d+))?$")

TRADE_TOPICS = [
    "국제무역이론(절대우위·비교우위·헥셔올린)",
    "무역정책(관세·비관세장벽·보호무역)",
    "WTO·FTA·통상협정",
    "국제수지·환율·외환시장",
    "무역계약·인코텀즈(Incoterms)",
    "신용장(L/C)·무역결제",
    "수출입통관·관세평가·원산지",
    "무역보험·무역금융",
    "전자상거래·디지털무역",
    "국제운송·해상보험",
]


class DailyContent(BaseModel):
    topic: str = Field(description="오늘의 주제")
    summary: str = Field(description="핵심요약 (3~5문장)")
    quiz: str = Field(description="O/X 퀴즈 문제 1문항")
    answer: str = Field(description="정답 (O 또는 X)")
    explanation: str = Field(description="정답 해설")


def seoul_today() -> date:
    return datetime.now(SEOUL).date()


def date_label(iso_date: str) -> str:
    d = date.fromisoformat(iso_date)
    return f"{d:%Y.%m.%d} ({WEEKDAYS[d.weekday()]})"


def pick_topic_hint() -> str:
    day = datetime.now(SEOUL).timetuple().tm_yday
    return TRADE_TOPICS[day % len(TRADE_TOPICS)]


def generate_daily_content() -> dict[str, Any]:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY 환경변수가 필요합니다.")

    client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = f"""당신은 대한민국 공무원 시험 '관세직 7급 무역학' 전문 강사입니다.
오늘 날짜: {date_label(seoul_today().isoformat())}
주제 힌트: {pick_topic_hint()}

실제 출제 빈도가 높은 핵심 개념 하나를 선정해 JSON으로 작성하세요.
1. topic: 구체적 주제명
2. summary: 핵심요약 3~5문장 (전문 용어 정확히)
3. quiz: O/X 진술문 1개 (애매하지 않게)
4. answer: O 또는 X만
5. explanation: 근거 포함 해설 2~4문장
한국어, 아침 복습용으로 명확하게.
"""

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": DailyContent,
            "temperature": 0.65,
        },
    )

    if response.parsed is not None:
        data = response.parsed
        if isinstance(data, DailyContent):
            return data.model_dump()
        if isinstance(data, dict):
            return DailyContent.model_validate(data).model_dump()

    if not response.text:
        raise RuntimeError("Gemini 응답이 비어 있습니다.")
    return DailyContent.model_validate_json(response.text).model_dump()


# ---------------------------------------------------------------- lessons


def lesson_sort_key(lesson_id: str) -> tuple[str, int]:
    m = LESSON_ID_RE.match(lesson_id)
    if not m:
        return (lesson_id, 0)
    return (m.group(1), int(m.group(2) or 1))


def next_lesson_id(iso_date: str) -> str:
    if not (LESSONS_DIR / f"{iso_date}.json").exists():
        return iso_date
    n = 2
    while (LESSONS_DIR / f"{iso_date}-{n}.json").exists():
        n += 1
    return f"{iso_date}-{n}"


def save_lesson(content: dict[str, Any], iso_date: str | None = None) -> dict[str, Any]:
    iso_date = iso_date or seoul_today().isoformat()
    lesson = {"id": next_lesson_id(iso_date), "date": iso_date, **content}
    LESSONS_DIR.mkdir(parents=True, exist_ok=True)
    path = LESSONS_DIR / f"{lesson['id']}.json"
    path.write_text(json.dumps(lesson, ensure_ascii=False, indent=2), encoding="utf-8")
    CONTENT_JSON.write_text(json.dumps(lesson, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"학습 저장: {path}")
    return lesson


def load_lessons() -> list[dict[str, Any]]:
    """오래된 순"""
    if not LESSONS_DIR.exists():
        return []
    lessons = [
        json.loads(p.read_text(encoding="utf-8")) for p in LESSONS_DIR.glob("*.json")
    ]
    return sorted(lessons, key=lambda x: lesson_sort_key(x["id"]))


def load_content() -> dict[str, Any]:
    if not CONTENT_JSON.exists():
        raise RuntimeError("content.json이 없습니다. 먼저 콘텐츠를 생성하세요.")
    return json.loads(CONTENT_JSON.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- html


def _esc(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


STYLE = """
:root {
  --bg: #0f1c17;
  --panel: #162820;
  --ink: #f3f6f2;
  --muted: #a8b8ae;
  --accent: #3dba7a;
  --line: rgba(243, 246, 242, 0.12);
}
* { box-sizing: border-box; }
body {
  margin: 0;
  min-height: 100dvh;
  font-family: "Noto Sans KR", sans-serif;
  color: var(--ink);
  background:
    radial-gradient(1200px 600px at 10% -10%, #1e3d30 0%, transparent 55%),
    radial-gradient(900px 500px at 100% 0%, #243528 0%, transparent 50%),
    var(--bg);
  line-height: 1.65;
}
a { color: inherit; text-decoration: none; }
main { width: min(720px, 100%); margin: 0 auto; padding: 28px 20px 64px; }
.topnav { margin-bottom: 22px; }
.topnav a { color: var(--accent); font-weight: 700; font-size: 0.95rem; }
.eyebrow {
  font-size: 0.85rem; letter-spacing: 0.08em; color: var(--accent);
  font-weight: 700; margin-bottom: 10px;
}
h1 {
  font-family: "Noto Serif KR", serif;
  font-size: clamp(1.85rem, 6vw, 2.45rem);
  line-height: 1.25; margin: 0 0 10px; font-weight: 700;
}
.date { color: var(--muted); font-size: 0.95rem; margin-bottom: 28px; }
section, details, .item {
  background: color-mix(in srgb, var(--panel) 88%, black);
  border: 1px solid var(--line);
  border-radius: 18px;
}
section { padding: 22px 20px; margin-bottom: 16px; }
h2 { margin: 0 0 12px; font-size: 1.05rem; color: var(--accent); letter-spacing: -0.01em; }
p { margin: 0; font-size: clamp(1.12rem, 3.8vw, 1.28rem); font-weight: 500; word-break: keep-all; }
.quiz p { font-size: clamp(1.2rem, 4.2vw, 1.4rem); font-weight: 700; }
details { padding: 6px 20px 18px; }
summary {
  list-style: none; cursor: pointer; padding: 16px 0 8px;
  font-size: 1.1rem; font-weight: 700; color: var(--ink);
}
summary::-webkit-details-marker { display: none; }
summary::after {
  content: "▾ 정답·해설 펼치기"; display: block; margin-top: 8px;
  color: var(--accent); font-size: 0.95rem; font-weight: 700;
}
details[open] summary::after { content: "▴ 접기"; }
.answer { margin-top: 8px; padding-top: 14px; border-top: 1px solid var(--line); }
.badge {
  display: inline-block; min-width: 2.4rem; text-align: center;
  padding: 6px 12px; border-radius: 999px; background: var(--accent);
  color: #062214; font-weight: 900; font-size: 1.25rem; margin-bottom: 12px;
}
.pager { display: flex; gap: 10px; margin-top: 24px; }
.pager a, .pager span {
  flex: 1; padding: 14px 12px; border-radius: 14px; text-align: center;
  border: 1px solid var(--line); font-weight: 700; font-size: 0.95rem;
}
.pager a { color: var(--accent); }
.pager span { color: var(--muted); opacity: 0.5; }
.list { display: flex; flex-direction: column; gap: 12px; }
.item { display: block; padding: 18px 20px; }
.item .when { color: var(--muted); font-size: 0.9rem; margin-bottom: 6px; }
.item .title { font-size: 1.15rem; font-weight: 700; word-break: keep-all; }
.new {
  display: inline-block; margin-left: 8px; padding: 2px 8px; border-radius: 999px;
  background: var(--accent); color: #062214; font-size: 0.75rem; font-weight: 900;
  vertical-align: middle;
}
footer { margin-top: 28px; color: var(--muted); font-size: 0.85rem; text-align: center; }
"""


def _page(title: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
  <title>{title}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;900&family=Noto+Serif+KR:wght@600;700&display=swap" rel="stylesheet" />
  <style>{STYLE}</style>
</head>
<body>
  <main>
{body}
  </main>
</body>
</html>
"""


def render_lesson_html(
    lesson: dict[str, Any],
    prev_id: str | None,
    next_id: str | None,
) -> str:
    topic = _esc(lesson["topic"])
    answer = _esc(str(lesson["answer"]).strip().upper())
    prev_link = (
        f'<a href="{prev_id}.html">← 이전 학습</a>' if prev_id else "<span>← 이전 학습</span>"
    )
    next_link = (
        f'<a href="{next_id}.html">다음 학습 →</a>' if next_id else "<span>다음 학습 →</span>"
    )
    body = f"""    <nav class="topnav"><a href="index.html">☰ 지난 학습 전체 보기</a></nav>
    <div class="eyebrow">CUSTOMS · TRADE</div>
    <h1>{topic}</h1>
    <div class="date">관세직 7급 무역학 · {date_label(lesson["date"])}</div>

    <section>
      <h2>핵심요약</h2>
      <p>{_esc(lesson["summary"])}</p>
    </section>

    <section class="quiz">
      <h2>O / X 퀴즈</h2>
      <p>{_esc(lesson["quiz"])}</p>
    </section>

    <details>
      <summary>스스로 답한 뒤 확인</summary>
      <div class="answer">
        <div class="badge">{answer}</div>
        <p>{_esc(lesson["explanation"])}</p>
      </div>
    </details>

    <div class="pager">{prev_link}{next_link}</div>"""
    return _page(f"관세직 7급 무역학 · {topic}", body)


def render_index_html(lessons: list[dict[str, Any]]) -> str:
    items = []
    for i, lesson in enumerate(reversed(lessons)):
        new_badge = '<span class="new">최신</span>' if i == 0 else ""
        items.append(
            f'      <a class="item" href="{lesson["id"]}.html">\n'
            f'        <div class="when">{date_label(lesson["date"])}{new_badge}</div>\n'
            f'        <div class="title">{_esc(lesson["topic"])}</div>\n'
            f"      </a>"
        )
    body = f"""    <div class="eyebrow">CUSTOMS · TRADE</div>
    <h1>무역학 학습 기록</h1>
    <div class="date">관세직 7급 무역학 · 총 {len(lessons)}개</div>
    <div class="list">
{chr(10).join(items)}
    </div>
    <footer>날짜를 누르면 그날 학습으로 이동합니다</footer>"""
    return _page("관세직 7급 무역학 · 학습 기록", body)


def build_site(open_browser: bool = False) -> None:
    lessons = load_lessons()
    if not lessons:
        raise RuntimeError("lessons/ 에 학습이 없습니다.")
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    for i, lesson in enumerate(lessons):
        prev_id = lessons[i - 1]["id"] if i > 0 else None
        next_id = lessons[i + 1]["id"] if i + 1 < len(lessons) else None
        (DOCS_DIR / f"{lesson['id']}.html").write_text(
            render_lesson_html(lesson, prev_id, next_id), encoding="utf-8"
        )
    INDEX_HTML.write_text(render_index_html(lessons), encoding="utf-8")
    print(f"사이트 생성: 학습 {len(lessons)}개 → {DOCS_DIR}")
    if open_browser:
        latest = DOCS_DIR / f"{lessons[-1]['id']}.html"
        webbrowser.open(latest.resolve().as_uri())


# ---------------------------------------------------------------- kakao


def refresh_kakao_access_token() -> str:
    if not KAKAO_REST_API_KEY or not KAKAO_REFRESH_TOKEN:
        if KAKAO_ACCESS_TOKEN:
            return KAKAO_ACCESS_TOKEN
        raise RuntimeError("KAKAO_REFRESH_TOKEN + KAKAO_REST_API_KEY 가 필요합니다.")

    data = {
        "grant_type": "refresh_token",
        "client_id": KAKAO_REST_API_KEY,
        "refresh_token": KAKAO_REFRESH_TOKEN,
    }
    if KAKAO_CLIENT_SECRET:
        data["client_secret"] = KAKAO_CLIENT_SECRET

    resp = requests.post(KAKAO_TOKEN_URL, data=data, timeout=30)
    resp.raise_for_status()
    payload = resp.json()
    access = payload.get("access_token")
    if not access:
        raise RuntimeError(f"카카오 토큰 갱신 실패: {payload}")
    if "refresh_token" in payload:
        print("[경고] 새 refresh_token 발급됨 → GitHub Secrets 갱신 필요")
        print(f"NEW_REFRESH_TOKEN={payload['refresh_token']}")
    return access


def lesson_page_url(lesson: dict[str, Any]) -> str:
    if not CONTENT_BASE_URL:
        raise RuntimeError(
            "CONTENT_BASE_URL이 없습니다. "
            "GitHub Pages URL을 .env / Secrets에 넣으세요. "
            "예: https://USERNAME.github.io/muyukhak/"
        )
    return f"{CONTENT_BASE_URL}/{lesson['id']}.html"


def clip(text: str, limit: int) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def send_kakao_teaser(lesson: dict[str, Any]) -> None:
    """짧은 카드 — 탭하면 그날 학습 페이지가 열림"""
    page_url = lesson_page_url(lesson)
    link = {"web_url": page_url, "mobile_web_url": page_url}
    topic = clip(lesson["topic"], 22)
    template = {
        "object_type": "feed",
        "content": {
            "title": clip(f"오늘의 무역학 · {topic}", 40),
            "description": clip(
                f"{date_label(lesson['date'])} 학습이 도착했습니다. 탭하면 전체 내용이 크게 열립니다.",
                80,
            ),
            "link": link,
        },
        "buttons": [{"title": "전체 학습 보기", "link": link}],
    }

    access = refresh_kakao_access_token()
    headers = {
        "Authorization": f"Bearer {access}",
        "Content-Type": "application/x-www-form-urlencoded;charset=utf-8",
    }
    resp = requests.post(
        KAKAO_MEMO_SEND_URL,
        headers=headers,
        data={"template_object": json.dumps(template, ensure_ascii=False)},
        timeout=30,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"카카오 전송 실패 ({resp.status_code}): {resp.text}")
    body = resp.json()
    if body.get("result_code", 0) != 0:
        raise RuntimeError(f"카카오 전송 실패: {body}")
    print(f"카카오 티저 전송 완료 → {page_url}")


# ---------------------------------------------------------------- cli


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--write-html",
        action="store_true",
        help="오늘 학습을 생성·저장하고 사이트를 다시 만든다",
    )
    parser.add_argument(
        "--build-site",
        action="store_true",
        help="lessons/ 로 사이트만 다시 만든다",
    )
    parser.add_argument(
        "--send-kakao",
        action="store_true",
        help="저장된 content.json으로 카카오 티저만 전송",
    )
    parser.add_argument("--open", action="store_true", help="HTML을 브라우저로 연다")
    args = parser.parse_args()

    if args.build_site:
        build_site(open_browser=args.open)
        return 0

    if args.send_kakao:
        send_kakao_teaser(load_content())
        return 0

    print("=== 관세직 7급 무역학 일일 콘텐츠 생성 ===")
    lesson = save_lesson(generate_daily_content())
    print(json.dumps(lesson, ensure_ascii=False, indent=2))
    do_both = not args.write_html
    build_site(open_browser=args.open or do_both)

    if args.write_html:
        return 0

    if os.environ.get("DRY_RUN", "").lower() in ("1", "true", "yes"):
        print("DRY_RUN=true → 카카오 전송 생략")
        return 0

    if not CONTENT_BASE_URL:
        print("[안내] CONTENT_BASE_URL이 없어 카카오 전송은 건너뜁니다.")
        return 0

    send_kakao_teaser(lesson)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
