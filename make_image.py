"""
KBO 팀 순위 이미지 생성 (하이브리드 방식 + 로고 + 3단 그룹 색상)
--------------------------------------------------------------
- 배경(assets/background.png)은 피그마에서 만든 1080x1440 템플릿을 사용
- 팀 로고는 assets/logos/*.png 에서 팀명에 맞춰 자동으로 붙여넣음
- 게임차 간격이 가장 크게 벌어지는 2곳을 기준으로 팀을 3그룹(강/중/약)으로
  나누고, 각 그룹마다 다른 색으로 행 배경을 반투명하게 얹음

필요 패키지:
    pip install pillow pandas

실행:
    python make_image.py
"""

import os
from datetime import datetime

import pandas as pd
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
FONT_DIR = os.path.join(BASE_DIR, "fonts")
ASSET_DIR = os.path.join(BASE_DIR, "assets")
LOGO_DIR = os.path.join(ASSET_DIR, "logos")

CSV_PATH = os.path.join(DATA_DIR, "kbo_team_rank_latest.csv")
BG_PATH = os.path.join(ASSET_DIR, "background.png")
OUT_LATEST = os.path.join(DATA_DIR, "kbo_rank_image_latest.png")

W, H = 1080, 1440

# ----------------------------------------------------------------------
# 팀명 -> 로고 파일명 매핑
# assets/logos/ 폴더에 아래 파일명으로 로고 PNG를 넣어주세요 (투명 배경 권장)
# ----------------------------------------------------------------------
TEAM_LOGO_FILES = {
    "삼성": "samsung.png",
    "KT": "kt.png",
    "LG": "lg.png",
    "KIA": "kia.png",
    "두산": "doosan.png",
    "한화": "hanwha.png",
    "NC": "nc.png",
    "롯데": "lotte.png",
    "SSG": "ssg.png",
    "키움": "kiwoom.png",
}

# ----------------------------------------------------------------------
# 좌표 / 스타일 설정 (config)
# 본인 피그마 템플릿에 맞춰 이 숫자들만 조정하면 됩니다.
# 아래 값은 업로드해주신 디자인 미리보기를 픽셀 분석해 추정한 값이라,
# 실제 1080x1440 배경 위에서 살짝 어긋날 수 있어요. 결과를 보고 미세조정하세요.
# ----------------------------------------------------------------------
LAYOUT = {
    "table_top": 400,       # 1번째 팀 행의 y 중심 좌표
    "row_height": 93,       # 행 간 간격
    "row_left": 55,         # 행 배경(그룹 색)의 왼쪽 x
    "row_right": 1025,      # 행 배경(그룹 색)의 오른쪽 x
    "row_radius": 14,       # 행 배경 모서리 둥글기
    "row_v_margin": 6,      # 위아래 행 사이 여백

    "logo_x": 215,          # 로고 중심 x
    "logo_size": 66,        # 로고 한 변 크기(px)

    "columns": {
        "순위": 118,
        "팀명": 300,
        "경기": 382,
        "승": 456,
        "패": 515,
        "무": 574,
        "승률": 655,
        "게임차": 751,
        "최근10경기": 868,
        "연속": 979,
    },

    "font_size": 32,
    "text_color": (40, 36, 34),
    "header_color": (255, 255, 255),

    # 3그룹(강/중/약) 배경 색상 - RGBA, 마지막 값이 투명도(0~255)
    "tier_colors": [
        (196, 214, 176, 130),   # 강 (연두)
        (238, 224, 205, 120),   # 중 (크림)
        (232, 170, 156, 130),   # 약 (코럴)
    ],
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
    """실제 템플릿이 없을 때 쓰는 데모 배경."""
    img = Image.new("RGB", (W, H), (245, 247, 250))
    d = ImageDraw.Draw(img)
    fonts = load_fonts()
    d.rectangle([0, 0, W, 200], fill=(20, 40, 90))
    d.text((60, 70), "KBO 팀 순위", font=fonts["title"], fill=(255, 255, 255))
    header_y = LAYOUT["table_top"] - LAYOUT["row_height"]
    d.rectangle([40, header_y - 30, W - 40, header_y + 30], fill=(60, 90, 160))
    for name, x in LAYOUT["columns"].items():
        d.text((x, header_y), name, font=fonts["small"],
               fill=LAYOUT["header_color"], anchor="mm")
    return img


def get_background() -> Image.Image:
    if os.path.exists(BG_PATH):
        bg = Image.open(BG_PATH).convert("RGB")
        return bg.resize((W, H)) if bg.size != (W, H) else bg
    print("※ assets/background.png 가 없어 데모 배경을 사용합니다.")
    return make_demo_background()


def parse_gap(value) -> float:
    """게임차 컬럼 값을 숫자로 변환 ('-' 는 1위, 0.0으로 취급)"""
    s = str(value).strip()
    if s in ("-", "", "nan"):
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def assign_tiers(gaps):
    """
    게임차 리스트를 받아 3그룹(강/중/약)으로 나눈 tier 인덱스 리스트를 반환.
    연속된 팀 사이의 게임차 증가폭이 가장 큰 2곳을 그룹 경계로 삼는다.
    """
    n = len(gaps)
    if n <= 3:
        return [0] * n

    diffs = [gaps[i + 1] - gaps[i] for i in range(n - 1)]
    # 차이가 큰 순으로 정렬해 상위 2개 인덱스(그룹 경계) 선택
    top2 = sorted(range(len(diffs)), key=lambda i: diffs[i], reverse=True)[:2]
    split_points = sorted(top2)

    tiers = []
    current = 0
    for i in range(n):
        tiers.append(current)
        if i in split_points:
            current += 1
    return tiers


def draw_tier_backgrounds(img: Image.Image, tiers) -> Image.Image:
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    margin = LAYOUT["row_v_margin"]
    half = LAYOUT["row_height"] / 2 - margin

    for i, tier in enumerate(tiers):
        yc = LAYOUT["table_top"] + i * LAYOUT["row_height"]
        top = yc - half
        bottom = yc + half
        color = LAYOUT["tier_colors"][tier]
        od.rounded_rectangle(
            [LAYOUT["row_left"], top, LAYOUT["row_right"], bottom],
            radius=LAYOUT["row_radius"],
            fill=color,
        )

    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")


def paste_logo(img: Image.Image, team_name: str, yc: float):
    filename = TEAM_LOGO_FILES.get(team_name)
    if not filename:
        return
    path = os.path.join(LOGO_DIR, filename)
    if not os.path.exists(path):
        return

    size = LAYOUT["logo_size"]
    logo = Image.open(path).convert("RGBA")
    logo.thumbnail((size, size))

    x = int(LAYOUT["logo_x"] - logo.width / 2)
    y = int(yc - logo.height / 2)
    img.paste(logo, (x, y), logo)


def render():
    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(
            CSV_PATH + " 없음. 먼저 kbo_team_rank_crawler.py 를 실행하세요."
        )

    df = pd.read_csv(CSV_PATH)
    fonts = load_fonts()
    bg = get_background()

    gaps = [parse_gap(v) for v in df["게임차"]] if "게임차" in df.columns else [0] * len(df)
    tiers = assign_tiers(gaps)

    img = draw_tier_backgrounds(bg, tiers)
    img = img.convert("RGBA")

    for i, (_, row) in enumerate(df.iterrows()):
        yc = LAYOUT["table_top"] + i * LAYOUT["row_height"]

        team_name = str(row["팀명"]) if "팀명" in df.columns else ""
        paste_logo(img, team_name, yc)

    d = ImageDraw.Draw(img)
    for i, (_, row) in enumerate(df.iterrows()):
        yc = LAYOUT["table_top"] + i * LAYOUT["row_height"]
        for col, x in LAYOUT["columns"].items():
            if col not in df.columns:
                continue
            val = str(row[col])
            font = fonts["row_bold"] if col in ("순위", "팀명") else fonts["row"]
            d.text((x, yc), val, font=font, fill=LAYOUT["text_color"], anchor="mm")

    stamp = datetime.now().strftime("%Y-%m-%d %H:%M 기준")
    d.text((W - 60, H - 50), stamp, font=fonts["small"], fill=(120, 120, 120), anchor="rm")

    img = img.convert("RGB")
    os.makedirs(DATA_DIR, exist_ok=True)
    img.save(OUT_LATEST)

    stamp_file = datetime.now().strftime("%Y%m%d")
    stamped = os.path.join(DATA_DIR, "kbo_rank_image_" + stamp_file + ".png")
    img.save(stamped)

    print("이미지 저장: " + OUT_LATEST)
    print("백업본: " + stamped)


if __name__ == "__main__":
    render()
