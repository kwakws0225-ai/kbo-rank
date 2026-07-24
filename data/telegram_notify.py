"""
텔레그램으로 KBO 순위 이미지 전송
--------------------------------
환경변수로 TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID 를 받아서
data/kbo_rank_image_latest.png 를 텔레그램 챗으로 전송합니다.

필요 패키지: pip install requests

실행:
    python telegram_notify.py
"""

import os
import sys
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_PATH = os.path.join(BASE_DIR, "data", "kbo_rank_image_latest.png")


def send_to_telegram():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("TELEGRAM_BOT_TOKEN 또는 TELEGRAM_CHAT_ID 환경변수가 없습니다.")
        sys.exit(1)

    if not os.path.exists(IMAGE_PATH):
        print("이미지 파일을 찾을 수 없습니다: " + IMAGE_PATH)
        sys.exit(1)

    url = "https://api.telegram.org/bot" + token + "/sendPhoto"

    with open(IMAGE_PATH, "rb") as f:
        files = {"photo": f}
        data = {"chat_id": chat_id, "caption": "오늘의 KBO 팀 순위"}
        resp = requests.post(url, data=data, files=files, timeout=20)

    if resp.status_code == 200:
        print("텔레그램 전송 성공")
    else:
        print("텔레그램 전송 실패: " + str(resp.status_code) + " " + resp.text)
        sys.exit(1)


if __name__ == "__main__":
    send_to_telegram()
