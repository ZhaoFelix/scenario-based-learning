#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
场景化学习课件 · 视频引擎
  课程 JSON -> HTML 板书页 -> Playwright 逐帧截图 -> 音轨 -> ffmpeg 合成 MP4

用法:  python3 render.py lessons/01.json       (在课程项目目录下执行)
  产物: <项目>/build/(中间产物)  <项目>/out/NN_场景.mp4

路径约定:
  ROOT      = 课程项目目录 = 环境变量 SBL_ROOT, 否则当前工作目录
  SCRIPT_DIR= 本脚本所在目录(技能 scripts/, 存放 shot.js 等前端脚本)
"""
import asyncio
import base64
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

try:
    import edge_tts
except ImportError:                      # 首选后端是 MiMo, edge-tts 仅作回退
    edge_tts = None

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("SBL_ROOT") or Path.cwd()).resolve()
BUILD = ROOT / "build"
FRAMES = BUILD / "frames"
AUDIO = BUILD / "audio"
OUT = ROOT / "out"

W, H = 1920, 1080
FPS = 25
VOICE_EN = "en-US-AriaNeural"
VOICE_ZH = "zh-CN-XiaoxiaoNeural"
RATE_EN = "-10%"
RATE_ZH = "+6%"

PAD = 0.42          # 每步尾部留白(秒)
MIN_DUR = 1.05      # 每步最短展示
SUB_FRAME = 0.075   # 过渡子帧时长
SUB_TS = [0.3, 0.65, 1.0]   # 过渡子帧的定格进度

os_ = None


def _node_bin():
    """定位 node(Playwright 前端脚本用): SBL_NODE > PATH > 托管安装 > 常见路径"""
    cands = []
    if os.environ.get("SBL_NODE"):
        cands.append(os.environ["SBL_NODE"])
    w = shutil.which("node")
    if w:
        cands.append(w)
    base = Path.home() / ".workbuddy/binaries/node/versions"
    if base.exists():
        cands += [str(p) for p in sorted(base.glob("*/bin/node"))]
    cands += ["/usr/local/bin/node", "/opt/homebrew/bin/node"]
    for c in cands:
        if c and os.path.exists(c):
            return c
    sys.exit("找不到 node: Playwright 前端脚本需要 Node.js")


def _node_env():
    """node 运行环境, 自动补 NODE_PATH 让 require('playwright') 可解析"""
    env = dict(os.environ)
    if not env.get("NODE_PATH"):
        for d in (Path.home() / ".workbuddy/binaries/node/workspace/node_modules",
                  ROOT / "node_modules", SCRIPT_DIR / "node_modules"):
            if d.exists():
                env["NODE_PATH"] = str(d)
                break
    return env


def run_node(script, *args):
    """运行技能自带的 node 脚本, 返回 CompletedProcess(stdout/stderr)"""
    return subprocess.run([_node_bin(), str(SCRIPT_DIR / script),
                           *[str(a) for a in args]],
                          env=_node_env(), capture_output=True, text=True)


def _real_ffmpeg():
    """定位真实 ffmpeg: SBL_FFMPEG > imageio_ffmpeg > 系统 ffmpeg(需探测)
    注意: 某些环境 /opt/homebrew/bin/ffmpeg 是只支持 PNG 的伪 wrapper,
    所以每个候选都必须通过 -f lavfi 探测才采用。"""
    import shutil
    if os.environ.get("SBL_FFMPEG"):
        return os.environ["SBL_FFMPEG"]
    try:
        import imageio_ffmpeg
        p = imageio_ffmpeg.get_ffmpeg_exe()
        if p and os.path.exists(p):
            return p
    except Exception:
        pass
    for c in ("/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg",
              shutil.which("ffmpeg") or ""):
        if not c or not os.path.exists(c):
            continue
        # 探测: 伪 wrapper 不支持 -f lavfi
        try:
            r = subprocess.run([c, "-hide_banner", "-f", "lavfi", "-i",
                                "anullsrc", "-t", "0.05", "-f", "null", "-"],
                               capture_output=True, timeout=20)
            if r.returncode == 0:
                return c
        except Exception:
            continue
    sys.exit("找不到可用的真实 ffmpeg")


FFMPEG = _real_ffmpeg()


def ffprobe_dur(path):
    """用 ffmpeg 读取媒体时长(无 ffprobe 环境下)"""
    try:
        r = subprocess.run([FFMPEG, "-hide_banner", "-i", str(path)],
                           capture_output=True, text=True)
        m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.?\d*)", r.stderr)
        if m:
            return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    except Exception:
        pass
    return 0.0


def log(*a):
    print(*a, flush=True)


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def inline(s):
    """支持 ==荧光高亮== 与 **强调**"""
    s = esc(s)
    s = re.sub(r"==(.+?)==", r'<span class="hl">\1</span>', s)
    s = re.sub(r"\*\*(.+?)\*\*", r'<span class="strong">\1</span>', s)
    return s


# ---------------------------------------------------------------- 1. TTS
# 三后端: MiMo TTS (首选, 音色最好) -> edge-tts -> macOS `say` (离线兜底)
MIMO_URL = "https://api.xiaomimimo.com/v1/chat/completions"
MIMO_MODEL = "mimo-v2.5-tts"
MIMO_VOICE = {"en": "Chloe", "zh": "冰糖"}
# 导演指令放在 user 角色(不会被朗读); 待朗读文本必须放 assistant 角色
MIMO_STYLE = {
    "en": ("You are a native American English speaker. Read the text below at a "
           "clear, unhurried teaching pace, slightly slower than normal "
           "conversation, with warm and friendly intonation."),
    "zh": ("你是一位亲切耐心的英语老师，正在给中国初学者讲解英语。"
           "用自然、口语化的中文讲解，语速平实不拖沓，重点词后稍作停顿，"
           "语气温和、有鼓励感。"),
}
VOICE_EN = ["en-US-AriaNeural", "en-US-JennyNeural", "en-US-GuyNeural"]
VOICE_ZH = ["zh-CN-XiaoxiaoNeural", "zh-CN-XiaoyiNeural"]
SAY_EN = ["Samantha", "Alex", "Daniel"]
SAY_ZH = ["Tingting", "Sinji", "Li-mu"]
RATE_EN = "-10%"
RATE_ZH = "+6%"
SAY_R_EN = 160      # 系统语音语速 wpm(偏慢, 适合教学)
SAY_R_ZH = 180

_MIMO_OK = [True]   # 本次运行 MiMo 是否可用(预检后决定)
_EDGE_OK = [True]   # edge-tts 是否可用
BACKEND = ["say"]   # 实际使用的后端, 决定缓存文件名
ZH_TEMPO = 1.18     # 中文讲解加速(ffmpeg atempo, 不改变音高)
LINK_GAP = 0.45     # 同一块内 英文说完 -> 中文讲解 的间隔
_STYLE_FP = __import__("hashlib").md5(
    ("|".join(MIMO_STYLE.values()) + f"|zh{ZH_TEMPO}").encode()
).hexdigest()[:6]


def _mimo_key():
    k = os.environ.get("MIMO_API_KEY", "").strip()
    if k:
        return k
    p = Path.home() / ".workbuddy" / "mimo_api_key"
    if p.exists():
        return p.read_text(encoding="utf-8").strip()
    return ""


def _estimate_words(text, total):
    """无词级时间戳时, 按字符长度按比例估算"""
    ws = [w for w in re.split(r"(\s+)", text) if w.strip()]
    if not ws:
        return []
    lens = [len(w.strip()) + 1 for w in ws]
    tot = sum(lens)
    out, t = [], 0.0
    for w, L in zip(ws, lens):
        d = max(0.09, total * L / tot)
        out.append({"o": round(t, 3), "d": round(d, 3), "t": w})
        t += d
    return out


def _pcm(src, dst):
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", str(src),
                    "-ar", "44100", "-ac", "1", "-c:a", "pcm_s16le", str(dst)],
                   check=True)


def _pcm_data(data, dst, tempo=1.0):
    """把内存里的音频字节直接转成 44.1k 单声道 wav(走 stdin, 不落临时文件)"""
    args = [FFMPEG, "-y", "-loglevel", "error", "-i", "pipe:0"]
    if abs(tempo - 1.0) > 0.01:
        args += ["-af", f"atempo={tempo:.3f}"]
    args += ["-ar", "44100", "-ac", "1", "-c:a", "pcm_s16le", str(dst)]
    subprocess.run(args, input=data, check=True)


async def _edge_tts(text, voice, rate, out_wav, sub_path, tempo=1.0):
    if edge_tts is None:
        raise RuntimeError("edge-tts 未安装: pip install edge-tts")
    out_wav = Path(out_wav)
    comm = edge_tts.Communicate(text, voice, rate=rate)
    audio, words = b"", []
    async for ch in comm.stream():
        if ch["type"] == "audio":
            audio += ch["data"]
        elif ch["type"] == "WordBoundary":
            words.append({"o": round(ch["offset"] / 1e7 / tempo, 3),
                          "d": round(ch["duration"] / 1e7 / tempo, 3),
                          "t": ch["text"]})
    _pcm_data(audio, out_wav, tempo)
    Path(sub_path).write_text(json.dumps(words, ensure_ascii=False),
                              encoding="utf-8")
    return ffprobe_dur(out_wav)


def _say_tts(text, voice, wpm, out_wav, sub_path, tempo=1.0):
    """macOS 系统语音 (离线)"""
    out_wav = Path(out_wav)
    tmp = Path("/tmp") / f"_say_{os.getpid()}_{abs(hash((voice, text))) % 10**9}.aiff"
    subprocess.run(["say", "-v", voice, "-r", str(wpm),
                    "-o", str(tmp), text], check=True)
    _pcm(tmp, out_wav)
    if abs(tempo - 1.0) > 0.01:
        sped = out_wav.with_suffix(".sped.wav")
        subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", str(out_wav),
                        "-af", f"atempo={tempo:.3f}", str(sped)], check=True)
        sped.replace(out_wav)
    d = ffprobe_dur(out_wav)
    words = _estimate_words(text, d)
    Path(sub_path).write_text(json.dumps(words, ensure_ascii=False),
                              encoding="utf-8")
    return d


def _mimo_tts(text, lang, out_wav, sub_path):
    """小米 MiMo-V2.5-TTS (OpenAI 兼容)。待朗读文本必须放 assistant 角色。"""
    import requests
    out_wav = Path(out_wav)
    tempo = ZH_TEMPO if lang == "zh" else 1.0
    body = {"model": MIMO_MODEL,
            "messages": [{"role": "user", "content": MIMO_STYLE[lang]},
                         {"role": "assistant", "content": text}],
            "audio": {"format": "wav", "voice": MIMO_VOICE[lang]}}
    r = requests.post(MIMO_URL,
                      headers={"Authorization": f"Bearer {_mimo_key()}",
                               "Content-Type": "application/json"},
                      json=body, timeout=180)
    if r.status_code != 200:
        raise RuntimeError(f"MiMo {r.status_code}: {r.text[:180]}")
    b64 = r.json()["choices"][0]["message"]["audio"]["data"]
    _pcm_data(base64.b64decode(b64), out_wav, tempo)
    d = ffprobe_dur(out_wav)
    Path(sub_path).write_text(
        json.dumps(_estimate_words(text, d), ensure_ascii=False),
        encoding="utf-8")
    return d


async def _one_tts(text, lang, out_wav, sub_path):
    """合成一条语音: MiMo -> edge-tts -> 系统 say"""
    out_wav = Path(out_wav)
    loop = asyncio.get_running_loop()
    if _MIMO_OK[0]:
        try:
            return await loop.run_in_executor(
                None, _mimo_tts, text, lang, out_wav, sub_path)
        except Exception as e:
            log(f"  [warn] MiMo 失败({type(e).__name__}: {str(e)[:110]}) -> 回退 edge-tts")
            _MIMO_OK[0] = False
    if _EDGE_OK[0]:
        voices = VOICE_EN if lang == "en" else VOICE_ZH
        rate = RATE_EN if lang == "en" else RATE_ZH
        tempo = 1.0 if lang == "en" else ZH_TEMPO
        for v in voices:
            try:
                return await _edge_tts(text, v, rate, out_wav, sub_path, tempo)
            except Exception:
                continue
        _EDGE_OK[0] = False
        log("  [warn] edge-tts 不可用, 切换到系统语音 (离线)")
    say_voices = SAY_EN if lang == "en" else SAY_ZH
    wpm = SAY_R_EN if lang == "en" else SAY_R_ZH
    tempo = 1.0 if lang == "en" else ZH_TEMPO
    last = None
    for v in say_voices:
        try:
            return await loop.run_in_executor(
                None, _say_tts, text, v, wpm, out_wav, sub_path, tempo)
        except Exception as e:
            last = e
    raise RuntimeError(f"语音合成失败: {last}")


def cid(text, lang):
    """音频缓存键: 后端 + 配音风格指纹 + 语种 + 文本内容。
    按内容去重 —— 同一句在短文三遍里复用时只合成一次;
    风格(导演指令)一变, 缓存自动失效, 避免新旧语速混用。"""
    import hashlib
    return hashlib.md5(
        f"{BACKEND[0]}|{_STYLE_FP}|{lang}|{text}".encode()).hexdigest()[:14]


async def build_audio(lesson):
    """为每个 block 生成中英双轨音频(按内容去重), 并回填时长与词级时间戳"""
    AUDIO.mkdir(parents=True, exist_ok=True)

    # --- 预检: MiMo 可用性决定本次使用的后端(并决定缓存文件名) ---
    if _mimo_key():
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None, _mimo_tts, "Hello.", "en",
                AUDIO / "_pre.wav", AUDIO / "_pre.json")
            BACKEND[0] = "mimo"
            log("[TTS] 后端: MiMo-V2.5-TTS (Chloe / 冰糖)")
        except Exception as e:
            _MIMO_OK[0] = False
            log(f"[TTS] MiMo 预检失败({type(e).__name__}: {str(e)[:110]}) "
                f"-> 回退 edge-tts / 系统语音")
    else:
        _MIMO_OK[0] = False
        log("[TTS] 未配置 MiMo Key -> 用 edge-tts / 系统语音")

    jobs, seen = [], set()
    for slide in lesson["slides"]:
        for b in slide.get("blocks", []):
            en, zh = b.get("say") or "", b.get("say_zh") or ""
            if not en and not zh:
                continue
            if (en, zh) in seen:      # 同文本复用同一条音频
                continue
            seen.add((en, zh))
            jobs.append((en, zh))

    log(f"[TTS] {len(jobs)} 段语音(内容去重后) ...")
    sem = asyncio.Semaphore(4)

    async def one(en, zh):
        async with sem:
            tasks = []
            for lang, txt in (("en", en), ("zh", zh)):
                if not txt:
                    continue
                w = AUDIO / f"{cid(txt, lang)}.wav"
                if w.exists() and w.stat().st_size > 2000:
                    continue          # 已缓存, 跳过
                tasks.append(_one_tts(txt, lang, w, AUDIO / f"{cid(txt, lang)}.json"))
            if tasks:
                await asyncio.gather(*tasks)

    for i in range(0, len(jobs), 4):
        try:
            await asyncio.gather(*[one(*k) for k in jobs[i:i + 4]])
        except Exception as e:
            log(f"  [ERROR] 批次 {i} 失败: {type(e).__name__}: {e}")
            raise
        log(f"  · {min(i + 4, len(jobs))}/{len(jobs)}")

    # 收集时长
    for slide in lesson["slides"]:
        for b in slide.get("blocks", []):
            en, zh = b.get("say") or "", b.get("say_zh") or ""
            de = dz = 0.0
            words = []
            if en:
                pe = AUDIO / f"{cid(en, 'en')}.wav"
                if pe.exists():
                    de = ffprobe_dur(pe)
                    sp = AUDIO / f"{cid(en, 'en')}.json"
                    if sp.exists():
                        words = json.loads(sp.read_text(encoding="utf-8"))
            if zh:
                pz = AUDIO / f"{cid(zh, 'zh')}.wav"
                if pz.exists():
                    dz = ffprobe_dur(pz)
            # 块内顺序播放: 英文 -> 间隔 -> 中文讲解(短文页无讲解, 只有英文)
            link = LINK_GAP if (de > 0.05 and dz > 0.05) else 0.0
            hold = float(b.get("hold", MIN_DUR))   # 无音频的标题页可用 hold 指定停留
            b["_dur"] = max(de + link + dz, hold) + PAD
            b["_den"], b["_dzh"] = de, dz
            b["_en"], b["_zh"] = en, zh
            # 只有 shadow 块需要词级高亮数据
            if b.get("type") == "shadow":
                b["_words"] = words if words else _estimate_words(en, de)
    return


# -------------------------------------------- 1.5 版面: 短文三遍 + 自动分页
PASS_LABEL = {"en": "第一遍 · 纯英文", "bi": "第二遍 · 双语", "blind": "第三遍 · 盲听"}
PASS_HINT = {
    "en": ("🎧", "只听英文，先不看中文"),
    "bi": ("📖", "英文 + 中文，对照着听"),
    "blind": ("🙈", "盲听 · 只听不看字"),
}
GAP = {"stack": 30, "vocab": 11, "passage": 9, "blind": 24, "cover": 38}
STAGE_PAD = 58          # .stage 上下 padding 合计


def expand_passes(lesson):
    """把带 passes 字段的短文页, 展开成「纯英文 / 双语 / 盲听」三页。
    同一段英文在三个 pass 里内容一致, 音频按内容去重只合成一次。"""
    out = []
    for sl in lesson["slides"]:
        modes = sl.get("passes")
        if not modes:
            out.append(sl)
            continue
        lines = [b for b in sl.get("blocks", []) if b.get("type") == "line"]
        for mode in modes:
            page = {k: v for k, v in sl.items() if k != "passes"}
            page["name"] = f"{sl.get('name', '场景短文')} · {PASS_LABEL[mode]}"
            page["pass_mode"] = mode
            ic, tip = PASS_HINT[mode]
            head = {"type": "sub",
                    "text": f"PART 3 · 场景短文 · {PASS_LABEL[mode]}",
                    "hold": 1.8}
            if mode == "en":
                bs = [head] + [dict(b, cn="") for b in lines]
            elif mode == "bi":
                bs = [head] + [dict(b) for b in lines]
            else:                                   # blind: 不显示任何文字
                full = " ".join((b.get("say") or b.get("text", ""))
                                .replace("==", "").replace("**", "") for b in lines)
                page["layout"] = "blind"
                bs = [head, {"type": "blind", "say": full.strip(),
                             "text": f"{tip}", "ic": ic, "hold": 2.2}]
            page["blocks"] = bs
            out.append(page)
    return out


def measure_pages(html_path):
    """用 Playwright 实测每一页的真实高度(整页 + 逐块), 供自动分页使用"""
    out = BUILD / "measure.json"
    r = run_node("measure.js", html_path, out)
    if "MEASURED" not in r.stdout or not out.exists():
        log("  [warn] 版面测量失败, 跳过自动分页")
        sys.stderr.write((r.stderr or "")[-800:] + "\n")
        return None
    try:
        return json.loads(out.read_text(encoding="utf-8"))
    except Exception:
        return None


def paginate(lesson, meas):
    """内容比一页装得下时, 自动拆成多页 —— 从根源上避免板书重叠。
    按实测高度贪心装箱: 装不下就翻页; 尾页只剩一点点时并回上一页。"""
    if not meas or len(meas) != len(lesson["slides"]):
        return lesson["slides"]
    out, split = [], 0
    for si, sl in enumerate(lesson["slides"]):
        blocks = sl.get("blocks", [])
        layout = sl.get("layout", "stack")
        m = meas[si]
        avail = float(m["avail"]) - 4      # 留 4px 余量; 再高交给自适应缩放兜底
        bh = m["bh"]
        if not blocks or len(bh) != len(blocks):
            out.append(sl)
            continue

        # 组成「行」: 词汇页是两列网格, 一行两个词, wide 块独占一行
        if layout == "vocab":
            rows, i = [], 0
            while i < len(bh):
                if blocks[i].get("wide") or i + 1 >= len(bh) or blocks[i + 1].get("wide"):
                    rows.append(([i], bh[i]))
                    i += 1
                else:
                    rows.append(([i, i + 1], max(bh[i], bh[i + 1])))
                    i += 2
        else:
            rows = [([i], bh[i]) for i in range(len(bh))]

        gap = GAP.get(layout, 30)
        groups, cur, h = [], [], 0.0
        for idxs, rh in rows:
            add = rh + (gap if cur else 0)
            if cur and h + add > avail:
                groups.append((cur, h))
                cur, h, add = [], 0.0, rh
            cur.extend(idxs)
            h += add
        if cur:
            groups.append((cur, h))
        # 页数不均衡(例如 9 行 / 3 行)时按条数重排, 让每页篇幅接近
        if len(groups) > 1 and groups[-1][1] < groups[0][1] * 0.55:
            n = len(groups)
            per = -(-len(rows) // n)
            cand, i = [], 0
            while i < len(rows):
                chunk = rows[i:i + per]
                hh = sum(r[1] for r in chunk) + gap * (len(chunk) - 1)
                cand.append(([x for idxs, _ in chunk for x in idxs], hh))
                i += per
            if len(cand) == n and all(c[1] <= avail for c in cand):
                groups = cand
        # 尾页过小则并回上一页(交给自适应缩放兜底), 避免出现只有一行字的孤页
        while len(groups) > 1 and groups[-1][1] < avail * 0.30:
            gi, gh = groups.pop()
            pi, ph = groups.pop()
            groups.append((pi + gi, ph + gap + gh))

        if len(groups) <= 1:
            out.append(sl)
            continue
        for gi, (idxs, _h) in enumerate(groups):
            part = dict(sl)
            part["blocks"] = [blocks[i] for i in idxs]
            part["_cont"] = gi > 0
            out.append(part)
        split += 1
    if split:
        log(f"[PAGE] {split} 页内容过多, 自动拆分为多页显示")
    return out


# ---------------------------------------------------------------- 2. HTML
CSS = """
*{margin:0;padding:0;box-sizing:border-box}
:root{--t:1}
html,body{width:1920px;height:1080px;overflow:hidden}
body{
  font-family:'PingFang SC','Hiragino Sans GB','Songti SC',sans-serif;
  background:#FBF7EE;
  background-image:
    repeating-linear-gradient(0deg,rgba(70,100,140,.055) 0 1px,transparent 1px 44px),
    radial-gradient(1200px 700px at 88% -10%,rgba(255,214,120,.30),transparent 62%),
    radial-gradient(900px 600px at -6% 108%,rgba(150,200,255,.22),transparent 60%);
  color:#1E2A3A;position:relative;
}
/* 左侧红色装订线 */
body::before{content:'';position:absolute;top:0;bottom:0;left:96px;width:2px;
  background:rgba(220,90,90,.35)}
body::after{content:'';position:absolute;top:0;bottom:0;left:88px;width:14px;
  background:rgba(220,90,90,.07)}

.topbar{position:absolute;top:0;left:0;right:0;height:92px;display:flex;
  align-items:center;gap:22px;padding:0 78px 0 132px;
  border-bottom:2px dashed rgba(60,90,130,.22);z-index:20}
.crumb{font-size:23px;letter-spacing:2px;color:#7A8CA3;font-weight:600}
.crumb b{color:#E06C4F;font-weight:800}
.spacer{flex:1}
.prog{font-size:21px;color:#93A3B6;letter-spacing:1px;font-variant-numeric:tabular-nums}

.stage{position:absolute;top:92px;left:132px;right:78px;bottom:0;padding:34px 0 24px;
  display:flex;align-items:center;z-index:10}
.slide{display:none;flex-direction:column;gap:30px;width:100%}
.slide.live{display:flex}

.h{font-size:70px;font-weight:800;letter-spacing:1px;line-height:1.22;color:#16233A}
.h .en{font-family:'Chalkboard SE','Bradley Hand','Marker Felt',cursive;
  color:#1B5FA8;letter-spacing:1px}
.sub{font-size:31px;color:#8497AC;letter-spacing:3px;font-weight:600}

.cover{justify-content:center;gap:38px}
.cover .kicker{display:inline-block;align-self:flex-start;font-size:28px;font-weight:800;
  letter-spacing:6px;color:#fff;background:#E06C4F;padding:13px 30px;border-radius:6px;
  transform:rotate(-1.4deg)}
.cover .title{font-size:116px;font-weight:900;line-height:1.1;color:#16233A}
.cover .title .en{font-family:'Chalkboard SE','Bradley Hand',cursive;color:#1B5FA8;
  display:block;font-size:72px;letter-spacing:2px;margin-top:14px;opacity:.92}
.cover .goal{font-size:32px;color:#5B6E85;line-height:1.75;max-width:1360px;
  border-left:7px solid #F2C14E;padding-left:26px;margin-top:8px}

.enline{font-family:'Chalkboard SE','Bradley Hand','Marker Felt',cursive;
  font-size:64px;line-height:1.34;color:#16233A;letter-spacing:.5px}
.enline.big{font-size:82px}
.enline .hl{background:linear-gradient(transparent 56%,#FFE08A 56%);
  padding:0 4px;border-radius:2px}
.strong{font-weight:800;color:#C8452E}

.zhline{font-size:35px;color:#5F7387;line-height:1.6}
.zhline .hl{background:linear-gradient(transparent 58%,#FFD9A0 58%);padding:0 3px}

.note{font-size:30px;color:#6E8090;line-height:1.7;display:flex;gap:16px;
  align-items:flex-start}
.note .tag{flex:0 0 auto;font-size:21px;font-weight:800;letter-spacing:1px;
  background:#EDF3FA;color:#3A6EA8;padding:6px 15px;border-radius:5px;margin-top:5px}

.bad,.good{display:flex;gap:18px;align-items:flex-start;font-size:43px;line-height:1.45;
  padding:18px 28px;border-radius:10px}
.bad{font-family:'Chalkboard SE','Bradley Hand',cursive;color:#B3382C;
  background:rgba(226,90,74,.09);border-left:8px solid #E25A4A}
.good{font-family:'Chalkboard SE','Bradley Hand',cursive;color:#1E7A52;
  background:rgba(58,168,116,.10);border-left:8px solid #3AA874}
.bad .mk,.good .mk{font-family:'PingFang SC',sans-serif;font-weight:900;font-size:38px;
  flex:0 0 auto}

.kv{display:flex;gap:20px;align-items:baseline;font-size:35px;line-height:1.55;
  color:#2A3A4D}
.kv .dot{flex:0 0 auto;width:15px;height:15px;border-radius:50%;background:#F2A93B;
  margin-top:17px}

.tip{display:flex;gap:18px;align-items:flex-start;font-size:31px;line-height:1.7;
  color:#4A5C70;background:rgba(242,169,59,.12);border:1px dashed #E0A03A;
  padding:22px 30px;border-radius:12px}
.tip .ic{flex:0 0 auto;font-size:36px;line-height:1.2}

/* 跟读高亮 */
.shadow{font-family:'Chalkboard SE','Bradley Hand',cursive;font-size:70px;line-height:1.5;
  color:#16233A}
.shadow .w{transition:none;padding:2px 4px;border-radius:4px}
.shadow .w.on{background:#FFD84D;color:#16233A;box-shadow:0 3px 0 rgba(0,0,0,.10)}
.shadow .w.past{color:#96A6B8}

/* 流程图 */
.flow{display:flex;align-items:stretch;gap:0}
.flow .step{flex:1;position:relative;background:#fff;border:2.5px solid #C9D8E8;
  border-radius:14px;padding:26px 22px;box-shadow:0 6px 18px rgba(40,70,110,.09)}
.flow .step .n{font-size:22px;font-weight:900;color:#fff;background:#4A7EBB;
  width:38px;height:38px;border-radius:50%;display:flex;align-items:center;
  justify-content:center;margin-bottom:14px}
.flow .step .t{font-family:'Chalkboard SE','Bradley Hand',cursive;font-size:34px;
  color:#1B3A5C;line-height:1.3;margin-bottom:10px}
.flow .step .d{font-size:24px;color:#78899C;line-height:1.5}
.flow .arrow{flex:0 0 54px;display:flex;align-items:center;justify-content:center;
  font-size:40px;color:#9DB2C8}

/* 便签 */
.card{background:#FFFDF7;border:2px solid #E4DCC8;border-radius:14px;padding:26px 32px;
  box-shadow:0 8px 22px rgba(90,80,50,.10);max-width:1460px;transform:rotate(-.35deg)}

.rule{height:0;border-top:2.5px solid rgba(60,90,130,.28);width:100%;margin:4px 0}

/* reveal 动画(用 --t 定格)。未显现的块不占布局空间, 内容随讲解逐条下移 */
.reveal{opacity:0;transform:translateY(18px)}
.reveal:not(.on){display:none}
.reveal.on{animation:rev .46s cubic-bezier(.2,.85,.3,1) both;
  animation-play-state:paused;animation-delay:calc(var(--t,1) * -0.46s)}
@keyframes rev{from{opacity:0;transform:translateY(18px)}
  to{opacity:1;transform:none}}
@media print{.reveal{opacity:1 !important;transform:none !important}}

/* ---- PART1 词汇网格 ---- */
.slide.vocab.live{display:grid;grid-template-columns:1fr 1fr;gap:11px 26px;
  align-content:start}
.slide.vocab .sub{font-size:24px}
.slide.vocab .h{font-size:46px}
.slide.vocab .tip{font-size:25px;padding:12px 22px}
.slide.vocab > .reveal.wide{grid-column:span 2}
.vcard{background:#FFFDF7;border:2px solid #E3DACA;border-radius:13px;
  padding:12px 20px 13px;box-shadow:0 5px 14px rgba(90,80,50,.08)}
.vcard .vtop{display:flex;align-items:baseline;gap:11px}
.vcard .vw{font-family:'Chalkboard SE','Bradley Hand',cursive;font-size:35px;
  color:#1B5FA8;letter-spacing:.5px;line-height:1.1}
.vcard .vph{font-size:18px;color:#8A97A8;
  font-family:ui-monospace,'SF Mono',Menlo,monospace}
.vcard .vpos{margin-left:auto;font-size:17px;color:#A89B78;font-style:italic;
  background:#F6F1E4;padding:2px 10px;border-radius:20px;white-space:nowrap}
.vcard .vcn{font-size:23px;color:#33455A;font-weight:700;margin-top:4px}
.vcard .veg{font-size:19px;color:#7A8A9C;margin-top:3px;line-height:1.4;
  font-family:'Chalkboard SE','Bradley Hand',cursive}
.vcard .veg::before{content:'↳ ';color:#C4B896}

/* ---- PART2 短句卡 ---- */
.pcard{background:#FFFDF7;border:2px solid #E3DACA;border-left:9px solid #4A7EBB;
  border-radius:14px;padding:24px 32px;box-shadow:0 7px 20px rgba(40,70,110,.10)}
.pcard .pen{font-family:'Chalkboard SE','Bradley Hand',cursive;font-size:56px;
  color:#16233A;line-height:1.28}
.pcard .pcn2{font-size:31px;color:#5F7387;margin-top:10px}
.pcard .ptip{font-size:24px;color:#8A97A8;margin-top:12px;padding-top:12px;
  border-top:1.5px dashed #E0D8C6;line-height:1.55}
.pcard .ptip::before{content:'💡 '}

/* ---- PART3 短文(图文并置) ---- */
.slide.passage{flex-direction:row;gap:46px;align-items:stretch}
.passage-text{flex:1.28;display:flex;flex-direction:column;gap:9px;min-width:0;
  padding-right:6px}
.passage-pic{flex:.72;display:flex;min-width:0}
.passage-pic .ph{position:relative;border-radius:16px;overflow:hidden;flex:1;
  box-shadow:0 12px 34px rgba(60,50,30,.22);border:3px solid #fff;
  transform:rotate(.5deg)}
.passage-pic .ph img{width:100%;height:100%;object-fit:cover;display:block}
.passage-pic .cap{position:absolute;left:0;right:0;bottom:0;padding:30px 22px 18px;
  background:linear-gradient(transparent,rgba(22,35,58,.88));
  color:#fff;font-size:24px;letter-spacing:1px;text-align:center}
.pline{display:flex;gap:14px;align-items:flex-start;padding:7px 14px;border-radius:9px}
.pline .who{flex:0 0 auto;font-size:17px;font-weight:900;letter-spacing:1px;
  color:#fff;background:#8FA3B8;border-radius:5px;padding:4px 10px;margin-top:7px}
.pline .who.you{background:#3AA874}
.pline .txt{min-width:0}
.pline .ten{font-family:'Chalkboard SE','Bradley Hand',cursive;font-size:27px;
  color:#54677C;line-height:1.42}
.pline .tcn{display:none;font-size:22px;color:#3A4C60;margin-top:3px;line-height:1.5}
.pline.cur{background:rgba(255,216,77,.32);box-shadow:inset 0 0 0 2.5px #F2C14E}
.pline.cur .who{background:#E06C4F}
.pline.cur .who.you{background:#1E7A52}
.pline.cur .ten{color:#16233A}
.pline.cur .tcn{display:block}

/* ---- PART4 易错点 ---- */
.err{background:#FFFDF7;border:2px solid #E3DACA;border-radius:14px;
  padding:20px 28px;box-shadow:0 6px 16px rgba(90,80,50,.08)}
.err .erow{display:flex;gap:15px;align-items:baseline;
  font-family:'Chalkboard SE','Bradley Hand',cursive;font-size:40px;line-height:1.32}
.err .emk{font-family:'PingFang SC',sans-serif;font-weight:900;font-size:33px;
  flex:0 0 auto}
.err .ebad{color:#B3382C;text-decoration:line-through;
  text-decoration-thickness:3.5px;text-decoration-color:rgba(226,90,74,.55)}
.err .egood{color:#1E7A52}
.err .ewhy{font-size:25px;color:#6E8090;margin-top:11px;padding-top:11px;
  border-top:1.5px dashed #E0D8C6;line-height:1.55}

/* ---- 自适应缩放: 内容再高也不会跟页眉/页脚重叠 ---- */
.slide{transform-origin:center center}
.contmark{position:absolute;right:78px;top:100px;font-size:21px;font-weight:800;
  letter-spacing:2px;color:#fff;background:#E06C4F;padding:5px 15px;border-radius:6px;
  box-shadow:0 4px 12px rgba(200,90,60,.28);display:none;z-index:26}
.meas .pline .tcn{display:block !important}      /* 测量时把所有双语行撑开 */
.slide.mode-en .pline .tcn{display:none !important}
.slide.mode-bi .pline .tcn{display:block}        /* 第二遍: 整段双语同时显示 */

/* ---- PART3 短文 · 三遍听法 ---- */
.slide.blind{flex-direction:row;gap:46px;align-items:center}
.blindtext{flex:1.28;display:flex;flex-direction:column;gap:24px;min-width:0}
.badge{display:flex;align-items:center;gap:22px;font-size:40px;font-weight:900;
  line-height:1.35;color:#1B3A5C;background:#FFFDF7;border:3px dashed #C9D8E8;
  border-radius:20px;padding:30px 38px;box-shadow:0 10px 26px rgba(40,70,110,.11)}
.badge .ic{font-size:60px;line-height:1}
"""

JS = """
const S = window.__STAGE;
const slides = () => document.querySelectorAll('.slide');

// 预量每一页的自然高度: 内容超出可视区就整体等比缩小, 绝不会和页眉重叠
function measureFit(){
  const stage = document.querySelector('.stage');
  if(!stage) return;
  S.avail = stage.clientHeight - 58;
  S.fitH = [];
  const secs = slides();
  document.body.classList.add('meas');
  secs.forEach((sec, i)=>{
    secs.forEach(s=>s.classList.remove('live'));
    sec.classList.add('live');
    sec.querySelectorAll('.reveal').forEach(e=>e.classList.add('on'));
    S.fitH[i] = sec.scrollHeight;
    sec.classList.remove('live');
    sec.querySelectorAll('.reveal').forEach(e=>e.classList.remove('on'));
  });
  document.body.classList.remove('meas');
}

function setStep(g, t){
  // 只显示当前 step 所属的 slide
  let cur = 0;
  for(let i=0;i<S.offsetBefore.length;i++){ if(g >= S.offsetBefore[i]) cur = i; }
  const secs = slides();
  secs.forEach((sec,i)=>{
    sec.classList.toggle('live', i === cur);
    sec.style.transform = '';
  });
  // 当前 step 的块随 t 逐笔写出, 之前的块保持完全显现
  const tv = (t === undefined ? 1 : t);
  document.querySelectorAll('.reveal').forEach(e=>{
    const on = (+e.dataset.reveal) <= g;
    e.classList.toggle('on', on);
    if(on) e.style.setProperty('--t', (+e.dataset.reveal === g) ? tv : 1);
  });
  // 短文页: 高亮当前正在读的那一行 (data-reveal 在外层 .reveal 上)
  document.querySelectorAll('.pline').forEach(e=>{
    const r = e.closest('.reveal');
    e.classList.toggle('cur', !!r && +r.dataset.reveal === g);
  });
  // 内容过长 -> 整体缩放适配(不影响换行与排版结构)
  const sec = secs[cur];
  if(sec && S.fitH && S.avail){
    const k = Math.min(1, S.avail / Math.max(1, S.fitH[cur]));
    if(k < 0.995) sec.style.transform = 'scale(' + k.toFixed(4) + ')';
  }
  const el = document.getElementById('prog');
  if(el) el.textContent = '第 ' + (cur+1) + ' / ' + S.offsetBefore.length + ' 页';
  const cm = document.getElementById('contmark');
  if(cm) cm.style.display = (S.cont && S.cont[cur]) ? 'block' : 'none';
}
measureFit();
function setShadow(idx, t){
  const el = document.querySelectorAll('[data-shadow]')[idx];
  if(!el) return;
  el.querySelectorAll('.w').forEach(w=>{
    const a = parseFloat(w.dataset.a), d = parseFloat(w.dataset.d);
    w.classList.toggle('on', t >= a && t < a+d);
    w.classList.toggle('past', t >= a+d);
  });
}
window.setStep = setStep;
window.setShadow = setShadow;
"""


def block_html(b, idx, slide_idx, layout):
    t = b.get("type", "note")
    batch = b.get("batch", 0)
    cls = "reveal" + (" wide" if b.get("wide") else "")
    at = (f'data-reveal="{idx}" data-batch="{batch}" '
          f'data-slide="{slide_idx}" class="{cls}"')
    if t == "h":
        return f'<div {at}><div class="h">{inline(b["text"])}</div></div>'
    if t == "sub":
        return f'<div {at}><div class="sub">{inline(b["text"])}</div></div>'
    if t == "en":
        cls2 = "enline" + (" big" if b.get("big") else "")
        return f'<div {at}><div class="{cls2}">{inline(b["text"])}</div></div>'
    if t == "zh":
        return f'<div {at}><div class="zhline">{inline(b["text"])}</div></div>'
    if t == "vocab":
        return (f'<div {at}><div class="vcard">'
                f'<div class="vtop"><span class="vw">{esc(b["w"])}</span>'
                f'<span class="vph">{esc(b.get("ph",""))}</span>'
                f'<span class="vpos">{esc(b.get("pos",""))}</span></div>'
                f'<div class="vcn">{inline(b.get("cn",""))}</div>'
                f'<div class="veg">{inline(b.get("eg",""))}</div>'
                f'</div></div>')
    if t == "phrase":
        return (f'<div {at}><div class="pcard">'
                f'<div class="pen">{inline(b["en"])}</div>'
                f'<div class="pcn2">{inline(b.get("cn",""))}</div>'
                f'<div class="ptip">{inline(b.get("tip",""))}</div>'
                f'</div></div>')
    if t == "line":
        who = esc(b.get("who", ""))
        wcls = "who" + (" you" if who.upper() == "YOU" else "")
        return (f'<div {at}><div class="pline">'
                f'<span class="{wcls}">{who}</span>'
                f'<div class="txt"><div class="ten">{inline(b["text"])}</div>'
                f'<div class="tcn">{inline(b.get("cn",""))}</div></div>'
                f'</div></div>')
    if t == "err":
        return (f'<div {at}><div class="err">'
                f'<div class="erow"><span class="emk" style="color:#E25A4A">✗</span>'
                f'<span class="ebad">{inline(b["bad"])}</span></div>'
                f'<div class="erow"><span class="emk" style="color:#3AA874">✓</span>'
                f'<span class="egood">{inline(b["good"])}</span></div>'
                f'<div class="ewhy">{inline(b.get("why",""))}</div>'
                f'</div></div>')
    if t == "bad":
        return (f'<div {at}><div class="bad"><span class="mk">✗</span>'
                f'<span>{inline(b["text"])}</span></div></div>')
    if t == "good":
        return (f'<div {at}><div class="good"><span class="mk">✓</span>'
                f'<span>{inline(b["text"])}</span></div></div>')
    if t == "kv":
        return (f'<div {at}><div class="kv"><span class="dot"></span>'
                f'<span>{inline(b["text"])}</span></div></div>')
    if t == "tip":
        return (f'<div {at}><div class="tip"><span class="ic">{b.get("ic","💡")}</span>'
                f'<span>{inline(b["text"])}</span></div></div>')
    if t == "blind":
        return (f'<div {at}><div class="badge"><span class="ic">{b.get("ic","🎧")}</span>'
                f'<span>{inline(b.get("text","盲听"))}</span></div></div>')
    if t == "card":
        inner = "".join(block_html(c, idx, slide_idx, layout) for c in b.get("items", []))
        return f'<div {at}><div class="card">{inner}</div></div>'
    if t == "shadow":
        words = b.get("_words", [])
        cur = 0.0
        spans = []
        for w in words:
            dur = w.get("d", 0.16) or 0.16
            spans.append(f'<span class="w" data-a="{cur:.3f}" data-d="{dur:.3f}">{esc(w["t"])}</span>')
            cur += dur
        return (f'<div {at}><div class="shadow" data-shadow data-total="{cur:.3f}">'
                f'{" ".join(spans)}</div></div>')
    if t == "flow":
        steps = b.get("items", [])
        parts = []
        for i, s in enumerate(steps):
            if i:
                parts.append('<div class="arrow">➜</div>')
            parts.append(f'<div class="step"><div class="n">{i+1}</div>'
                         f'<div class="t">{inline(s["t"])}</div>'
                         f'<div class="d">{inline(s.get("d",""))}</div></div>')
        return f'<div {at}><div class="flow">{"".join(parts)}</div></div>'
    # note
    return (f'<div {at}><div class="note"><span class="tag">{esc(b.get("tag","TIP"))}</span>'
            f'<span>{inline(b["text"])}</span></div></div>')


HTML_OUT = [""]


def _img_uri(rel):
    """把图片内嵌为 base64 data URI (HTML 自包含, file:// 下也能加载)"""
    p = ROOT / rel
    if not p.exists():
        log(f"  [warn] 图片不存在: {p}")
        return ""
    suffix = p.suffix.lower().lstrip(".") or "png"
    mime = "jpeg" if suffix in ("jpg", "jpeg") else suffix
    b64 = base64.b64encode(p.read_bytes()).decode("ascii")
    return f"data:image/{mime};base64,{b64}"


def build_html(lesson, out_name="board.html"):
    meta = lesson["meta"]
    offset_before, cont_flags, idx = [], [], 0
    parts = []
    for si, slide in enumerate(lesson["slides"]):
        offset_before.append(idx)
        cont_flags.append(bool(slide.get("_cont")))
        layout = slide.get("layout", "stack")
        blocks = []
        for b in slide.get("blocks", []):
            blocks.append(block_html(b, idx, si, layout))
            idx += 1
        cls = "slide" + ("" if layout == "stack" else " " + layout)
        mode = slide.get("pass_mode")
        if mode:
            cls += " mode-" + mode
        inner = "".join(blocks)
        if layout in ("passage", "blind") and slide.get("image"):
            uri = _img_uri(slide["image"])
            if layout == "blind":                       # 盲听: 只有画面, 没有文字
                fig = (f'<figure class="passage-pic blind"><div class="ph">'
                       f'<img src="{uri}" alt=""></div></figure>')
                inner = f'<div class="blindtext">{inner}</div>{fig}'
            else:
                at = (f'data-reveal="{offset_before[si]}" data-batch="0" '
                      f'data-slide="{si}" class="reveal wide"')
                fig = (f'<figure class="passage-pic"><div {at}><div class="ph">'
                       f'<img src="{uri}" alt="">'
                       f'<div class="cap">{esc(slide.get("image_caption",""))}</div>'
                       f'</div></div></figure>')
                inner = f'<div class="passage-text">{inner}</div>{fig}'
        elif slide.get("row"):
            inner = f'<div style="display:flex;gap:30px;align-items:flex-start">{inner}</div>'
        parts.append(f'<section class="{cls}">{inner}</section>')

    total = idx
    stage = json.dumps({"offsetBefore": offset_before, "cont": cont_flags,
                        "total": total, "t": 1})
    html = f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<style>{CSS}</style></head><body>
<div class="topbar">
  <div class="crumb">{esc(meta['series'])} · 第 <b>{esc(meta['lesson'])}</b> 课</div>
  <div class="crumb" style="color:#4A5C70">{esc(meta['scene'])}</div>
  <div class="spacer"></div>
  <div class="prog" id="prog">1 / {len(offset_before)}</div>
</div>
<div class="contmark" id="contmark">（续）</div>
<div class="stage">{''.join(parts)}</div>
<script>window.__STAGE={stage};{JS}</script>
</body></html>"""
    HTML_OUT[0] = html
    BUILD.mkdir(parents=True, exist_ok=True)
    p = BUILD / out_name
    p.write_text(html, encoding="utf-8")
    return p


# ---------------------------------------------------------------- 3. 渲染
def render_frames(html_path, lesson):
    """生成渲染计划 -> 调用 node shot.js -> 返回 frames.txt
    帧文件名确定(f00000.png...), 直接覆盖写入, 无需清理旧帧。"""
    FRAMES.mkdir(parents=True, exist_ok=True)

    # 扁平化: [(slide_idx, block)]
    flat = [(si, bi) for si, sl in enumerate(lesson["slides"])
            for bi in range(len(sl.get("blocks", [])))]
    total = len(flat)

    # 每个 slide 的起始全局序号
    off_before, idx = [], 0
    for sl in lesson["slides"]:
        off_before.append(idx)
        idx += len(sl.get("blocks", []))

    plan, manifest, shadow_n = [], [], 0
    shot_i = 0

    def add(step, t, dur, shadow=None, settle=26):
        nonlocal shot_i
        name = f"f{shot_i:05d}.png"
        item = {"out": name, "step": step, "t": t, "settle": settle}
        if shadow is not None:
            item["shadow"] = shadow
        plan.append(item)
        manifest.append((name, dur))
        shot_i += 1

    log(f"[RENDER] {total} 个板书步骤 -> 帧序列")

    for g, (si, bi) in enumerate(flat):
        b = lesson["slides"][si]["blocks"][bi]
        for ts in SUB_TS[:-1]:                      # 板书笔触过渡
            add(g, ts, SUB_FRAME, settle=30)

        words = b.get("_words")
        if b.get("type") == "shadow" and words and b.get("say") and b["_den"] > 1.0:
            zi = shadow_n
            shadow_n += 1
            end = 0.0
            for w in words:
                end = max(end, w["o"] + (w.get("d", 0.16) or 0.16))
            end = max(end + 0.3, b["_den"])
            prev = 0.0
            for w in words:
                a, d = w["o"], (w.get("d", 0.16) or 0.16)
                for m in (a, a + d / 2, a + d):
                    if m - prev >= 0.06:
                        add(g, 1.0, round(m - prev, 3),
                            shadow=[zi, round(prev + 0.01, 3)], settle=20)
                        prev = m
            if end - prev >= 0.05:
                add(g, 1.0, round(end - prev, 3),
                    shadow=[zi, round(prev + 0.01, 3)], settle=20)
        else:
            add(g, 1.0, round(max(b["_dur"] - SUB_FRAME * 2, 0.25), 3), settle=30)
        log(f"  步骤 {g + 1}/{total} · {b.get('_label', b.get('type', ''))}")

    plan_file = BUILD / "plan.json"
    plan_file.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")

    r = run_node("shot.js", plan_file, html_path, FRAMES)
    sys.stdout.write(r.stdout[-300:] + "\n")
    if "DONE" not in r.stdout:
        sys.stderr.write(r.stderr[-1500:] + "\n")
        sys.exit("渲染失败")

    txt = FRAMES / "frames.txt"
    with open(txt, "w", encoding="utf-8") as f:
        for name, d in manifest:
            f.write(f"file '{name}'\nduration {d}\n")
        f.write(f"file '{manifest[-1][0]}'\nduration 0.5\n")
    log(f"[RENDER] 共 {shot_i} 帧")
    return txt


# ---------------------------------------------------------------- 4. 音轨 & 合成
def build_track(lesson):
    """把各 step 音频按时间轴混成单条音轨(块内先英后中), 返回 (wav路径, 总时长)"""
    tracks, cursor = [], 0.0
    for slide in lesson["slides"]:
        for b in slide.get("blocks", []):
            base = cursor
            en, zh = b.get("_en", ""), b.get("_zh", "")
            pe = AUDIO / f"{cid(en, 'en')}.wav" if en else None
            pz = AUDIO / f"{cid(zh, 'zh')}.wav" if zh else None
            if pe and pe.exists() and b.get("_den", 0) > 0.05:
                tracks.append((pe, base))
            if pz and pz.exists() and b.get("_dzh", 0) > 0.05:
                tracks.append((pz, base + b.get("_den", 0) + LINK_GAP))
            cursor += b["_dur"]

    total = cursor
    if not tracks:
        sil = AUDIO / "_sil.wav"
        subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-f", "lavfi",
                        "-i", f"anullsrc=r=44100:cl=mono", "-t", str(total + 1),
                        str(sil)], check=True)
        return sil, total + 1

    out = AUDIO / "_track.wav"
    args = [FFMPEG, "-y", "-loglevel", "error"]
    for p, _ in tracks:
        args += ["-i", str(p)]
    fc = [f"[{i}]adelay={int(round(off * 1000))}|{int(round(off * 1000))}[a{i}]"
          for i, (p, off) in enumerate(tracks)]
    fc.append("".join(f"[a{i}]" for i in range(len(tracks))) +
              f"amix=inputs={len(tracks)}:duration=longest:normalize=0[mix]")
    fc.append(f"[mix]alimiter=limit=0.94,apad=whole_dur={total + 1:.3f}[out]")
    args += ["-filter_complex", ";".join(fc), "-map", "[out]",
             "-ar", "44100", "-ac", "1", str(out)]
    subprocess.run(args, check=True)
    return out, total + 1


def mux(frames_txt, audio_wav, out_path, total):
    subprocess.run([
        FFMPEG, "-y", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", str(frames_txt),
        "-i", str(audio_wav),
        "-fps_mode", "passthrough",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-pix_fmt", "yuv420p", "-profile:v", "high",
        "-c:a", "aac", "-b:a", "160k", "-ar", "44100",
        "-movflags", "+faststart", "-t", f"{total:.3f}", str(out_path)
    ], check=True)


# ---------------------------------------------------------------- main
async def amain(lesson_file):
    lesson = json.loads(Path(lesson_file).read_text(encoding="utf-8"))
    # 短文三遍: 纯英文 / 双语 / 盲听
    lesson["slides"] = expand_passes(lesson)
    for si, s in enumerate(lesson["slides"]):
        s["_name"] = s.get("name", f"slide{si}")
    log(f"=== {lesson['meta']['lesson']} · {lesson['meta']['scene']} ===")
    await build_audio(lesson)
    log(f"总时长 ≈ {sum(b['_dur'] for s in lesson['slides'] for b in s['blocks']):.1f}s")

    # 版面: 先实测每页高度, 再决定要不要拆页
    html = build_html(lesson, "measure.html")
    lesson["slides"] = paginate(lesson, measure_pages(html))
    log(f"[PAGE] 共 {len(lesson['slides'])} 页")
    html = build_html(lesson)
    frames_txt = render_frames(html, lesson)

    log("[AUDIO] 合成音轨 ...")
    track, total = build_track(lesson)

    OUT.mkdir(parents=True, exist_ok=True)
    name = f"{lesson['meta']['id']}_{lesson['meta']['scene']}"
    outp = OUT / f"{name}.mp4"
    log("[MUX] 合成视频 ...")
    mux(frames_txt, track, outp, total)
    log(f"✅ {outp}  ({total:.1f}s)")

    # 封面
    cover = FRAMES / "cover.png"
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", str(outp),
                    "-ss", "00:00:02", "-frames:v", "1", str(cover)], check=False)
    return outp


if __name__ == "__main__":
    import traceback
    try:
        asyncio.run(amain(sys.argv[1] if len(sys.argv) > 1 else "lessons/01.json"))
    except SystemExit:
        raise
    except BaseException as e:
        log(f"\n[ERROR] {type(e).__name__}: {e}")
        traceback.print_exc()
        sys.exit(1)