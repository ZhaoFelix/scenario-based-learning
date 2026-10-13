# 管线与踩坑（pipeline）

## 课程项目目录约定

引擎所有路径都相对于**项目根目录**（`SBL_ROOT`，默认当前工作目录），
所以脚本可以放在技能里、数据放在项目里：

```
<课程项目>/
├── lessons/            # 课程内容（唯一的"内容层"，改这里就能加新课）
│   ├── 01.json             # 主课：词汇/口语/短文三遍/口袋卡
│   ├── 01_errors.json      # 易错点（只进学习页）
│   ├── 01_culture.json     # 文化提示（只进学习页）
│   ├── 01_role.json        # 角色扮演实战（只进学习页）
│   └── 01_review.json      # 遮罩复习（只进学习页）
├── assets/             # 配图与封面底图（ImageGen 产出）
├── build/              # 中间产物：board.html / plan.json / frames/ / audio/
└── out/                # 交付物：MP4 + PDF + 封面 PNG + 学习页 HTML + 文案
```

## 五个阶段

| stage | 脚本 | 耗时 | 产出 |
|---|---|---|---|
| check | `layout_check.py` | ~10s | 打印每页实测高度与分页结果（不合成语音） |
| render | `render.py` | 数分钟 | `out/NN_场景.mp4`（1920×1080 / 25fps / 6-8 分钟） |
| pdf | `make_pdf.py` | ~30s | `out/NN_场景_资料卡片.pdf`（A4 六页） |
| cover | `make_cover.py` | ~20s | `out/NN_封面_3x4.png` + `out/NN_封面_4x3.png` |
| page | `make_page.py` | ~5s | `out/NN_场景_学习页.html`（交互，非必需交付物） |

统一入口：`python3 <SKILL>/scripts/sbl.py lessons/01.json --stage all`
（`all` = check+pdf+cover+page；`render` 单独跑，因为最慢）

## 视频是怎么出来的

```
lesson.json
  └─ expand_passes()   短文页 passes:["en","bi","blind"] → 展开成三页
  └─ build_audio()     每个块的 say(英) / say_zh(中) → 音频文件 + 实测时长
  └─ build_html()      HTML 板书页（一次 DOM，靠 class 切换）
  └─ measure_pages()   Playwright 实测每页高度 → paginate() 自动拆页
  └─ render_frames()   生成 plan.json → shot.js 逐帧截图（写实 reveal 动画定格）
  └─ build_track()     按时间轴 adelay + amix 混成单条音轨（块内先英后中）
  └─ mux()             ffmpeg concat 帧序列 + 音轨 → MP4
```

**为什么先合成音频再排版/渲染**：块的展示时长 = 该块音频实际时长，
所以必须先有语音时长，否则画面与讲解必然错位。

**分页**：`measure.js` 把每页单独置为 live、强制显示所有 reveal 块，量出"写满时"的
真实高度；`paginate()` 按行贪心装箱，超高自动拆页（续页右上角显示「续」）；
`GAP` 表必须与 CSS 里的 `gap` 保持一致，改 CSS 记得同步改表。
另有整页 `transform:scale()` 兜底，任何情况下都不会与页眉重叠。

**短文三遍**：第一遍纯英文（`.mode-en` 隐藏中文）→ 第二遍双语（`.mode-bi`）→
第三遍盲听（`layout:"blind"`，只显图+徽章，整段一次性朗读）。
三遍复用同一批音频（缓存按文本内容寻址），不重复计费。

## TTS 后端

| 优先级 | 后端 | 说明 |
|---|---|---|
| 1 | MiMo-V2.5-TTS | OpenAI 兼容接口；**待朗读文本必须放 `assistant` 角色**，导演指令放 `user` 角色；en=Chloe，zh=冰糖；返回 24kHz WAV base64 |
| 2 | edge-tts | 微软接口，已被 403 封过，只作回退 |
| 3 | macOS `say` | 离线兜底，英文 Samantha(160wpm)、中文 Tingting(180wpm) |

API key 走环境变量 `MIMO_API_KEY` 或 `~/.workbuddy/mimo_api_key`（权限 600），**不要落盘到项目里**。

音频缓存键 = `md5(后端 | 导演指令指纹 | 文本内容 | 语种)` —— 改讲解词只重合成改动的那几条，
改语速/风格会整体失效（这是故意的，避免新旧语速混用）。

同一块内的播放顺序是**先英文、间隔 0.45s、再中文讲解**（`LINK_GAP`）。
早期版本用 amix 并行混音，结果中英文同时说话，听不清——必须保持串行。

## 踩坑清单（换机器必看）

| 现象 | 原因 | 处置 |
|---|---|---|
| `unsupported invocation` + exit 127 | `/opt/homebrew/bin/ffmpeg` 是只支持 PNG 的伪 wrapper | 用 `imageio_ffmpeg.get_ffmpeg_exe()` 或 `SBL_FFMPEG` 指定 |
| 读不出媒体时长 | 环境里没有 ffprobe | 解析 `ffmpeg -i file` 的 stderr 里 `Duration: HH:MM:SS.xx`（不是 `time=`） |
| `One of -r/-fpsmax was specified together a non-CFR -vsync` | ffmpeg 7.x 不允许 `-vsync` 与 `-r` 同用 | 变帧率拼接改用 `-fps_mode passthrough` |
| 批量删除/`unlink` 被拦，退出码非 0 | 沙箱有删除配额 | **不要删帧**：帧名固定（`f00000.png…`）直接覆盖写；TTS 临时文件走 stdin 管道（`-i pipe:0`）零落盘 |
| 长后台任务莫名被杀 | 沙箱会 SIGKILL 长时后台进程 | 渲染这类长任务前台跑，或按 stage 分次跑 |
| `require('playwright')` 失败 | 没设 `NODE_PATH` | 引擎会自动探测托管 node_modules；也可显式设 `NODE_PATH` / `SBL_NODE` |
| 视频里中英混着说 | amix 并行播放 | 改串行：英文 → gap → 中文（已内置） |
| 中文讲解语速慢 | TTS 语速参数不稳定 | 用 ffmpeg `atempo=1.18` 后期加速（不改音高），见 `ZH_TEMPO` |

环境变量速查：`SBL_ROOT`（项目根）、`SBL_NODE`（node 路径）、`SBL_FFMPEG`（ffmpeg 路径）、
`MIMO_API_KEY`、`NODE_PATH`。

## 质量红线（必须用数据验收，不能靠感觉）

1. **无重叠**：`layout_check.py` 每页 `实测 ≤ 可用`；渲染后抽查 6-8 个时间点帧。
2. **无静音错位**：`render.py` 打印总时长，与视频实际时长比对（`ffprobe_dur`）。
3. **短文三遍都在**：三页内容分别为「只有英文」「英+中」「只有图」。
4. **PDF 无溢出**：逐页 `element screenshot` + `scrollHeight > 页面高度` 检测。
5. **封面不压主体、水印被盖住**：逐张看图确认。
