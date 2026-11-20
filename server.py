"""원리 영어 노트 — 로컬 서버

- index.html 을 보여주고
- 카드는 cards.json 파일에 저장하고
- AI 답변은 내 맥의 claude CLI(구독 요금제)로 받아요. API 키 필요 없음.

실행: python3 server.py   →  http://localhost:8765
"""
import json
import os
import subprocess
import threading
import time
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

PORT = 8765
HERE = os.path.dirname(os.path.abspath(__file__))
CARDS_FILE = os.path.join(HERE, "cards.json")
CLAUDE = os.path.expanduser("~/.local/bin/claude")

# 모델 바꾸고 싶으면 여기만 고치면 돼요
MODEL_NORMAL = "sonnet"   # 왜 / 어떻게 탭
MODEL_QUICK = "haiku"     # 복습 문장 확인

lock = threading.Lock()
ERR_MARK = "\u0000ERR:"


def load_cards() -> dict:
    try:
        with open(CARDS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_cards(cards: dict) -> None:
    tmp = CARDS_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cards, f, ensure_ascii=False, indent=2)
    os.replace(tmp, CARDS_FILE)


def to_prompt(messages) -> str:
    """대화 기록(리스트)을 claude -p 에 넣을 한 덩어리 글로 바꿔요."""
    if isinstance(messages, str):
        return messages
    if len(messages) == 1:
        return messages[0]["content"]
    parts = ["아래는 지금까지의 대화예요. 마지막 사용자 말에만 답하세요.\n"]
    for m in messages:
        who = "사용자" if m["role"] == "user" else "코치(너)"
        parts.append(f"[{who}]\n{m['content']}\n")
    return "\n".join(parts)


def claude_cmd(quick: bool) -> list:
    return [
        CLAUDE, "-p",
        "--model", MODEL_QUICK if quick else MODEL_NORMAL,
        "--tools", "",
        "--setting-sources", "",
        "--no-session-persistence",
        "--output-format", "stream-json", "--include-partial-messages", "--verbose",
        "--system-prompt", "너는 영어 코치 앱의 답변 엔진이다. 사용자 메시지의 지시를 그대로 따른다.",
    ]


def stream_claude(messages, quick=False):
    """답변을 글자 조각(delta)으로 하나씩 내보내요. 다 끝나면 멈춰요."""
    proc = subprocess.Popen(
        claude_cmd(quick), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True, cwd=HERE,
    )
    proc.stdin.write(to_prompt(messages))
    proc.stdin.close()
    sent = False
    try:
        for line in proc.stdout:
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            if ev.get("type") == "stream_event":
                d = ev["event"].get("delta") or {}
                if d.get("type") == "text_delta":
                    sent = True
                    yield d["text"]
            elif ev.get("type") == "result" and ev.get("is_error"):
                raise RuntimeError(ev.get("result") or "claude 오류")
        proc.wait(timeout=10)
        if proc.returncode != 0 and not sent:
            raise RuntimeError(proc.stderr.read().strip() or "claude 실행 실패")
    finally:
        if proc.poll() is None:   # 화면에서 '멈추기'를 누르면 여기서 끝내요
            proc.kill()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=HERE, **kw)

    def log_message(self, *a):
        pass

    def send_json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}")

    def do_GET(self):
        if self.path == "/api/cards":
            if not self.from_this_app():
                return self.send_json({"error": "forbidden"}, 403)
            with lock:
                return self.send_json(load_cards())
        if self.path in ("/", ""):
            self.path = "/index.html"
        return super().do_GET()

    def from_this_app(self) -> bool:
        """다른 웹사이트가 몰래 이 서버를 부르지 못하게, 이 앱 화면에서 온 요청만 받아요."""
        ok = {f"127.0.0.1:{PORT}", f"localhost:{PORT}"}
        origin = self.headers.get("Origin", "")
        return self.headers.get("Host") in ok and (
            not origin or origin.split("//", 1)[-1] in ok
        )

    def do_POST(self):
        if not self.from_this_app():
            return self.send_json({"error": "forbidden"}, 403)
        body = self.read_json()
        if self.path == "/api/sample":
            # 글자가 생기는 대로 바로 보내요. 오류는 맨 끝에 ERR_MARK 뒤에 붙여요.
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            gen = stream_claude(body.get("messages"), body.get("quick", False))
            try:
                for piece in gen:
                    self.wfile.write(piece.encode())
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                gen.close()
            except Exception as e:
                self.wfile.write((ERR_MARK + str(e)).encode())
            return
        if self.path == "/api/cards":   # 새 카드
            with lock:
                cards = load_cards()
                cid = "c" + str(int(time.time() * 1000))
                cards[cid] = body
                save_cards(cards)
            return self.send_json({"id": cid})
        if self.path.startswith("/api/cards/"):  # 카드 수정/삭제
            cid = self.path.rsplit("/", 1)[1]
            with lock:
                cards = load_cards()
                if body.get("_delete"):
                    cards.pop(cid, None)
                else:
                    cards[cid] = body
                save_cards(cards)
            return self.send_json({"ok": True})
        self.send_json({"error": "not found"}, 404)


if __name__ == "__main__":
    print(f"원리 영어 노트: http://localhost:{PORT}")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
