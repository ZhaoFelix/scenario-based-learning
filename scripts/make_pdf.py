#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把课程视频的内容导出成 A4 资料卡片 PDF(不用 HTML 交付物)。

卡片页:
  1 封面卡      2 场景词汇卡(10 词)   3 场景口语卡(5 句)
  4 短文卡·中英对照(配图)  5 短文卡·三遍听法   6 今日口袋卡

用法: python3 make_pdf.py lessons/01.json
"""
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render as R

ROOT, BUILD, OUT = R.ROOT, R.BUILD, R.OUT

CSS = """
@page{size:A4 portrait;margin:0}
*{margin:0;padding:0;box-sizing:border-box;
  -webkit-print-color-adjust:exact;print-color-adjust:exact}
body{font-family:'PingFang SC','Hiragino Sans GB','Songti SC',sans-serif;
  color:#1E2A3A;background:#FBF7EE}
.page{position:relative;width:210mm;height:296.4mm;overflow:hidden;
  padding:12mm 12mm 16mm;background:#FBF7EE;page-break-after:always;
  background-image:
    repeating-linear-gradient(0deg,rgba(70,100,140,.05) 0 1px,transparent 1px 9mm),
    radial-gradient(120mm 80mm at 92% -6%,rgba(255,214,120,.34),transparent 62%),
    radial-gradient(90mm 70mm at -6% 106%,rgba(150,200,255,.24),transparent 60%)}
.page:last-child{page-break-after:auto}
.ph{margin-bottom:6mm;border-bottom:2px dashed rgba(60,90,130,.22);padding-bottom:3.4mm}
.kicker{font-size:8.6pt;letter-spacing:2.6px;color:#8497AC;font-weight:700}
.ph h1{font-size:23pt;font-weight:800;color:#16233A;letter-spacing:.5px;
  margin-top:2mm;line-height:1.22}
.subh{font-size:10pt;color:#5A6C80;margin-top:2mm;line-height:1.5}
.pf{position:absolute;left:12mm;right:12mm;bottom:6mm;display:flex;
  justify-content:space-between;font-size:7.6pt;color:#9AA9BA;
  border-top:1px dashed rgba(60,90,130,.2);padding-top:2mm;
  font-variant-numeric:tabular-nums}
.hl{background:#FFF0A4;border-radius:2px;padding:0 1.5px;font-weight:800;color:#7A4A00}
.strong{font-weight:800;color:#B4482E}

/* ---------- 1 封面 ---------- */
.cover{display:flex;flex-direction:column}
.cv-top{display:flex;align-items:center;gap:3mm;font-size:9.4pt;font-weight:800;
  letter-spacing:2.4px;color:#E06C4F}
.cv-badge{background:#FFF3D6;border:1px solid #F2C14E;border-radius:20px;
  padding:1mm 4mm;color:#8A6A16;font-size:8.4pt;letter-spacing:1px}
.cv-h1{font-size:33pt;font-weight:900;letter-spacing:1px;color:#16233A;
  margin-top:6mm;line-height:1.18}
.cv-en{font-family:'Chalkboard SE','Bradley Hand','Marker Felt',cursive;
  font-size:17pt;color:#1B5FA8;margin-top:2.5mm}
.cv-goal{margin-top:7mm;background:#FFFDF7;border:1.6px solid #E3DACA;
  border-radius:4mm;padding:5mm 6mm;font-size:11pt;line-height:1.7;color:#33455A;
  box-shadow:0 2mm 5mm rgba(90,80,50,.07)}
.cv-goal .lbl{display:block;font-size:8.6pt;letter-spacing:2px;color:#A89B78;
  font-weight:700;margin-bottom:2mm}
.cv-pic{margin-top:6mm;border-radius:4mm;overflow:hidden;height:96mm;
  border:2px solid #E3DACA;box-shadow:0 3mm 7mm rgba(90,80,50,.10)}
.cv-pic img{width:100%;height:100%;object-fit:cover;object-position:center 34%;display:block}
.cv-toc{margin-top:6mm;display:grid;grid-template-columns:1fr 1fr;gap:3mm 5mm}
.cv-toc div{display:flex;align-items:center;gap:2.6mm;font-size:10pt;color:#33455A;
  background:#FFFDF7;border:1.4px solid #EAE2D2;border-radius:3mm;padding:2.6mm 3.4mm}
.cv-toc b{font-family:'Chalkboard SE',cursive;font-size:13pt;color:#E06C4F}

/* ---------- 2 词汇 ---------- */
.vgrid{display:grid;grid-template-columns:1fr 1fr;gap:3.4mm 5mm}
.vcard{background:#FFFDF7;border:1.6px solid #E3DACA;border-radius:3.4mm;
  padding:3.2mm 4mm 3.4mm;break-inside:avoid}
.vtop{display:flex;align-items:baseline;gap:2.4mm}
.vw{font-family:'Chalkboard SE','Bradley Hand',cursive;font-size:16pt;color:#1B5FA8;
  letter-spacing:.4px}
.vph{font-size:8pt;color:#8A97A8;font-family:ui-monospace,'SF Mono',Menlo,monospace}
.vpos{margin-left:auto;font-size:7.6pt;color:#A89B78;font-style:italic;
  background:#F6F1E4;padding:.4mm 2.4mm;border-radius:8px;white-space:nowrap}
.vcn{font-size:10.4pt;font-weight:700;color:#33455A;margin-top:1.4mm}
.veg{font-size:9pt;color:#6E8090;margin-top:1.2mm;line-height:1.42;
  font-family:'Chalkboard SE','Bradley Hand',cursive}

/* ---------- 3 口语 ---------- */
.plist{display:flex;flex-direction:column;gap:3.4mm}
.pcard{background:#FFFDF7;border:1.6px solid #E3DACA;border-left:1.6mm solid #F2C14E;
  border-radius:3.4mm;padding:3.4mm 4.6mm}
.pen{font-family:'Chalkboard SE','Bradley Hand',cursive;font-size:14pt;color:#16233A;
  line-height:1.34}
.pcn2{font-size:10pt;color:#4A5C70;margin-top:1.4mm}
.ptip{font-size:8.8pt;color:#8A97A8;margin-top:1.6mm;padding-top:1.6mm;
  border-top:1px dashed #E0D8C6;line-height:1.5}

/* ---------- 4/5 短文 ---------- */
.pcard-pic{border-radius:4mm;overflow:hidden;height:58mm;border:2px solid #E3DACA;
  margin-bottom:5mm;box-shadow:0 2.4mm 6mm rgba(90,80,50,.09)}
.pcard-pic.tall{height:112mm;margin-bottom:4mm}
.pcard-pic img{width:100%;height:100%;object-fit:cover;object-position:center 34%;
  display:block}
.pcap{font-size:8.4pt;color:#93A3B6;text-align:right;margin-top:1.6mm}
.dialogue{column-count:2;column-gap:6mm}
.pline{display:flex;gap:2.6mm;margin-bottom:3.2mm;break-inside:avoid}
.who{flex:0 0 15mm;font-size:7.6pt;font-weight:800;letter-spacing:.6px;
  color:#8497AC;padding-top:.7mm}
.who.you{color:#E06C4F}
.ten{font-size:9.6pt;line-height:1.36;color:#1B2A3C;
  font-family:'Chalkboard SE','Bradley Hand',cursive}
.tcn{font-size:8.4pt;color:#8497AC;margin-top:.5mm;line-height:1.4}
.passes{display:flex;gap:3mm}
.pass{flex:1;background:#FFFDF7;border:1.4px solid #EAE2D2;border-radius:3.4mm;
  padding:3.6mm;text-align:center}
.pass .n{font-size:8pt;letter-spacing:1.6px;color:#A89B78;font-weight:800}
.pass .t{font-size:10pt;font-weight:800;color:#1B3A5C;margin-top:1.6mm}
.pass .d{font-size:8.4pt;color:#7A8A9C;margin-top:1.2mm;line-height:1.45}
.pass.on{background:#FFF6DF;border-color:#F2C14E}
.blindbadge{margin-top:5mm;display:flex;align-items:center;gap:4mm;
  background:#FFFDF7;border:2px dashed #C9D8E8;border-radius:4mm;padding:5mm 6mm}
.blindbadge .ic{font-size:26pt;line-height:1}
.blindbadge .t{font-size:14pt;font-weight:900;color:#1B3A5C}
.blindbadge .d{font-size:9.4pt;color:#7A8A9C;margin-top:1.4mm;line-height:1.5}

/* ---------- 6 口袋卡 ---------- */
.kvlist{display:flex;flex-direction:column;gap:3mm}
.kv2{display:flex;align-items:flex-start;gap:3.4mm;background:#FFFDF7;
  border:1.5px solid #E3DACA;border-radius:3.4mm;padding:3.4mm 4.4mm;break-inside:avoid}
.kv2 .n{flex:0 0 7mm;height:7mm;border-radius:50%;background:#F2C14E;color:#5A4410;
  font-size:9pt;font-weight:900;display:flex;align-items:center;justify-content:center}
.kv2 .q{font-size:10.6pt;color:#16233A;font-family:'Chalkboard SE','Bradley Hand',cursive;
  line-height:1.34}
.kv2 .a{font-size:11pt;font-weight:800;color:#1B5FA8;margin-top:1.2mm;
  font-family:'Chalkboard SE','Bradley Hand',cursive}
.tipbox{margin-top:5mm;background:#FFF6DF;border:1.6px solid #F2C14E;border-radius:4mm;
  padding:4.4mm 5mm;font-size:10pt;line-height:1.65;color:#5A4410;display:flex;gap:3.4mm}
.tipbox .ic{font-size:15pt;line-height:1.2}
.tipbox.small{font-size:9.4pt;margin-top:4mm}
"""


def page(inner, i, total, meta, cls=""):
    foot = (f'<footer class="pf"><span>{R.esc(meta["series"])} · 第 '
            f'{R.esc(meta["lesson"])} 课 · {R.esc(meta["scene"])}</span>'
            f'<span>{i} / {total} · 资料卡片</span></footer>')
    return f'<section class="page {cls}">{inner}{foot}</section>'


def head(kicker, title, sub=""):
    s = (f'<div class="kicker">{R.esc(kicker)}</div>'
         f'<h1>{R.inline(title)}</h1>')
    if sub:
        s += f'<div class="subh">{R.inline(sub)}</div>'
    return f'<header class="ph">{s}</header>'


def blocks_of(slides, layout_name, btype=None):
    for sl in slides:
        if sl.get("name", "").startswith(layout_name):
            bs = sl.get("blocks", [])
            return [b for b in bs if b.get("type") == btype] if btype else bs
    return []


def card_html(lesson):
    slides = lesson["slides"]
    meta = lesson["meta"]
    out = []

    # ---------------- 1 封面 ----------------
    cover = next((s for s in slides if s.get("layout") == "cover"), slides[0])
    cb = {b["type"]: b for b in cover.get("blocks", []) if b.get("type") in
          ("sub", "h", "en", "zh")}
    img = next((s.get("image") for s in slides if s.get("image")), "")
    pic = (f'<div class="cv-pic"><img src="{R._img_uri(img)}" alt=""></div>'
           if img else "")
    toc = [("01", "场景词汇 · 10 个词"), ("02", "场景口语 · 5 句必答"),
           ("03", "场景短文 · 三遍听法"), ("04", "今日口袋卡 · 5 组问答")]
    toc_html = "".join(f'<div><b>{n}</b><span>{t}</span></div>' for n, t in toc)
    out.append((
        f'<div class="cover">'
        f'<div class="cv-top">美国生活英语 · 每天 10 分钟'
        f'<span class="cv-badge">DAY {R.esc(str(meta.get("day","01"))).zfill(2)}</span></div>'
        f'<div class="cv-h1">{R.esc(cb["h"]["text"])}</div>'
        f'<div class="cv-en">{R.inline(cb.get("en", {}).get("text", ""))}</div>'
        f'<div class="cv-goal"><span class="lbl">学完能做什么</span>'
        f'{R.inline(cb.get("zh", {}).get("text", "").split("：")[-1])}</div>'
        f'{pic}<div class="cv-toc">{toc_html}</div></div>'))

    # ---------------- 2 词汇卡 ----------------
    vocab = blocks_of(slides, "一、场景词汇", "vocab")
    vtip = blocks_of(slides, "一、场景词汇", "tip")
    vh = "".join(
        f'<div class="vcard"><div class="vtop"><span class="vw">{R.esc(b["w"])}</span>'
        f'<span class="vph">{R.esc(b.get("ph",""))}</span>'
        f'<span class="vpos">{R.esc(b.get("pos",""))}</span></div>'
        f'<div class="vcn">{R.inline(b.get("cn",""))}</div>'
        f'<div class="veg">{R.inline(b.get("eg",""))}</div></div>' for b in vocab)
    tip = (f'<div class="tipbox small"><span class="ic">{vtip[0].get("ic","🎯")}</span>'
           f'<span>{R.inline(vtip[0]["text"])}</span></div>' if vtip else "")
    out.append(head("PART 1 · 场景词汇 · SCENE WORDS", "先认这 10 个词",
                    "**蓝字是必须能说出口的**，其余听懂就够。") +
               f'<div class="vgrid">{vh}</div>' + tip)

    # ---------------- 3 口语卡 ----------------
    phrase = blocks_of(slides, "二、场景口语", "phrase")
    ph = "".join(
        f'<div class="pcard"><div class="pen">{R.inline(b["en"])}</div>'
        f'<div class="pcn2">{R.inline(b.get("cn",""))}</div>'
        f'<div class="ptip">💡 {R.inline(b.get("tip",""))}</div></div>' for b in phrase)
    out.append(head("PART 2 · 场景口语 · SCENE PHRASES", "五句话走完全程",
                    "海关只会问这五个问题，背熟就能一次过。") +
               f'<div class="plist">{ph}</div>')

    # ---------------- 4 短文卡 · 中英对照 ----------------
    pass_sl = next((s for s in slides if s.get("passes")), None)
    lines = [b for b in (pass_sl or {}).get("blocks", []) if b.get("type") == "line"]
    cap = (pass_sl or {}).get("image_caption", "")

    def line_html(b, cn=True):
        who = b.get("who", "")
        wcls = "who you" if who.upper() == "YOU" else "who"
        c = f'<div class="tcn">{R.inline(b.get("cn",""))}</div>' if cn else ""
        return (f'<div class="pline"><span class="{wcls}">{R.esc(who)}</span>'
                f'<div><div class="ten">{R.inline(b["text"])}</div>{c}</div></div>')

    dimg = (f'<div class="pcard-pic"><img src="{R._img_uri(pass_sl.get("image",""))}" alt=""></div>'
            f'<div class="pcap">{R.esc(cap)}</div>' if pass_sl and pass_sl.get("image") else "")
    out.append(head("PART 3 · 场景短文 · 中英对照", "入境大厅 · 一段完整的对话",
                    f"共 {len(lines)} 句，{sum(len(b.get('say','').split()) for b in lines)} 词 · "
                    "黄底的词都是今天学的") +
               dimg + f'<div class="dialogue">{"".join(line_html(b) for b in lines)}</div>')

    # ---------------- 5 短文卡 · 三遍听法 ----------------
    word_n = sum(len(b.get("say", "").split()) for b in lines)
    passes = "".join(
        f'<div class="pass{" on" if k == "blind" else ""}">'
        f'<div class="n">第 {i+1} 遍</div><div class="t">{t}</div>'
        f'<div class="d">{d}</div></div>'
        for i, (k, t, d) in enumerate([
            ("en", "纯英文", "只听英文，先不看中文，逐句跟读"),
            ("bi", "双语对照", "英文 + 中文一起看，确认每句都听懂"),
            ("blind", "盲听", "遮住文字，只看图，整段一遍听懂"),
        ]))
    out.append(head("PART 3 · 场景短文 · 三遍听法", "短文听三遍才算过",
                    f"全文 {word_n} 词，三遍听完约 2 分钟。") +
               (f'<div class="pcard-pic tall"><img src="{R._img_uri(pass_sl.get("image",""))}" alt=""></div>'
                if pass_sl and pass_sl.get("image") else "") +
               f'<div class="passes">{passes}</div>'
               f'<div class="blindbadge"><span class="ic">🙈</span><div>'
               f'<div class="t">盲听 · 只听不看字</div>'
               f'<div class="d">闭上眼或把卡片翻过去，听到 <b>customs / purpose / declare</b> '
               f'这三个词时心里跟一遍。听不懂的地方不用停，先整段跑完再说。</div>'
               f'</div></div>')

    # ---------------- 6 今日口袋卡 ----------------
    rev = next((s for s in slides if s.get("name", "").startswith("今日回顾")), None)
    kvs = [b for b in (rev or {}).get("blocks", []) if b.get("type") == "kv"]
    rtips = [b for b in (rev or {}).get("blocks", []) if b.get("type") == "tip"]
    kh = ""
    for i, b in enumerate(kvs, 1):
        q, a = (b["text"].split("→", 1) + [""])[:2]
        kh += (f'<div class="kv2"><div class="n">{i}</div><div>'
               f'<div class="q">{R.inline(q.strip())}</div>'
               f'<div class="a">{R.inline(a.strip())}</div></div></div>')
    rtip = (f'<div class="tipbox"><span class="ic">{rtips[0].get("ic","🔁")}</span>'
            f'<span>{R.inline(rtips[0]["text"])}</span></div>' if rtips else "")
    out.append(head("TODAY · 今日口袋卡", "记住这 5 组问答就够",
                    "海关问答 = 问什么答什么，越短越好。") +
               f'<div class="kvlist">{kh}</div>' + rtip)

    total = len(out)
    body = "".join(page(h, i + 1, total, meta) for i, h in enumerate(out))
    html = (f'<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">'
            f'<title>{R.esc(meta["scene"])} · 资料卡片</title>'
            f'<style>{CSS}</style></head><body>{body}</body></html>')
    BUILD.mkdir(parents=True, exist_ok=True)
    p = BUILD / "cards.html"
    p.write_text(html, encoding="utf-8")
    return p, total


def build_pdf(lesson_file):
    lesson = json.loads(Path(lesson_file).read_text(encoding="utf-8"))
    meta = lesson["meta"]
    html_path, total = card_html(lesson)
    OUT.mkdir(parents=True, exist_ok=True)
    pdf_path = OUT / f'{meta["lesson"]}_{meta["scene"]}_资料卡片.pdf'

    r = R.run_node("pdf.js", html_path, pdf_path)
    print((r.stdout or "").strip() or (r.stderr or "")[-600:], flush=True)
    return pdf_path, total


if __name__ == "__main__":
    f = sys.argv[1] if len(sys.argv) > 1 else "lessons/01.json"
    p, n = build_pdf(f)
    print(f"[OK] {n} 页卡片 -> {p}")
