#!/usr/bin/env python3
"""뉴스 시트를 읽어 기간 필터링 · 중복 묶음 · 키워드 매칭을 하고 후보 목록을 만든다.

사용법:
    python3 scripts/prepare.py data/2026-10-26_news.xlsx --date 2026-10-26

결과 (reports/<날짜>/):
    candidates.json  기간 안 기사를 사안별로 묶은 목록 (보도 매체 수, 키워드 매칭 포함)
    candidates.md    사람이 훑어보기 쉬운 요약
    selection.json   TOP 5 초안 (이미 있으면 --force 없이는 덮어쓰지 않음)

selection.json 을 검토·수정한 뒤 scripts/render.py 로 HTML 을 만든다.
"""
import argparse
import csv
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KST = timezone(timedelta(hours=9))
CUTOFF = (6, 30)  # 기준 시각 06:30
WEEKDAYS = "월화수목금토일"


# ---------- 로드 ----------
def load_rows(path: Path):
    if path.suffix.lower() in (".xlsx", ".xlsm"):
        import openpyxl
        ws = openpyxl.load_workbook(path, read_only=True, data_only=True).active
        rows = [list(r) for r in ws.iter_rows(values_only=True)]
    else:
        with open(path, encoding="utf-8-sig", newline="") as f:
            rows = list(csv.reader(f))
    header = [str(h or "").strip() for h in rows[0]]

    def col(*names):
        for n in names:
            if n in header:
                return header.index(n)
        raise SystemExit(f"열을 찾을 수 없습니다: {names} / 실제 열: {header}")

    ci = dict(title=col("제목", "title"), url=col("URL", "url", "링크"),
              date=col("날짜", "date", "발행일시"), pub=col("신문사", "언론사", "매체"))
    out = []
    for r in rows[1:]:
        if not r or not r[ci["title"]]:
            continue
        out.append(dict(title=str(r[ci["title"]]).strip(),
                        url=str(r[ci["url"]] or "").strip(),
                        raw_date=r[ci["date"]],
                        publisher=str(r[ci["pub"]] or "").strip()))
    return out


# ---------- 날짜 ----------
URL_PATTERNS = [
    (re.compile(r"/view/(20\d{2})(\d{2})(\d{2})(\d{2})(\d{2})"), True),     # 아주경제
    (re.compile(r"/article/(20\d{2})(\d{2})(\d{2})(\d{2})(\d{2})"), True),  # 경향신문
    (re.compile(r"/(20\d{2})(\d{2})(\d{2})/\d+"), False),                    # 동아일보 (날짜만)
]


def parse_date(raw, url):
    """(datetime|None, 출처) 반환. 출처: sheet / url / url-dateonly / unknown"""
    if isinstance(raw, datetime):
        return raw.replace(tzinfo=KST), "sheet"
    s = str(raw or "").strip()
    for fmt in ("%Y.%m.%d %H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=KST), "sheet"
        except ValueError:
            pass
    for pat, has_time in URL_PATTERNS:
        m = pat.search(url)
        if m:
            g = list(map(int, m.groups()))
            if has_time:
                return datetime(*g, tzinfo=KST), "url"
            return datetime(*g, tzinfo=KST), "url-dateonly"
    return None, "unknown"


def window_for(date_str):
    end = datetime.strptime(date_str, "%Y-%m-%d").replace(hour=CUTOFF[0], minute=CUTOFF[1], tzinfo=KST)
    return end - timedelta(days=1), end


def in_window(dt, src, start, end):
    if dt is None:
        return True  # 날짜를 알 수 없으면 포함하고 리포트에 표시
    if src == "url-dateonly":
        return start.date() <= dt.date() <= end.date()
    return start <= dt <= end


# ---------- 중복 묶음 ----------
def bigrams(t):
    t = re.sub(r"\[[^\]]*\]", " ", t)              # [단독] 같은 말머리 제거
    t = re.sub(r"[^A-Za-z가-힣\u4e00-\u9fff]", "", t)  # 숫자·기호 제거 (날짜·회차가 엉뚱하게 묶이지 않도록)
    return {t[i:i + 2] for i in range(len(t) - 1)}


def cluster(articles, pair_th=0.4, union_th=0.6):
    """제목 글자 2-gram 겹침으로 같은 사안을 묶는다.
    pair_th: 묶음 안 어느 한 기사와의 겹침 비율 / union_th: 묶음 전체 단어와의 겹침 비율"""
    clusters = []
    for a in articles:
        bg = bigrams(a["title"])
        best, score = None, 0.0
        for c in clusters:
            s1 = max(len(bg & m) / max(1, min(len(bg), len(m))) for m in c["bgs"])
            s2 = len(bg & c["union"]) / max(1, len(bg))
            s = max(s1, s2 if s2 >= union_th else 0)
            if s > score:
                best, score = c, s
        if best is not None and score >= pair_th:
            best["items"].append(a); best["bgs"].append(bg); best["union"] |= bg
        else:
            clusters.append({"items": [a], "bgs": [bg], "union": set(bg)})
    return [c["items"] for c in clusters]


# ---------- 키워드 ----------
def load_config():
    return json.loads((ROOT / "config" / "keywords.json").read_text(encoding="utf-8"))


def keyword_hits(title, cfg):
    hits = []
    for g in cfg["groups"]:
        found = [k for k in g["keywords"] if k.lower() in title.lower()]
        if found:
            hits.append({"group": g["name"], "keywords": found})
    return hits


BREAKING = re.compile(r"\[(속보|종합|단독)\]")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("data", type=Path, help="뉴스 시트 (.xlsx 또는 .csv)")
    ap.add_argument("--date", help="리포트 기준일 YYYY-MM-DD (기본: 오늘, 한국시간)")
    ap.add_argument("--force", action="store_true", help="selection.json 이 있어도 초안으로 덮어쓰기")
    args = ap.parse_args()

    date_str = args.date or datetime.now(KST).strftime("%Y-%m-%d")
    start, end = window_for(date_str)
    cfg = load_config()
    excl = [re.compile(p) for p in cfg.get("exclude_patterns", [])]

    rows = load_rows(args.data)
    kept, dropped = [], []
    for r in rows:
        dt, src = parse_date(r["raw_date"], r["url"])
        r["date"] = dt.strftime("%Y-%m-%d %H:%M") if dt else None
        r["date_source"] = src
        if in_window(dt, src, start, end):
            kept.append(r)
        else:
            dropped.append(r)

    if not any(r["date_source"] != "unknown" for r in kept):
        print(f"⚠ {start:%m-%d %H:%M} ~ {end:%m-%d %H:%M} 기간에 해당하는 기사가 없습니다.", file=sys.stderr)
        dates = sorted(r["date"] for r in rows if r["date"])
        if dates:
            print(f"  시트의 날짜 범위: {dates[0]} ~ {dates[-1]}  →  --date 로 기준일을 지정하세요.", file=sys.stderr)
        sys.exit(1)

    noise_rows = [r for r in kept if any(p.search(r["title"]) for p in excl)]
    kept_clean = [r for r in kept if r not in noise_rows]
    groups = []
    for c in cluster(kept_clean):
        pubs = sorted({a["publisher"] for a in c})
        rep = sorted(c, key=lambda a: (a["date_source"] != "sheet", -len(a["title"])))[0]
        hits = {}
        for a in c:
            for h in keyword_hits(a["title"], cfg):
                hits.setdefault(h["group"], set()).update(h["keywords"])
        groups.append(dict(
            title=rep["title"], url=rep["url"], date=rep["date"], publishers=pubs,
            publisher_count=len(pubs), article_count=len(c),
            breaking=any(BREAKING.search(a["title"]) for a in c),
            keyword_hits=[{"group": g, "keywords": sorted(k)} for g, k in hits.items()],
            articles=[{k: a[k] for k in ("title", "url", "publisher", "date", "date_source")} for a in c],
        ))
    groups.sort(key=lambda g: (-g["publisher_count"], -g["article_count"], not g["breaking"]))

    out_dir = ROOT / "reports" / date_str
    out_dir.mkdir(parents=True, exist_ok=True)
    unknown = sum(1 for r in kept if r["date_source"] == "unknown")
    stats = dict(total=len(rows), in_window=len(kept), dropped=len(dropped), unknown_date=unknown,
                 clusters=len(groups), excluded_noise=len(noise_rows), publishers=sorted({r["publisher"] for r in rows}))
    meta = dict(date=date_str, window={"start": start.strftime("%Y-%m-%d %H:%M"), "end": end.strftime("%Y-%m-%d %H:%M")},
                source_file=str(args.data), stats=stats)
    (out_dir / "candidates.json").write_text(json.dumps(dict(meta, groups=groups), ensure_ascii=False, indent=1), encoding="utf-8")

    # 사람이 읽는 요약
    md = [f"# 후보 목록 {date_str}", "",
          f"- 기간: {meta['window']['start']} ~ {meta['window']['end']} (KST)",
          f"- 원본 {stats['total']}건 → 기간 내 {stats['in_window']}건 (제외 {stats['dropped']}, 날짜 미상 포함 {unknown}) → 사안 {stats['clusters']}개", "",
          "## 다매체 보도 사안 (인기 TOP 5 후보)", ""]
    for g in groups[:25]:
        flag = " 🔴" if g["breaking"] else ""
        md.append(f"- **{g['publisher_count']}개사** {g['title']}{flag}  \n  {', '.join(g['publishers'])} · {g['url']}")
    md += ["", "## 키워드 매칭 사안", ""]
    for g in groups:
        if g["keyword_hits"]:
            tags = "; ".join(f"{h['group']}: {', '.join(h['keywords'])}" for h in g["keyword_hits"])
            md.append(f"- {g['title']}  \n  [{tags}] · {', '.join(g['publishers'])} · {g['url']}")
    (out_dir / "candidates.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    sel_path = out_dir / "selection.json"
    if sel_path.exists() and not args.force:
        print(f"selection.json 이 이미 있어 그대로 둡니다 (--force 로 초안 재생성).")
    else:
        sel_path.write_text(json.dumps(draft_selection(meta, groups, cfg), ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"초안 작성: {sel_path.relative_to(ROOT)}  ← 검토·수정 후 render.py 실행")
    print(f"후보: {(out_dir / 'candidates.md').relative_to(ROOT)}  (사안 {len(groups)}개)")


def draft_selection(meta, groups, cfg):
    """보도 매체 수 기준의 기계적 초안. 분야 안배·요약·시사점은 사람이(또는 Claude가) 다듬는다."""
    d = datetime.strptime(meta["date"], "%Y-%m-%d")
    clean = groups
    top = clean[:5]
    kw = [g for g in clean if g["keyword_hits"]]
    kw.sort(key=lambda g: (min(int(h["group"][1]) for h in g["keyword_hits"]), -g["publisher_count"]))
    found = {h["group"] for g in kw for h in g["keyword_hits"]}
    return {
        "_안내": "초안입니다. category·summary·impact 를 채우고 순서를 조정한 뒤 render.py 를 실행하세요.",
        "date": meta["date"],
        "date_label": f"{d.year}년 {d.month}월 {d.day}일({WEEKDAYS[d.weekday()]})",
        "window": meta["window"],
        "stats": meta["stats"],
        "top5": [{"category": "", "title": g["title"], "url": g["url"], "summary": "", "sources": g["publishers"]} for g in top],
        "top5_also": [g["title"] for g in clean[5:12]],
        "keyword_notice": "" if any(g["name"] in found for g in cfg["groups"][:2]) else
            "디와이그룹사 직접 언급 기사 없음. 디와이사업부 사업군 관련 기사도 이번 기간에는 없었습니다.",
        "keyword_top5": [{"group": g["keyword_hits"][0]["group"], "title": g["title"], "url": g["url"], "impact": "",
                          "sources": g["publishers"]} for g in kw[:5]],
        "keyword_also": [{"title": g["title"], "url": g["url"], "note": g["keyword_hits"][0]["group"]} for g in kw[5:8]],
        "notes": [f"원본: {Path(meta['source_file']).name} ({meta['stats']['total']}건). 같은 사안을 다룬 기사는 대표 1건만 남겼습니다."],
    }


if __name__ == "__main__":
    main()
