# DI_Dashboard_test

디지털혁신팀 일일 뉴스 브리핑 생성기.

| 경로 | 내용 |
|---|---|
| `data/` | 원본 뉴스 시트 (`<기준일>_news.xlsx`) |
| `config/keywords.json` | 당사 관심 키워드 그룹 · 제외 패턴 |
| `scripts/prepare.py` | 기간 필터(어제 06:30~오늘 06:30) · 중복 묶음 · 키워드 매칭 → 후보와 선정 초안 |
| `scripts/render.py` | `selection.json` → `briefing.html` |
| `templates/briefing.html` | 리포트 디자인 (CSS) |
| `reports/<기준일>/` | `candidates.md`, `selection.json`, `briefing.html` |
| `reports/index.html` | 브리핑 목록 |

## 사용법

```bash
python3 scripts/prepare.py data/2026-10-26_news.xlsx --date 2026-10-26
# reports/2026-10-26/selection.json 검토·수정
python3 scripts/render.py 2026-10-26
```

필요 패키지: Python 3, `openpyxl` (xlsx 읽기용; CSV 는 추가 패키지 없이 가능).

Claude Code 에서는 "디지털혁신팀클로드 시트로 브리핑 만들어줘" 라고 요청하면 `CLAUDE.md` 의 절차대로 진행한다.
