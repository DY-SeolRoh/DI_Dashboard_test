#!/usr/bin/env python3
"""selection.json 을 읽어 브리핑 HTML 을 만든다.

사용법:
    python3 scripts/render.py 2026-10-26          # reports/2026-10-26/selection.json → briefing.html
    python3 scripts/render.py path/to/selection.json

결과: reports/<날짜>/briefing.html  (+ reports/index.html 목록 갱신)
"""
import json
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "templates" / "briefing.html"


def e(s):
    return escape(str(s or ""), quote=True)


def link(title, url):
    if not url:
        return e(title)
    return f'<a href="{e(url)}" target="_blank" rel="noopener">{e(title)}</a>'


def top_item(i, it):
    src = " · ".join(it.get("sources", []))
    cnt = f"{len(it.get('sources', []))}개사 보도" if len(it.get("sources", [])) > 1 else src
    tag = f'<span class="tag">{e(it.get("category"))}</span>' if it.get("category") else ""
    return f"""    <li><span class="no">{i}</span>
      <div class="row1">{tag}<span class="cnt">{e(cnt)}</span></div>
      <div class="ttl">{link(it['title'], it.get('url'))}</div>
      <div class="desc">{e(it.get('summary'))}<div class="src">{e(src)}</div></div>
    </li>"""


def kw_item(i, it):
    src = " · ".join(it.get("sources", []))
    impact = f'<span class="imp">{e(it["impact"])}</span>' if it.get("impact") else ""
    return f"""    <li><span class="no">{i}</span>
      <div class="row1"><span class="tag">{e(it.get('group'))}</span><span class="cnt">{e(src)}</span></div>
      <div class="ttl">{link(it['title'], it.get('url'))}</div>
      <div class="desc">{impact}</div>
    </li>"""


def render(sel):
    st = sel.get("stats", {})
    w = sel.get("window", {})
    ws, we = w.get("start", "")[5:].replace("-", "."), w.get("end", "")[5:].replace("-", ".")
    pubs = st.get("publishers", [])
    parts = [f"""<header>
  <div class="eyebrow">디지털혁신팀 · Daily News Briefing</div>
  <h1>일일 뉴스 브리핑 · {e(sel.get('date_label', sel.get('date')))}</h1>
  <div class="meta">
    <span>수집 기간 <b>{e(ws)} ~ {e(we)}</b></span>
    <span>대상 기사 <b>{st.get('in_window', '-')}건</b> / 원본 {st.get('total', '-')}건</span>
    <span>매체 <b>{len(pubs)}개사</b> ({e('·'.join(p[:2] for p in pubs))})</span>
  </div>
</header>"""]

    parts.append('<section>\n  <h2>Ⅰ. 매체별 통합 인기 뉴스 TOP 5 <small>동시 보도량 · 속보성 · 파급력 · 분야 안배 기준</small></h2>\n  <ol class="rank">')
    parts += [top_item(i, it) for i, it in enumerate(sel.get("top5", [])[:5], 1)]
    parts.append("  </ol>")
    also = sel.get("top5_also") or []
    if also:
        parts.append(f'  <p class="also"><b>TOP 5에 못 든 화제 사안</b> · {" · ".join(e(a) for a in also)}</p>')
    parts.append("</section>")

    parts.append('<section>\n  <h2>Ⅱ. 당사 관심 키워드 뉴스 TOP 5</h2>')
    if sel.get("keyword_notice"):
        n = sel["keyword_notice"]
        head, _, rest = n.partition(". ")
        parts.append(f'  <div class="notice"><b>{e(head)}.</b> {e(rest)}</div>' if rest else f'  <div class="notice">{e(n)}</div>')
    items = sel.get("keyword_top5", [])[:5]
    if items:
        parts.append('  <ol class="rank">')
        parts += [kw_item(i, it) for i, it in enumerate(items, 1)]
        parts.append("  </ol>")
    kalso = sel.get("keyword_also") or []
    if kalso:
        bits = [f"{link(a['title'], a.get('url'))}" + (f" ({e(a['note'])})" if a.get("note") else "") for a in kalso]
        parts.append(f'  <p class="also"><b>참고 후보</b> · {" · ".join(bits)}</p>')
    groups = sel.get("keyword_groups")
    if not groups:
        cfg = json.loads((ROOT / "config" / "keywords.json").read_text(encoding="utf-8"))
        groups = {}
        for g in cfg["groups"]:
            n = sum(1 for it in items if it.get("group", "").startswith(g["name"][:3]))
            groups[g["name"]] = f"{n}건 선정" if n else "해당 기사 없음"
    parts.append('  <div class="kw">' + "".join(f"\n    <div><b>{e(k)}</b><span>{e(v)}</span></div>" for k, v in groups.items()) + "\n  </div>")
    parts.append("</section>")

    notes = sel.get("notes") or []
    if notes:
        parts.append("<footer>\n  <div>작성 기준과 참고 사항</div>\n  <ul>" + "".join(f"\n    <li>{e(n)}</li>" for n in notes) + "\n  </ul>\n</footer>")

    title = f"DY 일일 뉴스 브리핑 {sel.get('date', '')[5:].replace('-', '.')}"
    return TEMPLATE.read_text(encoding="utf-8").replace("{{TITLE}}", e(title)).replace("{{BODY}}", "\n\n".join(parts))


def write_index():
    rows = []
    for d in sorted((ROOT / "reports").glob("*/briefing.html"), reverse=True):
        rows.append(f'<li><a href="{d.parent.name}/briefing.html">{d.parent.name}</a></li>')
    html = TEMPLATE.read_text(encoding="utf-8").replace("{{TITLE}}", "DY 뉴스 브리핑 목록").replace(
        "{{BODY}}", '<header><div class="eyebrow">디지털혁신팀 · Daily News Briefing</div><h1>브리핑 목록</h1></header>\n'
                    f'<section><ol class="rank" style="padding:12px 28px;list-style:disc">{"".join(rows)}</ol></section>')
    (ROOT / "reports" / "index.html").write_text(html, encoding="utf-8")


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    arg = Path(sys.argv[1])
    path = arg if arg.suffix == ".json" else ROOT / "reports" / sys.argv[1] / "selection.json"
    sel = json.loads(path.read_text(encoding="utf-8"))
    out = path.parent / "briefing.html"
    out.write_text(render(sel), encoding="utf-8")
    write_index()
    print(f"생성: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
