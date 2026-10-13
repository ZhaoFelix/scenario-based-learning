#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
学习页生成器: 把 lesson JSON 转成可交互的 HTML 学习页
  ① 场景词汇  ② 场景口语  ③ 场景短文(配图)  ④ 实战  ⑤ 易错点·文化·复习
用法: python3 make_page.py lessons/01.json   (在课程项目目录下执行)
"""
import base64
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(os.environ.get("SBL_ROOT") or Path.cwd()).resolve()
OUT = ROOT / "out"

CSS = """
*{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#F7F8FA; --card:#FFFFFF; --ink:#1B2430; --sub:#6B7A8C;
  --line:#E6EAF0; --blue:#2563EB; --blue-l:#EFF4FF; --green:#0E9F6E;
  --green-l:#E8F8F1; --red:#DC2626; --red-l:#FEF2F2; --amber:#D97706;
  --amber-l:#FEF6E7; --radius:16px;
  --shadow:0 1px 3px rgba(16,32,56,.06),0 8px 24px rgba(16,32,56,.05);
}
body{font-family:'PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif;
  background:var(--bg);color:var(--ink);line-height:1.6;
  -webkit-font-smoothing:antialiased}
.wrap{max-width:1080px;margin:0 auto;padding:0 24px 80px}

/* header */
.hero{background:linear-gradient(135deg,#2563EB 0%,#4F46E5 55%,#7C3AED 100%);
  color:#fff;padding:44px 0 96px;margin-bottom:-64px}
.hero .inner{max-width:1080px;margin:0 auto;padding:0 24px}
.kicker{font-size:13px;letter-spacing:3px;opacity:.85;font-weight:700}
.hero h1{font-size:34px;font-weight:800;margin:10px 0 6px;letter-spacing:.5px}
.hero p{margin:0;opacity:.92;font-size:15px}
.hero .meta{display:flex;gap:10px;flex-wrap:wrap;margin-top:18px}
.pill{background:rgba(255,255,255,.18);border:1px solid rgba(255,255,255,.28);
  padding:6px 14px;border-radius:99px;font-size:13px;font-weight:600}

/* tabs */
.tabs{display:flex;gap:6px;background:#fff;border-radius:14px;padding:6px;
  box-shadow:var(--shadow);margin-bottom:26px;position:sticky;top:12px;z-index:30}
.tabs button{flex:1;border:0;background:transparent;padding:12px 6px;border-radius:10px;
  font-size:14px;font-weight:700;color:var(--sub);cursor:pointer;font-family:inherit;
  transition:.18s;white-space:nowrap}
.tabs button:hover{background:#F1F5F9;color:var(--ink)}
.tabs button.on{background:var(--blue);color:#fff;box-shadow:0 2px 8px rgba(37,99,235,.3)}

.panel{display:none;animation:fade .3s ease}
.panel.on{display:block}
@keyframes fade{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}

.card{background:var(--card);border-radius:var(--radius);padding:22px 24px;
  box-shadow:var(--shadow);margin-bottom:16px;border:1px solid var(--line)}
.card h2{font-size:19px;font-weight:800;margin-bottom:4px;display:flex;
  align-items:center;gap:9px}
.card .desc{font-size:13.5px;color:var(--sub);margin-bottom:16px}
.sect-no{width:26px;height:26px;border-radius:8px;background:var(--blue);color:#fff;
  font-size:14px;display:flex;align-items:center;justify-content:center;flex:0 0 auto}

/* 场景词汇 */
.vgrid{display:grid;grid-template-columns:1fr 1fr;gap:11px}
@media(max-width:720px){.vgrid{grid-template-columns:1fr}}
.vcard{border:1px solid var(--line);border-radius:13px;padding:14px 16px;background:#fff;
  transition:.2s;cursor:pointer}
.vcard:hover{border-color:var(--blue);box-shadow:0 4px 14px rgba(37,99,235,.1)}
.vcard .vw{font-family:'Chalkboard SE','Segoe UI',cursive;font-size:22px;color:var(--blue)}
.vcard .vph{font-size:12px;color:var(--sub);margin-left:8px;
  font-family:ui-monospace,Menlo,monospace}
.vcard .vpos{float:right;font-size:11px;color:#A89B78;font-style:italic;
  background:var(--amber-l);padding:2px 8px;border-radius:20px}
.vcard .vcn{font-size:14.5px;font-weight:700;margin-top:4px}
.vcard .veg{font-size:13px;color:var(--sub);margin-top:3px;
  font-family:'Chalkboard SE','Segoe UI',cursive}

/* 场景口语 */
.sent{border:1px solid var(--line);border-radius:13px;padding:16px 18px;margin-bottom:11px;
  background:#fff;transition:.2s;cursor:pointer}
.sent:hover{border-color:var(--blue);box-shadow:0 4px 14px rgba(37,99,235,.1)}
.sent .en{font-family:'Chalkboard SE','Segoe UI',cursive;font-size:22px;
  color:var(--ink);line-height:1.4}
.sent .en mark{background:#FEF3C7;border-radius:3px;padding:0 3px;color:#92400E;font-weight:600}
.sent .zh{font-size:14px;color:var(--sub);margin-top:5px}
.sent .tip2{font-size:13px;color:#92400E;margin-top:7px;padding-top:8px;
  border-top:1px dashed var(--line)}
.sent .tip2::before{content:'💡 '}
.tag{font-size:11.5px;font-weight:700;padding:3px 9px;border-radius:6px;
  background:var(--blue-l);color:var(--blue)}

/* 场景短文 */
.passage{display:grid;grid-template-columns:1fr 300px;gap:18px;align-items:start}
@media(max-width:860px){.passage{grid-template-columns:1fr}}
.passage .pic img{width:100%;border-radius:14px;border:1px solid var(--line);display:block}
.passage .pic .cap{font-size:12.5px;color:var(--sub);margin-top:8px;text-align:center}
.pline{border-left:3px solid var(--line);padding:9px 14px;margin-bottom:8px;
  border-radius:0 10px 10px 0;cursor:pointer;transition:.2s}
.pline:hover{background:var(--blue-l);border-color:var(--blue)}
.pline .who{font-size:11px;font-weight:800;color:var(--sub);letter-spacing:1px}
.pline .who.you{color:var(--green)}
.pline .ten{font-family:'Chalkboard SE','Segoe UI',cursive;font-size:19px;line-height:1.45}
.pline .ten mark{background:#FEF3C7;border-radius:3px;padding:0 3px;color:#92400E;font-weight:600}
.pline .tcn{font-size:13px;color:var(--sub);margin-top:3px}

/* 短文三遍听法: 纯英文 / 双语 / 盲听 */
.lmode{display:flex;gap:8px;margin-bottom:14px;flex-wrap:wrap;align-items:center}
.lmode button{border:1.5px solid var(--line);background:#fff;border-radius:11px;
  padding:8px 16px;font-size:13.5px;font-weight:700;color:var(--sub);cursor:pointer;
  font-family:inherit;transition:.18s}
.lmode button:hover{border-color:var(--blue);color:var(--blue)}
.lmode button.on{background:var(--blue);border-color:var(--blue);color:#fff}
.lmode .hint{font-size:12.5px;color:var(--sub)}
.passage.mode-en .pline .tcn{display:none}
.passage.mode-blind{grid-template-columns:1fr}
.passage.mode-blind .plist{display:none}

/* 实战 */
.role{display:flex;gap:14px;margin-bottom:18px;align-items:flex-start}
.avatar{width:42px;height:42px;border-radius:50%;flex:0 0 auto;display:flex;
  align-items:center;justify-content:center;font-size:21px;background:var(--blue-l)}
.avatar.u{background:var(--green-l)}
.bubble{background:#F1F5F9;border-radius:14px;padding:13px 17px;flex:1}
.bubble .en{font-family:'Chalkboard SE','Segoe UI',cursive;font-size:18px}
.bubble .zh{font-size:13px;color:var(--sub);margin-top:3px}
.step-dots{display:flex;gap:6px;margin-bottom:20px;flex-wrap:wrap}
.dot{width:9px;height:9px;border-radius:50%;background:#CBD5E1;transition:.25s}
.dot.on{background:var(--blue);transform:scale(1.25)}
.dot.ok{background:var(--green)}
.chips{display:flex;flex-wrap:wrap;gap:9px;margin-top:14px}
.chip{border:1.5px solid var(--line);background:#fff;border-radius:11px;padding:9px 15px;
  font-size:14px;cursor:pointer;font-family:inherit;transition:.18s;color:var(--ink)}
.chip:hover{border-color:var(--blue);background:var(--blue-l)}
.chip.right{border-color:var(--green);background:var(--green-l);color:var(--green);font-weight:700}
.chip.wrong{border-color:var(--red);background:var(--red-l);color:var(--red)}
.fb{margin-top:14px;padding:14px 16px;border-radius:12px;font-size:14px;display:none;
  line-height:1.7}
.fb.show{display:block;animation:fade .3s}
.fb.ok{background:var(--green-l);color:#065F46;border:1px solid #A7F3D0}
.fb.no{background:var(--red-l);color:#991B1B;border:1px solid #FECACA}
.fb b{font-weight:800}

/* 易错点 / 文化 / 打卡 */
.err{border:1px solid var(--line);border-radius:12px;padding:14px 16px;margin-bottom:10px;
  background:#fff}
.err .fix{font-size:15px;margin-top:2px;font-family:'Chalkboard SE','Segoe UI',cursive}
.err .fix .b{color:var(--red);text-decoration:line-through;opacity:.7}
.err .fix .g{color:var(--green);font-weight:700}
.err .why{font-size:12.5px;color:var(--sub);margin-top:5px}
.cult{display:flex;gap:12px;align-items:flex-start;border:1px solid var(--line);
  border-radius:12px;padding:13px 16px;margin-bottom:10px;background:#fff}
.cult .ic{font-size:22px;flex:0 0 auto}
.cult .tx{font-size:14px;line-height:1.65}
.streak{display:flex;gap:8px;margin:18px 0 6px;flex-wrap:wrap}
.day{flex:1;min-width:52px;text-align:center;padding:11px 4px;border-radius:11px;
  background:#F1F5F9;border:1px solid var(--line)}
.day.done{background:var(--green-l);border-color:#A7F3D0;color:var(--green)}
.day.today{outline:2.5px solid var(--blue);outline-offset:1px}
.day .n{font-size:10.5px;color:var(--sub);font-weight:700}
.day .d{font-size:17px;margin-top:3px}
.day .c{font-size:10.5px;color:var(--sub);margin-top:2px}
.day.done .c{color:var(--green);font-weight:700}
.btn{border:0;border-radius:11px;padding:11px 24px;font-size:14.5px;font-weight:700;
  cursor:pointer;font-family:inherit;transition:.18s}
.btn-p{background:var(--blue);color:#fff}
.btn-p:hover{background:#1D4ED8}
.btn-s{background:#EEF2F7;color:var(--ink)}
.btn-s:hover{background:#E2E8F0}
.ctrl{display:flex;gap:10px;justify-content:center;margin-top:20px;align-items:center;
  flex-wrap:wrap}
@media print{body{background:#fff}.tabs,.hero,.ctrl{display:none}
  .panel{display:block !important}}
"""

JS = r"""
const S = window.__DATA__;
let voices = [];
function loadVoices(){ voices = window.speechSynthesis.getVoices(); }
loadVoices(); window.speechSynthesis.onvoiceschanged = loadVoices;

function pickVoice(lang){
  if(!voices.length) loadVoices();
  const want = lang.startsWith('en') ? ['Samantha','Alex','Aria','Jenny','Google US English']
                                      : ['Tingting','Ting-Ting','Sinji','Meijia','Google 普通话'];
  for(const w of want){ const v = voices.find(v=>v.name.includes(w)); if(v) return v; }
  return voices.find(v=>v.lang.startsWith(lang.slice(0,2))) || null;
}
function speak(text, lang, rate, onEnd){
  if(!text) return;
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  const v = pickVoice(lang);
  if(v) u.voice = v;
  u.lang = lang.startsWith('en')?'en-US':'zh-CN';
  u.rate = rate || 1;
  if(onEnd) u.onend = onEnd;
  window.speechSynthesis.speak(u);
}
function strip(s){ return (s||'').replace(/==/g,'').replace(/\*\*/g,''); }

// 实战
let step = 0;
function renderRole(){
  const box = document.getElementById('roleBox');
  if(!box) return;
  const sc = S.role && S.role[step];
  if(!sc){ box.innerHTML = '<div class="bubble" style="text-align:center;background:var(--green-l);color:var(--green);font-weight:800">🎉 通关完成！</div>'; document.getElementById('chips').innerHTML=''; return; }
  let h = `<div class="role"><div class="avatar">👮</div><div class="bubble">
    <div class="en">${sc.q_en}</div><div class="zh">${sc.q_zh||''}</div></div></div>`;
  if(sc.tip) h += `<div class="role"><div class="avatar">💡</div><div class="bubble" style="background:var(--amber-l)"><div class="zh" style="color:#92400E;font-size:14px">${sc.tip}</div></div></div>`;
  box.innerHTML = h;
  const dots = document.querySelector('.step-dots');
  dots.innerHTML = S.role.map((_,i)=>`<div class="dot ${i<step?'ok':(i===step?'on':'')}"></div>`).join('');
  const chips = document.getElementById('chips');
  chips.innerHTML = '';
  sc.opts.forEach((o,i)=>{
    const b = document.createElement('button');
    b.className = 'chip'; b.textContent = o;
    b.onclick = ()=> pick(i);
    chips.appendChild(b);
  });
  const fb = document.getElementById('fb');
  fb.className = 'fb'; fb.innerHTML = '';
}
function pick(i){
  const sc = S.role[step];
  const chips = document.querySelectorAll('#chips .chip');
  const fb = document.getElementById('fb');
  const ok = i === sc.ans;
  chips.forEach((c,k)=>{ if(k===i) c.className = 'chip '+(ok?'right':'wrong'); });
  fb.className = 'fb show '+(ok?'ok':'no');
  fb.innerHTML = ok
    ? `✅ <b>完全正确！</b> ${sc.good||''}<br><span style="opacity:.75">${sc.why||''}</span>`
    : `❌ 再想想～ 正确答案是：<b>${sc.opts[sc.ans]}</b><br>${sc.why||''}`;
  speak(strip(sc.opts[sc.ans]),'en',0.85);
  setTimeout(()=>{
    step++;
    document.querySelectorAll('#chips .chip').forEach(c=>c.className='chip');
    renderRole();
  }, 2600);
}

// 打卡
function markDone(){
  localStorage.setItem('lesson'+S.meta.lesson, '1');
  const el = document.getElementById('todayCell');
  el.classList.add('done');
  el.querySelector('.c').textContent='✓';
  el.querySelector('.d').textContent='🎉';
}
if(localStorage.getItem('lesson'+S.meta.lesson)){
  const el=document.getElementById('todayCell');
  if(el){ el.classList.add('done'); el.querySelector('.c').textContent='✓'; }
}
renderRole();

// tabs
document.querySelectorAll('.tabs button').forEach(b=>{
  b.onclick = ()=>{
    document.querySelectorAll('.tabs button').forEach(x=>x.classList.remove('on'));
    document.querySelectorAll('.panel').forEach(x=>x.classList.remove('on'));
    b.classList.add('on');
    document.getElementById(b.dataset.p).classList.add('on');
  };
});
// 短文三遍听法: 纯英文 / 双语 / 盲听
const LM = {en:'只听英文，先别看中文', bi:'英文 + 中文，对照着听',
            blind:'盲听：只看图，把整段听完再回看文字'};
function setLMode(m){
  document.querySelectorAll('#lmode button').forEach(b=>b.classList.toggle('on', b.dataset.m===m));
  const box = document.getElementById('passageBox');
  if(box) box.className = 'passage mode-' + m;
  const h = document.getElementById('lmHint');
  if(h) h.textContent = LM[m];
}
document.querySelectorAll('#lmode button').forEach(b=>{ b.onclick = ()=> setLMode(b.dataset.m); });

// 顺序播放
function seq(items, gap){
  let i = 0;
  (function next(){
    if(i >= items.length) return;
    const it = items[i++];
    if(typeof it === 'string') return speak(it,'en',0.85,()=>setTimeout(next,gap));
    speak(it.t, it.l||'en', it.r||0.85, ()=>setTimeout(next,gap));
  })();
}
const av = document.getElementById('playAllV');
if(av) av.onclick = ()=> seq(S.vocab.map(v=>({t:v.w,r:0.75})), 500);
const as = document.getElementById('playAllS');
if(as) as.onclick = ()=> seq(S.sents.map(s=>strip(s.en)), 600);
const ap = document.getElementById('playAllP');
if(ap) ap.onclick = ()=> seq(S.passage.map(p=>strip(p.en)), 400);
"""


def build(page_data, out_name):
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / out_name
    p.write_text(page_data, encoding="utf-8")
    return p


def _img_uri(rel):
    p = ROOT / rel
    if not p.exists():
        return ""
    mime = "jpeg" if p.suffix.lower() in (".jpg", ".jpeg") else "png"
    b64 = base64.b64encode(p.read_bytes()).decode("ascii")
    return f"data:image/{mime};base64,{b64}"


def make(lesson_path):
    L = json.loads(Path(lesson_path).read_text(encoding="utf-8"))
    meta = L["meta"]
    lid = meta["id"]
    name = f"{lid}_{meta['scene']}_学习页.html"

    # ---- 从课程 JSON 抽取四部分内容 ----
    vocab, sents, passage, errs, cults = [], [], [], [], []
    passage_img = passage_cap = ""
    for sl in L["slides"]:
        if sl.get("image"):
            passage_img = sl["image"]
            passage_cap = sl.get("image_caption", "")
        for b in sl["blocks"]:
            t = b.get("type")
            if t == "vocab":
                vocab.append({"w": b["w"], "ph": b.get("ph", ""),
                              "pos": b.get("pos", ""), "cn": b.get("cn", ""),
                              "eg": b.get("eg", "")})
            elif t == "phrase":
                sents.append({"en": b["en"], "zh": b.get("cn", ""),
                              "tip": b.get("tip", "")})
            elif t == "line":
                passage.append({"who": b.get("who", ""), "en": b["text"],
                                "zh": b.get("cn", "")})
            elif t == "err":
                errs.append({"bad": b["bad"], "good": b["good"],
                             "why": b.get("why", "")})
            if "文化" in sl.get("name", "") and t == "tip":
                cults.append({"ic": b.get("ic", "💡"), "tx": b["text"]})

    # 易错点 / 文化提示已从课件里移出(只留在学习页), 从独立 JSON 读取
    if not errs:
        f = ROOT / "lessons" / f"{lid}_errors.json"
        if f.exists():
            errs = json.loads(f.read_text(encoding="utf-8"))
    if not cults:
        f = ROOT / "lessons" / f"{lid}_culture.json"
        if f.exists():
            cults = json.loads(f.read_text(encoding="utf-8"))
    role, reviews = [], []
    f = ROOT / "lessons" / f"{lid}_role.json"
    if f.exists():
        role = json.loads(f.read_text(encoding="utf-8"))
    f = ROOT / "lessons" / f"{lid}_review.json"
    if f.exists():
        reviews = json.loads(f.read_text(encoding="utf-8"))

    data = {"meta": meta, "vocab": vocab, "sents": sents,
            "passage": passage, "errs": errs, "cults": cults, "role": role}

    # ---- HTML 片段 ----
    vocab_html = "\n".join(
        f'<div class="vcard" onclick="speak(\'{e(s["w"])}\',\'en\',0.8)">'
        f'<span class="vpos">{e(s["pos"])}</span>'
        f'<span class="vw">{e(s["w"])}</span><span class="vph">{e(s["ph"])}</span>'
        f'<div class="vcn">{e(s["cn"])}</div>'
        f'<div class="veg">↳ {e(s["eg"])}</div></div>'
        for s in vocab)

    sents_html = "\n".join(
        f'<div class="sent" onclick="speak(strip(this.querySelector(\'.en\').innerHTML),\'en\',0.85)">'
        f'<div class="en">{hl(s["en"])}</div>'
        f'<div class="zh">{e(s["zh"])}</div>'
        f'<div class="tip2">{hl(s["tip"])}</div></div>'
        for s in sents)

    passage_html = "\n".join(
        f'<div class="pline" onclick="speak(strip(this.querySelector(\'.ten\').innerHTML),\'en\',0.82)">'
        f'<div class="who {wcls}">{e(p["who"])}</div>'
        f'<div class="ten">{hl(p["en"])}</div>'
        f'<div class="tcn">{e(p["zh"])}</div></div>'
        for p, wcls in ((p, "who you" if p["who"].upper() == "YOU" else "who")
                        for p in passage))

    errs_html = "\n".join(
        f'<div class="err"><div class="fix">'
        f'<span class="b">{e(s2["bad"])}</span> → <span class="g">{e(s2["good"])}</span></div>'
        f'<div class="why">{hl(s2["why"])}</div></div>'
        for s2 in errs) or '<div style="color:#6B7A8C;font-size:14px">本课暂无易错记录</div>'

    cult_html = "\n".join(
        f'<div class="cult"><div class="ic">{c["ic"]}</div>'
        f'<div class="tx">{hl(c["tx"])}</div></div>' for c in cults)

    review_html = "\n".join(
        f'<div class="err"><div class="why" style="font-size:14.5px;color:var(--ink);'
        f'font-weight:700">Q{r["i"]}. {e(r["q"])}</div>'
        f'<div class="why hide" onclick="this.classList.toggle(\'show\')" '
        f'style="cursor:pointer;filter:blur(5px)">点此显示答案 → {e(r["a"])}</div></div>'
        for r in reviews)

    days = ["10/13", "10/14", "10/15", "10/16", "10/17", "10/18", "10/19"]
    day_html = ""
    for i, d in enumerate(days):
        cls = "day" + (" done" if i == 0 else "") + (" today" if i == 1 else "")
        idc = ' id="todayCell"' if i == 1 else ""
        c = "✓" if i == 0 else ("·" if i == 1 else "")
        day_html += (f'<div class="{cls}"{idc}><div class="n">{d}</div>'
                     f'<div class="d">{"🎉" if i==0 else ("📖" if i==1 else "·")}</div>'
                     f'<div class="c">{c}</div></div>')

    img_html = (f'<img src="{_img_uri(passage_img)}" alt="">' if passage_img else "")
    cap_html = f'<div class="cap">{e(passage_cap)}</div>' if passage_cap else ""

    html = f"""<!DOCTYPE html>
<html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>第 {meta['lesson']} 课 · {meta['scene']} · 美国生活英语</title>
<style>{CSS}</style></head><body>
<div class="hero"><div class="inner">
  <div class="kicker">{meta['series']} · LESSON {meta['lesson']}</div>
  <h1>{meta['scene']}</h1>
  <p>{len(vocab)} 个词汇 · {len(sents)} 句口语 · 1 段短文 · 实战 + 复习 · 约 10 分钟</p>
  <div class="meta">
    <span class="pill">🎬 有讲解视频</span>
    <span class="pill">🔊 点任意内容即发音</span>
    <span class="pill">🎭 角色扮演实战</span>
    <span class="pill">🔁 间隔复习曲线</span>
  </div>
</div></div>

<div class="wrap">
  <div class="tabs">
    <button class="on" data-p="p1">① 场景词汇</button>
    <button data-p="p2">② 场景口语</button>
    <button data-p="p3">③ 场景短文</button>
    <button data-p="p4">④ 实战</button>
    <button data-p="p5">⑤ 易错点·复习</button>
  </div>

  <div class="panel on" id="p1">
    <div class="card">
      <h2><div class="sect-no">1</div>场景词汇 · 点卡片听发音</h2>
      <div class="desc">这 {len(vocab)} 个词是今天的地基。每个都点一遍，先混个耳熟。</div>
      <div class="vgrid">{vocab_html}</div>
      <div class="ctrl"><button class="btn btn-p" id="playAllV">▶ 按顺序读一遍</button></div>
    </div>
  </div>

  <div class="panel" id="p2">
    <div class="card">
      <h2><div class="sect-no">2</div>场景口语 · 点句子即朗读</h2>
      <div class="desc">海关会问的就是这几句。反复点，直到不用想就能脱口而出。</div>
      {sents_html}
      <div class="ctrl"><button class="btn btn-p" id="playAllS">▶ 连续播放全部</button></div>
    </div>
  </div>

  <div class="panel" id="p3">
    <div class="card">
      <h2><div class="sect-no">3</div>场景短文 · 听三遍</h2>
      <div class="desc">按「纯英文 → 双语 → 盲听」三遍来练：第一遍只看英文，第二遍对照中文，第三遍不看字，直接听。</div>
      <div class="lmode" id="lmode">
        <button data-m="en">① 纯英文</button>
        <button class="on" data-m="bi">② 双语</button>
        <button data-m="blind">③ 盲听</button>
        <span class="hint" id="lmHint">英文 + 中文，对照着听</span>
      </div>
      <div class="passage mode-bi" id="passageBox">
        <div class="plist">{passage_html}</div>
        <div class="pic">{img_html}{cap_html}</div>
      </div>
      <div class="ctrl"><button class="btn btn-p" id="playAllP">▶ 完整朗读短文</button></div>
    </div>
  </div>

  <div class="panel" id="p4">
    <div class="card">
      <h2><div class="sect-no">4</div>实战 · 我扮海关官员</h2>
      <div class="desc">真实通关题。选错会告诉你为什么才对——这比看答案有用得多。</div>
      <div class="step-dots"></div>
      <div id="roleBox"></div>
      <div class="chips" id="chips"></div>
      <div class="fb" id="fb"></div>
    </div>
  </div>

  <div class="panel" id="p5">
    <div class="card">
      <h2><div class="sect-no">5</div>易错点 · 中式英语重灾区</h2>
      <div class="desc">这些是中国学习者最常犯的错误，见到就改。</div>
      {errs_html}
    </div>
    <div class="card">
      <h2><div class="sect-no">6</div>美国文化备忘录</h2>
      <div class="desc">语法对了，态度不对也过不去。</div>
      {cult_html}
    </div>
    <div class="card">
      <h2><div class="sect-no">7</div>主动回忆 + 打卡</h2>
      <div class="desc"><b>先自己说出来</b>，再点开对照。按遗忘曲线：今天 → 明天 → 3 天后 → 7 天后。</div>
      {review_html}
      <div class="streak">{day_html}</div>
      <div class="ctrl" style="justify-content:flex-start;margin-top:18px">
        <button class="btn btn-p" onclick="markDone()">✅ 完成今日打卡</button>
      </div>
    </div>
  </div>
</div>

<script>window.__DATA__ = {json.dumps(data, ensure_ascii=False)};
{JS}
</script>
</body></html>"""
    return build(html, name)


def hl(s):
    import html as H
    s = H.escape(s or "")
    s = re.sub(r"==(.+?)==", r'<mark>\1</mark>', s)
    s = re.sub(r"\*\*(.+?)\*\*", r'<b>\1</b>', s)
    return s


def e(s):
    import html as H
    return H.escape(s or "")


if __name__ == "__main__":
    p = make(sys.argv[1] if len(sys.argv) > 1 else "lessons/01.json")
    print("✅", p)
