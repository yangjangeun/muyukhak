"""
카카오 OAuth로 refresh_token 발급받기.

사전 조건:
1. 카카오 디벨로퍼스에서 카카오 로그인 ON
2. Redirect URI에 정확히 등록: http://localhost:8765/oauth
   (플랫폼 키 > REST API 키 안에 등록)
3. 동의항목 talk_message 설정
4. .env에 KAKAO_REST_API_KEY 저장
   (클라이언트 시크릿 ON이면 KAKAO_CLIENT_SECRET도 필요)

실행:
  python get_kakao_token.py
"""

from __future__ import annotations

import json
import os
import threading
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import requests
from dotenv import load_dotenv

# 5000은 다른 앱과 충돌하는 경우가 많아 8765 사용
REDIRECT_URI = "http://localhost:8765/oauth"
CALLBACK_PORT = 8765
SCOPE = "talk_message"
ENV_PATH = Path(__file__).resolve().parent / ".env"

load_dotenv(ENV_PATH)

REST_API_KEY = os.environ.get("KAKAO_REST_API_KEY", "").strip()
CLIENT_SECRET = os.environ.get("KAKAO_CLIENT_SECRET", "").strip()
# scope 없이 테스트: $env:KAKAO_SKIP_SCOPE='1'
SKIP_SCOPE = os.environ.get("KAKAO_SKIP_SCOPE", "").lower() in ("1", "true", "yes")


class OAuthHandler(BaseHTTPRequestHandler):
    code: str | None = None
    error: str | None = None

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/oauth":
            self.send_response(404)
            self.end_headers()
            return

        qs = urllib.parse.parse_qs(parsed.query)
        if "error" in qs:
            OAuthHandler.error = qs.get("error_description", qs["error"])[0]
            body = "<h1>인가 실패</h1><p>터미널을 확인하세요.</p>"
        else:
            OAuthHandler.code = qs.get("code", [None])[0]
            body = (
                "<h1>인가 성공</h1>"
                "<p>이 창을 닫고 터미널을 확인하세요.</p>"
            )

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

        # 응답 후 서버 종료
        threading.Thread(target=self.server.shutdown, daemon=True).start()

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


def upsert_env(key: str, value: str) -> None:
    text = ENV_PATH.read_text(encoding="utf-8-sig") if ENV_PATH.exists() else ""
    lines = text.splitlines()
    prefix = f"{key}="
    updated = False
    new_lines: list[str] = []
    for line in lines:
        if line.startswith(prefix) or line.startswith(f"#{prefix}"):
            new_lines.append(f"{key}={value}")
            updated = True
        else:
            new_lines.append(line)
    if not updated:
        if new_lines and new_lines[-1].strip():
            new_lines.append("")
        new_lines.append(f"{key}={value}")
    ENV_PATH.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def exchange_code(code: str) -> dict:
    data = {
        "grant_type": "authorization_code",
        "client_id": REST_API_KEY,
        "redirect_uri": REDIRECT_URI,
        "code": code,
    }
    if CLIENT_SECRET:
        data["client_secret"] = CLIENT_SECRET

    resp = requests.post(
        "https://kauth.kakao.com/oauth/token",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded;charset=utf-8"},
        timeout=30,
    )
    payload = resp.json()
    if resp.status_code != 200:
        raise RuntimeError(f"토큰 발급 실패 ({resp.status_code}): {payload}")
    return payload


def main() -> None:
    if not REST_API_KEY:
        raise SystemExit(".env에 KAKAO_REST_API_KEY를 먼저 넣어 주세요.")

    params = {
        "client_id": REST_API_KEY,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
    }
    if not SKIP_SCOPE:
        params["scope"] = SCOPE
    else:
        print("[안내] KAKAO_SKIP_SCOPE=1 → scope 없이 로그인만 시도합니다.")
        print("메시지 전송에는 talk_message 동의항목 설정이 반드시 필요합니다.\n")

    auth_url = (
        "https://kauth.kakao.com/oauth/authorize?"
        + urllib.parse.urlencode(params)
    )

    server = HTTPServer(("127.0.0.1", CALLBACK_PORT), OAuthHandler)
    print(f"로컬 콜백 서버 시작: {REDIRECT_URI}")
    print("브라우저에서 카카오 로그인·동의를 완료하세요.")
    print(f"(Redirect URI가 정확히 {REDIRECT_URI} 인지 확인)")
    print()
    print("*** KOE205가 뜨면 아래를 먼저 하세요 ***")
    print("  카카오 디벨로퍼스 → 내 앱 → 카카오 로그인 → 동의항목")
    print("  → [접근권한] 탭 → '카카오톡 메시지 전송' → 설정")
    print("  → 동의 단계: 선택 동의 → 저장")
    print()
    if not CLIENT_SECRET:
        print("[경고] KAKAO_CLIENT_SECRET이 없습니다.")
        print("  플랫폼 키 > REST API 키 > 클라이언트 시크릿이 ON이면 .env에 넣으세요.")
        print()
    print(auth_url)
    print()

    webbrowser.open(auth_url)
    server.serve_forever()
    server.server_close()

    if OAuthHandler.error:
        raise SystemExit(f"인가 실패: {OAuthHandler.error}")
    if not OAuthHandler.code:
        raise SystemExit("인가 코드를 받지 못했습니다.")

    print("인가 코드 수신 → 토큰 교환 중...")
    token = exchange_code(OAuthHandler.code)

    refresh = token.get("refresh_token")
    access = token.get("access_token")
    if not refresh:
        raise SystemExit(f"refresh_token이 없습니다. 응답: {json.dumps(token, ensure_ascii=False)}")

    upsert_env("KAKAO_REFRESH_TOKEN", refresh)
    if access:
        upsert_env("KAKAO_ACCESS_TOKEN", access)

    print()
    print("성공! .env에 KAKAO_REFRESH_TOKEN을 저장했습니다.")
    print(f"access_token 만료(초): {token.get('expires_in')}")
    print(f"refresh_token 만료(초): {token.get('refresh_token_expires_in')}")
    print()
    print("이제 테스트:")
    print("  python main.py")


if __name__ == "__main__":
    main()
