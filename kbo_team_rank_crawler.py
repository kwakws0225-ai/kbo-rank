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
    "Referer": "https://www.koreabaseball.com/",
}

# 결과 저장 폴더 (스크립트와 같은 위치에 data/ 폴더 생성)
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def crawl_kbo_team_rank(save_csv: bool = True) -> pd.DataFrame:
    """KBO 팀 순위표를 크롤링해서 DataFrame으로 반환합니다."""
    resp = requests.get(URL, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    resp.encoding = "utf-8"

    # 페이지 내 모든 <table> 을 파싱한 뒤, '순위'와 '팀명' 컬럼이 있는 표를 찾음
    tables = pd.read_html(io.StringIO(resp.text))

    rank_df = None
    for t in tables:
        cols = [str(c) for c in t.columns]
        if any("순위" in c for c in cols) and any("팀명" in c for c in cols):
            rank_df = t
            break

    if rank_df is None:
        raise RuntimeError(
            "팀 순위 테이블을 찾지 못했습니다. "
            "KBO 사이트의 페이지 구조가 변경되었을 수 있습니다."
        )

    if save_csv:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        now = datetime.now()

        # 1) 실행할 때마다 기록이 남는 타임스탬프 파일 (하루 여러 번 실행해도 안 겹침)
        stamped_name = os.path.join(
            OUTPUT_DIR, f"kbo_team_rank_{now.strftime('%Y%m%d_%H%M')}.csv"
        )
        rank_df.to_csv(stamped_name, index=False, encoding="utf-8-sig")

        # 2) 항상 최신 상태만 덮어쓰는 파일 (매번 이 파일만 확인하면 됨)
        latest_name = os.path.join(OUTPUT_DIR, "kbo_team_rank_latest.csv")
        rank_df.to_csv(latest_name, index=False, encoding="utf-8-sig")

        print(f"저장 완료: {stamped_name}")
        print(f"최신본 갱신: {latest_name}")

    return rank_df


if __name__ == "__main__":
    df = crawl_kbo_team_rank()
    print(df.to_string(index=False))
