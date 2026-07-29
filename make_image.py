"""
KBO 팀 순위 이미지 생성 (하이브리드 방식 + 로고(SVG 지원) + 3단 그룹 색상)
--------------------------------------------------------------
- 배경(assets/background.png)은 피그마에서 만든 1080x1440 템플릿을 사용
- 팀 로고는 assets/logos/*.svg 또는 *.png 에서 팀명에 맞춰 자동으로 붙여넣음
  (SVG는 cairosvg로 변환해서 사용 -> pip install cairosvg 필요)
- 게임차 간격이 가장 크게 벌어지는 2곳을 기준으로 팀을 3그룹(강/중/약)으로
  나누고, 각 그룹마다 다른 색으로 행 배경을 얹음

필요 패키지:
    pip install pillow pandas cairosvg

실행:
    python make_image.py
"""

import io
import os
from datetime import datetime

import pandas as pd
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
FONT_DIR = os.path.join(BASE_DIR, "fonts")
ASSET_DIR = os.path.join(BASE_DIR, "assets")
LOGO_DIR = ASSET_DIR  # 로고 png를 assets/ 바로 아래에 넣는 경우

CSV_PATH = os.path.join(DATA_DIR, "kbo_team_rank_latest.csv")
BG_PATH = os.path.join(ASSET_DIR, "background.png")
OUT_LATEST = os.path.join(DATA_DIR, "kbo_rank_image_latest.png")

W, H = 1080, 1440

# ----------------------------------------------------------------------
# 팀명 -> 로고 파일명 매핑 (svg, png 둘 다 지원)
# ----------------------------------------------------------------------
TEAM_LOGO_FILES = {
    "삼성": "samsung.svg",
    "KT": "kt.svg",
    "LG": "lg.svg",
    "KIA": "kia.svg",
    "두산": "doosan.svg",
    "한화": "hanwha.svg",
    "NC": "nc.svg",
    "롯데": "lotte.svg",
    "SSG": "ssg.svg",
    "키움": "kiwoom.svg",
}

# ----------------------------------------------------------------------
# 좌표 / 스타일 설정 (config)
# 아래 columns 좌표는 실제 배경 이미지의 헤더 라벨 위치를 픽셀 분석해서
# 뽑아낸 정확한 값입니다.
# ----------------------------------------------------------------------
LAYOUT = {
    "table_top": 338,
    "row_height": 103,
    "row_left": 60,
    "row_right": 1020,
    "row_radius": 14,
    "row_v_margin": 7,

    "logo_x": 180,
    "logo_size": 62,

    "columns": {
        "순위": 93,
        "팀명": 260,
        "경기": 346,
        "승": 417,
        "패": 473,
        "무": 529,
        "승률": 599,
        "게임차": 702,
        "최근10경기": 852,
        "연속": 988,
    },

    "font_size": 36,
    "text_color": (40, 36, 34),
    "header_color": (255, 255, 255),

    # 제목 아래 빈 밑줄 위에 날짜를 적을 위치 (실측 좌표) + 제목과 맞춘 스타일
    "date_pos": (372, 172),
    "date_font_size": 46,
    "date_color": (44, 57, 38),      # 메인 제목 글자색과 동일하게 샘플링한 값
    "date_letter_spacing": 0,         # 자연스러운 자간 (인위적 간격 제거, 폰트 크기로 폭 조절)

    # 3그룹(강/중/약) 배경 색 - 채도를 높이고 불투명도를 올려 또렷하게
    "tier_colors": [
        (120, 190, 96, 215),    # 강 - 선명한 초록
        (255, 202, 78, 200),    # 중 - 선명한 골드/머스타드
        (235, 92, 78, 210),     # 약 - 선명한 코랄레드
    ],
}


def load_fonts():
    bold = os.path.join(FONT_DIR, "Pretendard-Bold.otf")
    reg = os.path.join(FONT_DIR, "Pretendard-Regular.otf")
    fs = LAYOUT["font_size"]
    fs_date = LAYOUT["date_font_size"]
    return {
        "row": ImageFont.truetype(reg, fs),
        "row_bold": ImageFont.truetype(bold, fs),
        "title": ImageFont.truetype(bold, 64),
        "small": ImageFont.truetype(reg, 30),
        "date": ImageFont.truetype(bold, fs_date),
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


def load_logo_image(path, size):
    """PNG는 그대로, SVG는 cairosvg로 변환해서 불러온다."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".svg":
        import cairosvg
        # 3배 크기로 렌더링 후 축소 -> 안티에일리어싱 품질 향상
        png_bytes = cairosvg.svg2png(url=path, output_width=size * 3, output_height=size * 3)
        logo = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    else:
        logo = Image.open(path).convert("RGBA")
    logo.thumbnail((size, size), Image.LANCZOS)
    return logo


def paste_logo(img: Image.Image, team_name: str, yc: float):
    filename = TEAM_LOGO_FILES.get(team_name)
    if not filename:
        return
    path = os.path.join(LOGO_DIR, filename)
    if not os.path.exists(path):
        # png 확장자로도 한 번 더 시도 (svg 파일이 아직 없을 때 대비)
        alt = os.path.join(LOGO_DIR, os.path.splitext(filename)[0] + ".png")
        if os.path.exists(alt):
            path = alt
        else:
            return

    size = LAYOUT["logo_size"]
    try:
        logo = load_logo_image(path, size)
    except Exception as e:
        print("로고 로드 실패 (" + team_name + "): " + str(e))
        return

    x = int(LAYOUT["logo_x"] - logo.width / 2)
    y = int(yc - logo.height / 2)
    img.paste(logo, (x, y), logo)


def draw_condensed_text(base_img, text, font, center, fill, scale_x=1.0):
    """폰트 크기(높이)는 그대로 유지하면서 가로 폭만 줄여서 그린다."""
    tmp = Image.new("RGBA", (500, 100), (0, 0, 0, 0))
    td = ImageDraw.Draw(tmp)
    bbox = td.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    td.text((-bbox[0], -bbox[1]), text, font=font, fill=fill)
    cropped = tmp.crop((0, 0, w, h))
    if scale_x != 1.0:
        new_w = max(1, int(w * scale_x))
        cropped = cropped.resize((new_w, h), Image.LANCZOS)
    x = int(center[0] - cropped.width / 2)
    y = int(center[1] - cropped.height / 2)
    base_img.paste(cropped, (x, y), cropped)


def draw_text_with_spacing(draw, text, font, center, spacing, fill):
    """글자 사이 간격(자간)을 주면서 전체를 center 기준 가운데 정렬로 그린다."""
    widths = [draw.textlength(ch, font=font) for ch in text]
    total_width = sum(widths) + spacing * (len(text) - 1)
    x = center[0] - total_width / 2
    y = center[1]
    for ch, w in zip(text, widths):
        draw.text((x + w / 2, y), ch, font=font, fill=fill, anchor="mm")
        x += w + spacing


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

    # 제목 아래 빈 밑줄 위에 오늘 날짜 표시 (예: 07.24) - 자간을 주고 제목 색상에 맞춤
    date_str = datetime.now().strftime("%m.%d")
    draw_text_with_spacing(
        d, date_str, fonts["date"], LAYOUT["date_pos"],
        LAYOUT["date_letter_spacing"], LAYOUT["date_color"],
    )

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
