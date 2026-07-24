"""
텔레그램 즉시 응답 스크립트 (repository_dispatch로 트리거됨)
--------------------------------------------------------
Cloudflare Worker가 GitHub repository_dispatch를 호출하면 이 스크립트가
바로 실행되어, 그 메시지를 보낸 chat_id로 최신 순위 이미지를 답장합니다.

환경변수:
    TELEGRAM_BOT_TOKEN, CHAT_ID, MATCHED (true/false)

필요 패키지: pip install requests
"""

import os
import sys
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_PATH = os.path.join(BASE_DIR, "data", "kbo_rank_image_latest.png")


def send_photo(token, chat_id):
    url = "https://api.telegram.org/bot" + token + "/sendPhoto"
    with open(IMAGE_PATH, "rb") as f:
        files = {"photo": f}
        data = {"chat_id": chat_id, "caption": "요청하신 최신 KBO 팀 순위입니다."}
        resp = requests.post(url, data=data, files=files, timeout=20)
    if resp.status_code == 200:
        print("이미지 전송 성공")
    else:
        print("이미지 전송 실패 (" + str(resp.status_code) + "): " + resp.text)


def send_text(token, chat_id, text):
    url = "https://api.telegram.org/bot" + token + "/sendMessage"
    resp = requests.post(url, data={"chat_id": chat_id, "text": text}, timeout=15)
    if resp.status_code != 200:
        print("텍스트 전송 실패 (" + str(resp.status_code) + "): " + resp.text)


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("CHAT_ID")
    matched = os.environ.get("MATCHED", "false").lower() == "true"

    if not token or not chat_id:
        print("TELEGRAM_BOT_TOKEN 또는 CHAT_ID 환경변수가 없습니다.")
        sys.exit(1)

    if not matched:
        send_text(token, chat_id, "'순위' 또는 '이미지' 라고 보내시면 최신 순위표를 바로 보내드려요.")
        return

    if not os.path.exists(IMAGE_PATH):
        send_text(token, chat_id, "아직 생성된 순위 이미지가 없습니다.")
        return

    send_photo(token, chat_id)


if __name__ == "__main__":
    main()
