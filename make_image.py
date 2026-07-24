"""
KBO 팀 순위 이미지 생성 (하이브리드 방식)
------------------------------------------
- 배경(background.png)은 피그마/캔바에서 만든 1080x1440 템플릿을 사용
- 이 스크립트는 그 위에 팀명/숫자만 정해진 좌표에 그려 넣습니다
- 배경 파일이 없으면 자동으로 데모 배경을 생성해 파이프라인이 바로 동작

필요 패키지:
    pip install pillow pandas

실행:
    python make_image.py
"""

import os
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
FONT_DIR = os.path.join(BASE_DIR, "fonts")
ASSET_DIR = os.path.join(BASE_DIR, "assets")

CSV_PATH = os.path.join(DATA_DIR, "kbo_team_rank_latest.csv")
BG_PATH = os.path.join(ASSET_DIR, "background.png")   # ← 여기에 본인 템플릿 넣기
OUT_LATEST = os.path.join(DATA_DIR, "kbo_rank_image_latest.png")

W, H = 1080, 1440

# ----------------------------------------------------------------------
# 좌표 설정 (config)
# 본인 피그마/캔바 템플릿에 맞춰 이 숫자만 조정하면 됩니다.
# ----------------------------------------------------------------------
LAYOUT = {
    "table_top": 300,      # 첫 번째 팀 행이 시작되는 y 좌표
    "row_height": 104,     # 행 간 간격
    # 각 컬럼의 중앙 x 좌표 (표시할 항목: 순위, 팀명, 경기, 승, 패, 무, 승률, 게임차)
    "columns": {
        "순위":  110,
        "팀명":  250,
        "경기":  430,
        "승":    530,
        "패":    620,
        "무":    710,
        "승률":  850,
        "게임차": 990,
    },
    "font_size": 40,
    "text_color": (30, 30, 30),
    "header_color": (255, 255, 255),
}


def load_fonts():
    bold = os.path.join(FONT_DIR, "Pretendard-Bold.otf")
    reg = os.path.join(FONT_DIR, "Pretendard-Regular.otf")
    fs = LAYOUT["font_size"]
    return {
        "row": ImageFont.truetype(reg, fs),
        "row_bold": ImageFont.truetype(bold, fs),
        "title": ImageFont.truetype(bold, 64),
        "small": ImageFont.truetype(reg, 30),
    }


def make_demo_background() -> Image.Image:
    """실제 템플릿이 없을 때 쓰는 데모 배경. (피그마/캔바 템플릿으로 교체 예정)"""
    img = Image.new("RGB", (W, H), (245, 247, 250))
    d = ImageDraw.Draw(img)
    fonts = load_fonts()

    # 상단 헤더 바
    d.rectangle([0, 0, W, 200], fill=(20, 40, 90))
    d.text((60, 70), "KBO 팀 순위", font=fonts["title"], fill=(255, 255, 255))

    # 표 헤더 줄
    header_y = LAYOUT["table_top"] - 70
    d.rectangle([40, header_y - 10, W - 40, header_y + 50], fill=(60, 90, 160))
    for name, x in LAYOUT["columns"].items():
        d.text((x, header_y), name, font=fonts["small"],
               fill=LAYOUT["header_color"], anchor="mm")

    # 행 구분선
    for i in range(10):
        y = LAYOUT["table_top"] + i * LAYOUT["row_height"]
        if i % 2 == 1:
            d.rectangle([40, y - 40, W - 40, y + 40], fill=(235, 238, 244))
    return img


def get_background() -> Image.Image:
    if os.path.exists(BG_PATH):
        bg = Image.open(BG_PATH).convert("RGB")
        return bg.resize((W, H)) if bg.size != (W, H) else bg
    print("※ assets/background.png 가 없어 데모 배경을 사용합니다.")
    return make_demo_background()


def render():
    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(
            f"{CSV_PATH} 없음. 먼저 kbo_team_rank_crawler.py 를 실행하세요."
        )

    df = pd.read_csv(CSV_PATH)
    fonts = load_fonts()
    img = get_background()
    d = ImageDraw.Draw(img)

    # CSV 컬럼명이 사이트 표기와 같다고 가정 (순위/팀명/경기/승/패/무/승률/게임차)
    for i, (_, row) in enumerate(df.iterrows()):
        y = LAYOUT["table_top"] + i * LAYOUT["row_height"]
        for col, x in LAYOUT["columns"].items():
            if col not in df.columns:
                continue
            val = str(row[col])
            font = fonts["row_bold"] if col in ("순위", "팀명") else fonts["row"]
            d.text((x, y), val, font=font, fill=LAYOUT["text_color"], anchor="mm")

    # 하단 갱신 시각
    from datetime import datetime
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M 기준")
    d.text((W - 60, H - 50), stamp, font=fonts["small"],
           fill=(120, 120, 120), anchor="rm")

    os.makedirs(DATA_DIR, exist_ok=True)
    img.save(OUT_LATEST)

    # 날짜별 백업본도 저장
    stamped = os.path.join(DATA_DIR, f"kbo_rank_image_{datetime.now():%Y%m%d}.png")
    img.save(stamped)
    print(f"이미지 저장: {OUT_LATEST}")
    print(f"백업본: {stamped}")


if __name__ == "__main__":
    render()
