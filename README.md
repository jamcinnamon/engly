# ENGLY · 원리 영어 노트

외우지 말고 원리로 익히는 영어 노트. 내 맥에서 돌아가는 작은 웹앱이에요.

| 탭 | 하는 일 |
|---|---|
| 1 궁금한 영어 | 영어 표현을 넣으면 왜 그런 뜻이 되는지 핵심 느낌·어원으로 풀어줘요 |
| 2 네이티브 번역 | 한국어는 원어민 영어로, 영어는 속뜻까지 담은 한국어로 바꾸고, 다시 쓸 패턴을 뽑아줘요 |
| 3 공부 | 1·2에서 저장한 카드를 1·3·7·14·30일 간격으로 복습해요 |

## 필요한 것
- [Claude Code](https://claude.com/claude-code) (`claude` 명령어, 로그인된 상태). AI 답변은 이걸 통해 받아서 API 키가 따로 필요 없어요.
- Python 3.9 이상 (외부 패키지 없음)

## 실행
```bash
cp config.example.js config.local.js   # 선택: AI가 나를 부를 이름 정하기
python3 server.py
# 브라우저에서 http://127.0.0.1:8765
```
카드는 같은 폴더의 `cards.json`에 저장돼요 (git에는 안 올라가요).

## 고치고 싶을 때
| 파일 | 하는 일 |
|---|---|
| index.html | 화면, 프롬프트(`PROMPTS`), 복습 간격(`INTERVALS`) |
| server.py | 카드 저장, claude CLI 호출, 모델(`MODEL_NORMAL` / `MODEL_QUICK`) |
| local-bridge.js | 화면과 서버를 잇는 연결 파일 (답변 스트리밍) |
| config.local.js | 내 이름 설정 (git 제외) |

서버는 내 컴퓨터(127.0.0.1)에서만 열리고, 이 앱 화면에서 온 요청만 받아요.
