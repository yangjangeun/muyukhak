"""
관세직 7급 무역학 일일 학습
1) Gemini로 콘텐츠 생성
2) 모바일에서 크게 읽히는 HTML 학습 페이지 저장 (docs/index.html)
3) 카카오톡에는 '탭하면 전체 보기' 카드 전송 → 링크가 HTML 페이지로 이동
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import webbrowser
from datetime import datetime
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
CONTENT_JSON = ROOT / "content.json"
HTML_PATH = DOCS_DIR / "index.html"

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
KAKAO_REST_API_KEY = os.environ.get("KAKAO_REST_API_KEY", "")
KAKAO_CLIENT_SECRET = os.environ.get("KAKAO_CLIENT_SECRET", "")
KAKAO_REFRESH_TOKEN = os.environ.get("KAKAO_REFRESH_TOKEN", "")
KAKAO_ACCESS_TOKEN = os.environ.get("KAKAO_ACCESS_TOKEN", "")
# 탭 시 열릴 학습 페이지 URL (GitHub Pages 등). 끝에 / 권장
CONTENT_BASE_URL = os.environ.get("CONTENT_BASE_URL", "").rstrip("/")

KAKAO_TOKEN_URL = "https://kauth.kakao.com/oauth/token"
KAKAO_MEMO_SEND_URL = "https://kapi.kakao.com/v2/api/talk/memo/default/send"

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


def today_label() -> str:
    return datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y.%m.%d")


def pick_topic_hint() -> str:
    day = datetime.now(ZoneInfo("Asia/Seoul")).timetuple().tm_yday
    return TRADE_TOPICS[day % len(TRADE_TOPICS)]


def generate_daily_content() -> dict[str, Any]:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY 환경변수가 필요합니다.")

    client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = f"""당신은 대한민국 공무원 시험 '관세직 7급 무역학' 전문 강사입니다.
오늘 날짜: {today_label()}
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


def _esc(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def render_html(content: dict[str, Any]) -> str:
    date_str = today_label()
    answer = str(content["answer"]).strip().upper()
    topic = _esc(content["topic"])
    summary = _esc(content["summary"])
    quiz = _esc(content["quiz"])
    explanation = _esc(content["explanation"])
    answer_esc = _esc(answer)

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
  <title>관세직 7급 무역학 · {topic}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;900&family=Noto+Serif+KR:wght@600;700&display=swap" rel="stylesheet" />
  <style>
    :root {{
      --bg: #0f1c17;
      --panel: #162820;
      --ink: #f3f6f2;
      --muted: #a8b8ae;
      --accent: #3dba7a;
      --line: rgba(243, 246, 242, 0.12);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100dvh;
      font-family: "Noto Sans KR", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(1200px 600px at 10% -10%, #1e3d30 0%, transparent 55%),
        radial-gradient(900px 500px at 100% 0%, #243528 0%, transparent 50%),
        var(--bg);
      line-height: 1.65;
    }}
    main {{
      width: min(720px, 100%);
      margin: 0 auto;
      padding: 28px 20px 64px;
    }}
    .eyebrow {{
      font-size: 0.85rem;
      letter-spacing: 0.08em;
      color: var(--accent);
      font-weight: 700;
      margin-bottom: 10px;
    }}
    h1 {{
      font-family: "Noto Serif KR", serif;
      font-size: clamp(1.85rem, 6vw, 2.45rem);
      line-height: 1.25;
      margin: 0 0 10px;
      font-weight: 700;
    }}
    .date {{
      color: var(--muted);
      font-size: 0.95rem;
      margin-bottom: 28px;
    }}
    section {{
      background: color-mix(in srgb, var(--panel) 88%, black);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 22px 20px;
      margin-bottom: 16px;
    }}
    h2 {{
      margin: 0 0 12px;
      font-size: 1.05rem;
      color: var(--accent);
      letter-spacing: -0.01em;
    }}
    p {{
      margin: 0;
      font-size: clamp(1.12rem, 3.8vw, 1.28rem);
      font-weight: 500;
      word-break: keep-all;
    }}
    .quiz p {{
      font-size: clamp(1.2rem, 4.2vw, 1.4rem);
      font-weight: 700;
    }}
    details {{
      background: color-mix(in srgb, var(--panel) 88%, black);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 6px 20px 18px;
    }}
    summary {{
      list-style: none;
      cursor: pointer;
      padding: 16px 0 8px;
      font-size: 1.1rem;
      font-weight: 700;
      color: var(--ink);
    }}
    summary::-webkit-details-marker {{ display: none; }}
    summary::after {{
      content: "▾ 정답·해설 펼치기";
      display: block;
      margin-top: 8px;
      color: var(--accent);
      font-size: 0.95rem;
      font-weight: 700;
    }}
    details[open] summary::after {{
      content: "▴ 접기";
    }}
    .answer {{
      margin-top: 8px;
      padding-top: 14px;
      border-top: 1px solid var(--line);
    }}
    .badge {{
      display: inline-block;
      min-width: 2.4rem;
      text-align: center;
      padding: 6px 12px;
      border-radius: 999px;
      background: var(--accent);
      color: #062214;
      font-weight: 900;
      font-size: 1.25rem;
      margin-bottom: 12px;
    }}
    footer {{
      margin-top: 28px;
      color: var(--muted);
      font-size: 0.85rem;
      text-align: center;
    }}
  </style>
</head>
<body>
  <main>
    <div class="eyebrow">CUSTOMS · TRADE</div>
    <h1>{topic}</h1>
    <div class="date">관세직 7급 무역학 · {date_str}</div>

    <section>
      <h2>핵심요약</h2>
      <p>{summary}</p>
    </section>

    <section class="quiz">
      <h2>O / X 퀴즈</h2>
      <p>{quiz}</p>
    </section>

    <details>
      <summary>스스로 답한 뒤 확인</summary>
      <div class="answer">
        <div class="badge">{answer_esc}</div>
        <p>{explanation}</p>
      </div>
    </details>

    <footer>탭해서 들어온 학습 페이지 · 매일 아침 갱신</footer>
  </main>
</body>
</html>
"""


def write_html(content: dict[str, Any], open_browser: bool = False) -> Path:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    html = render_html(content)
    HTML_PATH.write_text(html, encoding="utf-8")
    CONTENT_JSON.write_text(
        json.dumps(content, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"HTML 저장: {HTML_PATH}")
    if open_browser:
        webbrowser.open(HTML_PATH.resolve().as_uri())
    return HTML_PATH


def load_content() -> dict[str, Any]:
    if not CONTENT_JSON.exists():
        raise RuntimeError("content.json이 없습니다. 먼저 콘텐츠를 생성하세요.")
    return json.loads(CONTENT_JSON.read_text(encoding="utf-8"))


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


def content_page_url() -> str:
    if not CONTENT_BASE_URL:
        raise RuntimeError(
            "CONTENT_BASE_URL이 없습니다. "
            "GitHub Pages URL을 .env / Secrets에 넣으세요. "
            "예: https://USERNAME.github.io/muyukhak/"
        )
    return CONTENT_BASE_URL if CONTENT_BASE_URL.endswith(".html") else f"{CONTENT_BASE_URL}/"


def clip(text: str, limit: int) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def send_kakao_teaser(content: dict[str, Any]) -> None:
    """짧은 티저 카드 — 탭하면 학습 HTML이 크게 열림"""
    page_url = content_page_url()
    link = {"web_url": page_url, "mobile_web_url": page_url}
    topic = clip(content["topic"], 22)
    template = {
        "object_type": "feed",
        "content": {
            "title": clip(f"오늘의 무역학 · {topic}", 40),
            "description": clip(
                f"{today_label()} 학습이 도착했습니다. 탭하면 전체 내용이 크게 열립니다.",
                80,
            ),
            "link": link,
        },
        "buttons": [
            {
                "title": "전체 학습 보기",
                "link": link,
            }
        ],
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--write-html",
        action="store_true",
        help="콘텐츠 생성 후 HTML만 저장",
    )
    parser.add_argument(
        "--send-kakao",
        action="store_true",
        help="저장된 content.json으로 카카오 티저만 전송",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="HTML을 브라우저로 연다",
    )
    args = parser.parse_args()

    write_only = args.write_html
    kakao_only = args.send_kakao
    do_both = not write_only and not kakao_only

    if kakao_only:
        content = load_content()
    else:
        print("=== 관세직 7급 무역학 일일 콘텐츠 생성 ===")
        content = generate_daily_content()
        print(json.dumps(content, ensure_ascii=False, indent=2))
        write_html(content, open_browser=args.open or do_both)

    if write_only:
        return 0

    dry_run = os.environ.get("DRY_RUN", "").lower() in ("1", "true", "yes")
    if dry_run:
        print("DRY_RUN=true → 카카오 전송 생략")
        return 0

    if do_both and not CONTENT_BASE_URL:
        print(
            "\n[안내] CONTENT_BASE_URL이 없어 카카오 전송은 건너뜁니다.\n"
            "로컬 HTML은 브라우저에서 확인하세요.\n"
            "GitHub Pages 배포 후 CONTENT_BASE_URL을 설정하면\n"
            "카카오 탭 시 이 학습 페이지가 크게 열립니다."
        )
        return 0

    send_kakao_teaser(content)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
