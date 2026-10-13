#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 3:4 竖版 / 4:3 横版吸睛封面图。
AI 底图(无文字) + 极简大字排版, Playwright 截图输出 PNG。

meta.cover 可配: img_v/img_h(底图), big1/big2(主标题两行), sub(一行副标)。
用法: python3 make_cover.py lessons/01.json
"""
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render as R

ROOT, BUILD, OUT = R.ROOT, R.BUILD, R.OUT

# 吸睛贴纸描边(8 向叠加, 白字深藏青描边)
OUTLINE = ("3px 0 0 C,-3px 0 0 C,0 3px 0 C,0 -3px 0 C,"
           "2px 2px 0 C,-2px 2px 0 C,2px -2px 0 C,-2px -2px 0 C,"
           "5px 5px 0 C,-5px 5px 0 C,5px -5px 0 C,-5px -5px 0 C,"
           "0 18px 40px rgba(10,18,34,.5)").replace("C", "#14213A")
OUTLINE2 = ("2px 0 0 C,-2px 0 0 C,0 2px 0 C,0 -2px 0 C,"
            "3px 3px 0 C,-3px 3px 0 C,3px -3px 0 C,-3px -3px 0 C,"
            "0 12px 30px rgba(10,18,34,.5)").replace("C", "#14213A")

CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'PingFang SC','Hiragino Sans GB','Heiti SC',sans-serif;background:#000}
.cover{position:relative;width:100vw;height:100vh;overflow:hidden;color:#fff}
.bg{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}

/* ---------- 竖版 3:4 ---------- */
.v .scrim-top{position:absolute;top:0;left:0;right:0;height:46%;
  background:linear-gradient(180deg,rgba(14,24,44,.86) 0%,rgba(14,24,44,.5) 34%,
    rgba(14,24,44,0) 100%)}
.v .scrim-bot{position:absolute;bottom:0;left:0;right:0;height:34%;
  background:linear-gradient(0deg,rgba(14,24,44,.92) 0%,rgba(14,24,44,.45) 45%,
    rgba(14,24,44,0) 100%)}
.v .top{position:absolute;top:64px;left:60px;right:60px}
.chip{display:inline-block;background:#F6B93B;color:#14213A;font-weight:900;
  font-size:34px;letter-spacing:3px;padding:12px 30px;border-radius:999px;
  box-shadow:0 10px 26px rgba(10,18,34,.35)}
.v .big{margin-top:34px;font-weight:900;line-height:1.16;letter-spacing:4px}
.v .big .l1{font-size:172px;display:block}
.v .big .l2{font-size:132px;display:block;margin-top:10px}
.num{display:inline-block;background:#F6B93B;color:#14213A;border-radius:22px;
  padding:0 30px;line-height:1.16;letter-spacing:0}
.v .bot{position:absolute;bottom:56px;left:60px;right:60px;display:flex;
  align-items:flex-end;justify-content:space-between}
.sub{font-size:46px;font-weight:800;letter-spacing:3px;text-shadow:0 4px 16px rgba(0,0,0,.5)}
.brand{background:rgba(14,24,44,.82);border:2px solid rgba(255,255,255,.28);
  color:#fff;font-size:30px;font-weight:700;letter-spacing:2px;
  padding:12px 26px;border-radius:16px}

/* ---------- 横版 4:3 ---------- */
.h .bg{object-position:60% 32%;transform:scale(1.1);transform-origin:50% 30%}
.h .glow{position:absolute;inset:0;
  background:radial-gradient(1200px 900px at 20% 45%,rgba(14,24,44,.62),transparent 62%),
  linear-gradient(0deg,rgba(14,24,44,.5) 0%,transparent 22%)}
.h .top{position:absolute;left:84px;top:50%;transform:translateY(-50%);max-width:46%}
.h .chip{font-size:30px;padding:10px 26px}
.h .big{margin-top:30px;font-weight:900;line-height:1.18;letter-spacing:4px}
.h .big .l1{font-size:150px;display:block}
.h .big .l2{font-size:112px;display:block;margin-top:20px;white-space:nowrap}
.h .sub{margin-top:34px;font-size:44px;color:#FFE9A8;display:block;font-weight:800;
  letter-spacing:3px;text-shadow:OUTLINE2}
.h .brand{position:absolute;right:64px;bottom:52px}
"""


def cover_html(lesson, orient):
    meta = lesson["meta"]
    cv = meta.get("cover", {})
    key = "img_v" if orient == "v" else "img_h"
    img = cv.get(key) or next((s.get("image") for s in lesson["slides"]
                               if s.get("image")), "")
    big1 = cv.get("big1") or meta["scene"]
    big2 = cv.get("big2") or "只用这 5 句"
    sub = cv.get("sub") or "海关问答 · 背完直接过"

    # big2 里的数字用黄块强调
    import re
    big2 = re.sub(r"([0-9]+)", r'<span class="num">\1</span>', big2)

    chip = f'DAY {str(meta.get("day", "01")).zfill(2)} · {R.esc(meta["scene"])}'
    brand = f'<span class="brand">{R.esc(meta["series"])}</span>'
    if orient == "v":
        text = (f'<div class="top"><span class="chip">{chip}</span>'
                f'<div class="big"><span class="l1">{R.esc(big1)}</span>'
                f'<span class="l2">{big2}</span></div></div>'
                f'<div class="bot"><span class="sub">{R.esc(sub)}</span>{brand}</div>')
    else:
        text = (f'<div class="top"><span class="chip">{chip}</span>'
                f'<div class="big"><span class="l1">{R.esc(big1)}</span>'
                f'<span class="l2">{big2}</span></div>'
                f'<span class="sub">{R.esc(sub)}</span></div>{brand}')
    inner = (
        f'<img class="bg" src="{R._img_uri(img)}" alt="">'
        f'<div class="scrim-top"></div><div class="scrim-bot"></div>'
        if orient == "v" else
        f'<img class="bg" src="{R._img_uri(img)}" alt=""><div class="glow"></div>')
    body = f'<section class="cover {orient}">{inner}{text}</section>'
    return (f'<!DOCTYPE html><html><head><meta charset="utf-8">'
            f'<style>{CSS}</style></head><body>{body}</body></html>')


def build_covers(lesson_file):
    lesson = json.loads(Path(lesson_file).read_text(encoding="utf-8"))
    meta = lesson["meta"]
    lid = str(meta.get("id", meta.get("lesson", "01"))).zfill(2)
    OUT.mkdir(parents=True, exist_ok=True)
    BUILD.mkdir(parents=True, exist_ok=True)

    specs = [("v", 1080, 1440, "3x4"), ("h", 1440, 1080, "4x3")]
    outs = []
    for orient, w, h, ratio in specs:
        hp = BUILD / f"cover_{ratio}.html"
        hp.write_text(cover_html(lesson, orient), encoding="utf-8")
        png = OUT / f"{lid}_封面_{ratio}.png"
        r = R.run_node("cover.js", hp, png, w, h)
        if "COVER_OK" not in (r.stdout or ""):
            print((r.stderr or "")[-600:])
            raise SystemExit(f"封面 {ratio} 渲染失败")
        outs.append(png)
    return outs


if __name__ == "__main__":
    f = sys.argv[1] if len(sys.argv) > 1 else "lessons/01.json"
    for p in build_covers(f):
        print(f"[OK] {p}")
