"""
KBO(한국야구위원회) 팀 순위 자동 크롤러
--------------------------------------
https://www.koreabaseball.com/Record/TeamRank/TeamRank.aspx 의
정규시즌 팀 순위표를 가져와 CSV로 저장합니다.

필요 패키지 설치:
    pip install requests pandas lxml

실행:
    python kbo_team_rank_crawler.py
"""

import os
import io
import requests
import pandas as pd
from datetime import datetime

URL = "https://www.koreabaseball.com/Record/TeamRank/TeamRank.aspx"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Referer":
