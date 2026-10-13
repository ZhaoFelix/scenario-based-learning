#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分页自检: 不合成语音, 直接实测每页高度并模拟分页, 打印结果。
用法: python3 layout_check.py lessons/01.json
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render as R


def main(path="lessons/01.json"):
    lesson = json.loads(Path(path).read_text(encoding="utf-8"))
    lesson["slides"] = R.expand_passes(lesson)
    for s in lesson["slides"]:
        for b in s.get("blocks", []):
            b.setdefault("_dur", 1.0)
    for i, s in enumerate(lesson["slides"]):
        s["_name"] = s.get("name", f"slide{i}")

    html = R.build_html(lesson, "measure.html")
    meas = R.measure_pages(html)
    if not meas:
        print("测量失败")
        return
    print(f"{'#':>2} {'页名':<32} {'可用':>5} {'实测':>6} 结论")
    for i, (s, m) in enumerate(zip(lesson["slides"], meas)):
        over = "  ← 超高" if m["h"] > m["avail"] else ""
        print(f"{i:>2} {s['name'][:30]:<32} {m['avail']:>5} {m['h']:>6}{over}")

    pages = R.paginate(lesson, meas)
    print(f"\n分页结果: {len(lesson['slides'])} 页 -> {len(pages)} 页")
    for i, p in enumerate(pages):
        kinds = {}
        for b in p["blocks"]:
            kinds[b.get("type")] = kinds.get(b.get("type"), 0) + 1
        cont = " [续]" if p.get("_cont") else ""
        print(f"  {i:>2} {p['name'][:28]:<30} {len(p['blocks']):>2} 块 "
              f"{kinds}{cont}")

    if "--preview" in sys.argv:
        lesson["slides"] = pages
        final = R.build_html(lesson, "preview.html")
        out = R.BUILD / "preview"
        r = R.run_node("preview.js", final, out)
        print((r.stdout or "").strip()[-40:], f"-> {out}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "lessons/01.json")
