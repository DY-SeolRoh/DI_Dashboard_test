# 일일 뉴스 브리핑 작업 지침

이 레포는 디지털혁신팀 일일 뉴스 브리핑을 만들고 보관하는 곳이다. 사용자가 "브리핑 만들어줘", "시트 다시 읽어줘" 같은 요청을 하면 아래 절차를 따른다.

## 역할

실행 시각 기준 **어제 06:30 ~ 오늘 06:30 (KST)** 에 발행된 기사를 뉴스 시트에서 골라 브리핑 리포트를 만든다.
- 같은 사안의 중복 기사는 대표 1건만 남긴다.
- 시트의 날짜가 기준 기간과 맞지 않으면(예: 지난달 데이터) 멋대로 바꾸지 말고, 시트의 날짜 범위를 알려준 뒤 그 범위에 맞춰 `--date` 를 정해 진행하고 그 사실을 리포트와 답변에 밝힌다.

### Ⅰ. 매체별 통합 인기 뉴스 TOP 5
조회수·댓글이 없으므로 다음을 종합해 5건을 고른다.
- 여러 매체가 동시에 보도한 사안 (보도 매체 수가 많을수록 화제성↑)
- [속보], [종합], [단독] 등 헤드라인성 기사
- 사회·경제적 파급력과 대중 관심도
- 정치/경제/국제/산업/사회 등 분야가 한쪽으로 쏠리지 않게 안배

### Ⅱ. 당사 관심 키워드 뉴스 TOP 5 (5건 이하)
키워드 목록은 `config/keywords.json` 에 있다 (그룹 1~4).
1. 디와이그룹사 (디와이주식회사, 디와이오토, 디와이사업부(구 디와이이노베이트), 디와이파워, DY AUTO, DY POWER)
2. 디와이사업부 사업군 (콘크리트 펌프카, 세차기, 세차장, 골프카, 크레인, 특장차, 전기 골프카, CPT, 세차타운, 트럭 장착형 크레인, 고소작업차)
3. 자동차 산업군 (자동차부품, 자동차, 모터, 배터리, 전기차, 모빌리티, 로보틱스 액추에이터, 자율주행, 글로벌자동차)
4. 유압실린더 산업군 (건설기계, 건설장비, 굴삭기, 지게차) 및 디와이파워 고객사 (JLG, John Deere, JCB, Volvo, 캐터필러, 두산밥캣)

그룹 1·2 우선. 해당 기사가 없으면 그 사실을 리포트에 명시한다. 각 기사에 "당사 시사점"을 한 줄 붙인다.

## 데이터 위치

- 구글 드라이브 스프레드시트 **`디지털혁신팀클로드`** (file ID `1-zeXOHStIKxu_SulhUDOk5I6Q0FBJVEuzzAHpp2AveQ`)
- 열: `제목, URL, 날짜, 신문사, 필터`
- 받는 법: Google Drive 커넥터 `download_file_content` 에 exportMimeType
  `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` 로 xlsx 를 받아 `data/<기준일>_news.xlsx` 로 저장한다.
  (CSV 로 받으면 엑셀에서 좁은 열이 `#########` 로 들어온 값을 구분하기 어렵다.)

## 절차

```bash
# 1) 후보 만들기: 기간 필터 · 중복 묶음 · 키워드 매칭 → reports/<기준일>/candidates.md, selection.json(초안)
python3 scripts/prepare.py data/2026-10-26_news.xlsx --date 2026-10-26

# 2) reports/<기준일>/candidates.md 를 읽고 selection.json 을 다듬는다
#    (TOP 5 선정·분야 안배, category/summary/impact 작성, 묶이지 않은 중복 정리)

# 3) HTML 생성 → reports/<기준일>/briefing.html, reports/index.html
python3 scripts/render.py 2026-10-26
```

- `prepare.py` 의 자동 묶음은 제목 유사도 기반이라 같은 사안이 두 묶음으로 나뉘기도 한다. 보도 매체 수를 셀 때는 candidates.md 를 보고 직접 합친다.
- `selection.json` 이 이미 있으면 `prepare.py` 는 덮어쓰지 않는다 (`--force` 로 초안 재생성).
- 기존 브리핑을 고칠 때는 `selection.json` 만 수정하고 `render.py` 를 다시 실행한다.
- 요약·시사점은 시트에 본문이 없으면 제목만 근거로 쓰고, 그렇게 했다고 notes 에 남긴다. 제목에 없는 사실을 지어내지 않는다.
- 완성 후 `briefing.html` 을 Artifact 로 게시해 링크를 주고, 작업 브랜치에 커밋·푸시한다.

## 디자인 기준

브리핑 HTML 의 디자인은 `templates/briefing.html` 한 곳에서 정하며, 모든 브리핑과 `reports/index.html` 에 같이 적용된다.
- **페이지 전체 배경은 파란색**으로 한다. 라이트 모드 `#1d5aa6`, 다크 모드 `#0c2a52`(짙은 남색).
- 배경 위에 바로 놓이는 글자(제목·수집 정보·섹션 제목·"TOP 5에 못 든 화제 사안"·하단 참고 사항)는 흰색/연한 파랑(`--on-bg*` 변수)으로 쓴다.
- 기사 목록 카드와 키워드 그룹 칸은 라이트 모드에서 흰색(다크 모드에서 한 톤 밝은 파랑)으로 두어 가독성을 지킨다.
- 색은 `:root` 변수로만 바꾸고, 라이트·다크 두 모드를 함께 수정한다. 디자인을 바꾼 뒤에는 기존 브리핑도 `render.py` 로 다시 만든다.

## selection.json 구조

`reports/2026-10-26/selection.json` 을 예시로 본다. 주요 필드:
`date`, `date_label`, `window`, `stats`, `top5[]{category,title,url,summary,sources[]}`, `top5_also[]`,
`keyword_notice`, `keyword_top5[]{group,title,url,impact,sources[]}`, `keyword_also[]{title,url,note}`,
`keyword_groups{그룹명: 상태}` (생략 시 자동 계산), `notes[]`.
