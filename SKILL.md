---
name: scenario-based-learning
display_name: 场景化学习课件工坊
display_name_en: Scenario-Based Learning Studio
description: "场景化学习（scenario-based learning）课件全流程工厂——给定一个生活/工作场景，产出 10 分钟讲解视频、A4 资料卡片 PDF、3:4 与 4:3 吸睛封面图、抖音/小红书发布文案、可交互学习页。适用于「场景化学习」「做一个英语场景课」「场景学习课件」「把某个场景做成学习视频」「学习资料卡片导出 PDF」「课程封面图」，以及任何『场景 → 课件 + 卡片 + 文案』的需求。内置视频引擎（自动分页防重叠）、MiMo 语音、卡片排版与封面模板。"
description_zh: "把一个生活场景一键做成场景化学习课件：讲解视频（词汇/口语/短文三遍听法）+ A4 资料卡片 PDF + 横竖版封面图 + 抖音小红书文案 + 交互学习页。"
description_en: "Build scenario-based learning courseware from a single scenario: narrated video, printable A4 study-card PDF, 3:4 and 4:3 covers, Douyin/Xiaohongshu copy, and an interactive study page."
version: 1.0.0
author: felix
license: MIT
categories: [education, content-creation, video]
tags: [英语学习, 场景化学习, 课程视频, 资料卡片, 封面图, 自媒体文案]
---

# scenario-based-learning · 场景化学习课件工坊

给**一个场景**，产出**一整套可学、可发、可印的课件**：

| 产物 | 说明 |
|---|---|
| 讲解视频 | 1920×1080，6-8 分钟。场景词汇 → 场景口语 → 场景短文（三遍听法）→ 今日口袋卡 |
| 资料卡片 PDF | A4 六页：封面卡 / 词汇卡 / 口语卡 / 短文对照卡 / 三遍听法卡 / 口袋卡 |
| 封面图 | 3:4（1080×1440）与 4:3（1440×1080），大字少字、AI 底图 |
| 发布文案 | 抖音（封面文案/标题/口播脚本/标签）+ 小红书（标题/正文/标签） |
| 学习页 HTML | 交互版，含实战、易错点、文化提示、遮罩复习（非必需交付物） |

## 快速上手

```bash
# 0. 先建课程项目（内容放 lessons/，图放 assets/）
mkdir -p <项目>/lessons <项目>/assets && cd <项目>
cp <SKILL>/assets/lesson.example.json lessons/01.json     # 这是可直接改的范本

# 1. 版面自检（不合成语音，只验分页，先跑这个）
python3 <SKILL>/scripts/sbl.py lessons/01.json --stage check

# 2. 出视频（最慢，需要 MIMO_API_KEY；必须前台跑）
python3 <SKILL>/scripts/sbl.py lessons/01.json --stage render

# 3. 出 PDF 卡片 / 封面 / 学习页
python3 <SKILL>/scripts/sbl.py lessons/01.json --stage pdf
python3 <SKILL>/scripts/sbl.py lessons/01.json --stage cover
python3 <SKILL>/scripts/sbl.py lessons/01.json --stage page
```

配图由你调用 ImageGen 生成（技能本身不出图）：短文插画、封面竖底图、封面横底图，
提示词里**必须强调"无任何文字/字母"**。详见 `examples/README.md`。

## 何时用

用户说：场景化学习 / scenario-based learning / 做一个 XX 场景的课 / 场景学习课件 /
把某个场景做成视频 / 学习卡片导出 PDF / 课件封面图 / 抖音小红书发课件文案。
**只要涉及"一个场景 → 课件全家桶"，就用本技能**，不要临时手写 ffmpeg 或散着拼。

## 核心理念

1. **一个场景 = 四层加工**：认词（输入）→ 会答（产出）→ 整段听懂（综合）→ 口袋卡（复习）。
   每层都比上一层加工更深，学员一路走完就是"从看懂到能开口"。
2. **短句优先、答案要短**：词汇只要求 4 个能说出口，口袋卡答案尽量一个词。
   开口压力越小，越可能坚持下去。
3. **短文必须复用全部词汇**：在真实对话里第二次遇到当天生词，比多做十道练习题有效。
4. **短文听三遍**：纯英文（跟读）→ 双语（确认）→ 盲听（不看字听懂），三遍到齐才算过。
5. **一切靠数据验收**：有没有重叠、有没有静音错位、PDF 有没有溢出——都要实测，
   不能"看着差不多"。

## 前置依赖

| 依赖 | 说明 |
|---|---|
| Python | 需 `requests` `imageio-ffmpeg`（缺了用清华源装）；建议固定用同一个解释器 |
| Node.js + Playwright(已装 playwright) | 逐帧截图 / 版面测量 / PDF 打印 / 封面截图 |
| ffmpeg | 真 ffmpeg（自动定位，可用 `SBL_FFMPEG` 指定）；**没有 ffprobe** 也能跑 |
| MiMo API Key | `MIMO_API_KEY` 或 `~/.workbuddy/mimo_api_key`。**不要写进任何项目文件** |
| ImageGen | 短文插画 + 封面底图 |

环境变量：`SBL_ROOT`（项目根，默认 cwd）、`SBL_NODE`、`SBL_FFMPEG`、`NODE_PATH`。

## 内容设计规范（写 JSON 前先读）

词汇 10 个 / 口语 5 句 / 短文 ≤100 词且含全部词汇 / 口袋卡 5 组问答 + 一个立刻能做的动作。
块类型、字段、行内高亮标记、配套文件（易错点/文化/实战/复习）：
→ `references/lesson-schema.md`

## 质量红线

1. `layout_check.py` 每页实测高度 ≤ 可用高度（引擎会自动分页 + 缩放兜底）。
2. 渲染后抽查 6-8 个时间点的帧，确认无重叠、无空页。
3. 视频总时长与音频时间轴一致（`render.py` 打印的时长 = 成品时长），6-8 分钟。
4. PDF 逐页检测 `scrollHeight` 不溢出；封面逐张看图，确认文字不压主体、水印被盖住。
5. 文案里出现的每句英文都能在课程 JSON 里找到（不许编）。

## 参考文件

- `references/pipeline.md` —— 管线全貌、TTS 后端、踩坑清单（换机器必读）
- `references/lesson-schema.md` —— 课程 JSON schema 与内容写作规范
- `references/copywriting.md` —— 抖音/小红书文案规范与自检清单
- `assets/lesson.example.json` —— 可直接改的课程范本（第 01 课）
- `assets/share-copy.template.md` —— 分享文案样张
- `examples/README.md` —— 完整复现步骤与实测产出
