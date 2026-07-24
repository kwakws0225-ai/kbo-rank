# KBO 팀 순위 이미지 자동화

매일 밤 KBO 팀 순위를 크롤링해서 이미지로 만들고, GitHub 저장소에 자동 저장합니다.
서버·유료 API 없이 **전부 무료**(GitHub Actions)로 동작합니다.

## 폴더 구조

```
(저장소 루트)
├── kbo_team_rank_crawler.py     # 1) 순위 크롤링 → data/*.csv
├── make_image.py                # 2) CSV → 이미지 렌더링
├── fonts/
│   ├── Pretendard-Bold.otf      # 한글 폰트 (무료, 상업사용 가능)
│   └── Pretendard-Regular.otf
├── assets/
│   └── background.png           # ★ 여기에 본인 피그마/캔바 템플릿(1080x1440) 넣기
├── data/                        # 결과물이 쌓이는 곳 (자동 생성)
│   ├── kbo_team_rank_latest.csv
│   ├── kbo_rank_image_latest.png   # ← 항상 최신 이미지
│   └── ...
└── .github/workflows/kbo-daily.yml  # 자동 실행 스케줄
```

## 최초 세팅 (한 번만)

1. GitHub에 새 저장소 생성 (public이면 Actions 완전 무료·무제한)
2. 위 파일들을 저장소에 업로드
   - `.yml` 파일은 반드시 `.github/workflows/` 폴더 안에 넣기
3. Settings → Actions → General → **Workflow permissions**을
   "Read and write permissions"으로 변경 (커밋 권한)
4. Actions 탭 → "KBO 순위 이미지 자동 생성" → **Run workflow**로 즉시 테스트

## 내 디자인 템플릿 적용하기

1. 피그마/캔바에서 **1080 x 1440** 캔버스로 배경 디자인
   - 헤더, 로고, 표의 칸 선, 색상 등 "안 바뀌는 부분"만 만들기
   - 숫자/팀명이 들어갈 자리는 비워두기
2. PNG로 내보내서 `assets/background.png`로 저장
3. `make_image.py` 상단의 `LAYOUT` 딕셔너리에서 좌표를 템플릿에 맞게 조정
   - `table_top`: 첫 행 y좌표
   - `row_height`: 행 간격
   - `columns`: 각 항목의 중앙 x좌표
4. 로컬에서 `python make_image.py`로 미리보기 → 좌표 미세조정 반복

## 결과 이미지 공개 URL

커밋되면 아래 형식의 링크로 바로 접근 가능합니다 (공유용):

```
https://raw.githubusercontent.com/(내아이디)/(저장소명)/main/data/kbo_rank_image_latest.png
```

이 URL은 항상 "가장 최근 이미지"를 가리킵니다.

## 왜 수치가 최신인가?
크롤링을 GitHub 서버가 KBO 사이트에 직접 요청하므로 캐시 없이 실시간 데이터를 받습니다.
```
