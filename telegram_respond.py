"""
텔레그램 요청 응답 봇 (폴링 방식, GitHub Actions로 주기적 실행)
------------------------------------------------------------
사용자가 봇에게 '/순위', '순위', '이미지', 'kbo' 등의 메시지를 보내면
가장 최근의 순위 이미지를 답장으로 보내줍니다.

마지막으로 처리한 메시지 update_id 를 data/.last_update_id 에 저장해
같은 메시지에 중복 응답하지 않습니다.

환경변수: TELEGRAM_BOT_TOKEN
필요 패키지: pip install requests

실행: python telegram_respond.py
"""

import os
import sys
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
IMAGE_PATH = os.path.join(DATA_DIR, "kbo_rank_image_latest.png")
OFFSET_PATH = os.path.join(DATA_DIR, ".last_update_id")

# 이 단어들이 메시지에 포함되면 이미지를 보냄
TRIGGER_WORDS = ["순위", "이미지", "kbo", "KBO", "표", "/rank", "/순위", "/start"]


def load_offset():
    if not os.path.exists(OFFSET_PATH):
        return 0
    with open(OFFSET_PATH, "r") as f:
        try:
            return int(f.read().strip())
        except ValueError:
            return 0


def save_offset(update_id):
    with open(OFFSET_PATH, "w") as f:
        f.write(str(update_id))


def get_updates(token, offset):
    url = "https://api.telegram.org/bot" + token + "/getUpdates"
    params = {"offset": offset + 1, "timeout": 5}
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json().get("result", [])


def send_photo(token, chat_id):
    url = "https://api.telegram.org/bot" + token + "/sendPhoto"
    with open(IMAGE_PATH, "rb") as f:
        files = {"photo": f}
        data = {"chat_id": chat_id, "caption": "요청하신 최신 KBO 팀 순위입니다."}
        requests.post(url, data=data, files=files, timeout=20)


def send_text(token, chat_id, text):
    url = "https://api.telegram.org/bot" + token + "/sendMessage"
    requests.post(url, data={"chat_id": chat_id, "text": text}, timeout=15)


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        print("TELEGRAM_BOT_TOKEN 환경변수가 없습니다.")
        sys.exit(1)

    offset = load_offset()
    updates = get_updates(token, offset)

    if not updates:
        print("새 메시지 없음")
        return

    max_update_id = offset
    for u in updates:
        max_update_id = max(max_update_id, u["update_id"])
        msg = u.get("message") or u.get("edited_message")
        if not msg:
            continue
        chat_id = msg["chat"]["id"]
        text = (msg.get("text") or "").strip()

        if any(w.lower() in text.lower() for w in TRIGGER_WORDS):
            if os.path.exists(IMAGE_PATH):
                send_photo(token, chat_id)
                print("이미지 전송 -> chat_id " + str(chat_id))
            else:
                send_text(token, chat_id, "아직 생성된 순위 이미지가 없습니다.")
        else:
            send_text(token, chat_id, "'순위' 또는 '이미지' 라고 보내시면 최신 순위표를 보내드려요.")

    save_offset(max_update_id)


if __name__ == "__main__":
    main()
