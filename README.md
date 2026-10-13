# 场景化学习课件工坊 · Scenario-Based Learning Studio

> **一个场景 → 一整套课件。** 给一个生活/工作场景，产出讲解视频、可打印资料卡片、
> 吸睛封面图、平台发布文案与交互学习页——一次生成，学、练、发全齐。

![icon](./_icon.png)

## 产物一览

| 产物 | 规格 | 典型用途 |
|------|------|----------|
| 🎬 讲解视频 | 1920×1080 · 25fps · 6-8 分钟 | 学习、发抖音/B站/西瓜 |
| 🗂 资料卡片 PDF | A4 竖版 6 页，打印即用 | 复习、小红书图文素材 |
| 🖼 封面图 ×2 | 3:4（1080×1440）+ 4:3（1440×1080） | 竖版/横版平台封面 |
| ✍️ 发布文案 | 抖音 + 小红书各一份 | 复制即发 |
| 📱 交互学习页 | 五栏点读练习 HTML | 电脑/手机自学 |

**视频结构**（教学法已定版）：场景词汇（10 词）→ 场景口语（5 句）→ 场景短文（≤100 词、
含全部词汇、AI 配图，**听三遍**：纯英文跟读 → 双语对照 → 盲听）→ 今日口袋卡（5 组问答）。

## 快速开始

```bash
# 安装：整包放进技能目录
cp -r scenario-based-learning ~/.workbuddy/skills/

# 30 秒跑通
mkdir -p demo/lessons demo/assets && cd demo
cp ~/.workbuddy/skills/scenario-based-learning/assets/lesson.example.json lessons/01.json

SK=~/.workbuddy/skills/scenario-based-learning/scripts
python3 $SK/sbl.py lessons/01.json --stage all      # 自检 + PDF卡片 + 封面 + 学习页
python3 $SK/sbl.py lessons/01.json --stage render   # 出视频（需 MIMO_API_KEY）
```

> ⚠️ 短文插画与封面底图需用 ImageGen 生成到 `assets/`（提示词必须强调"无任何文字"），
> 详见 [使用说明 · 第六节](./使用说明.md#六写自己的课程)。

## 文档导航

| 文档 | 内容 |
|------|------|
| [使用说明.md](./使用说明.md) | **完整使用手册**：安装 / 依赖 / 五阶段详解 / 自定义课程 / FAQ 排障 |
| [SKILL.md](./SKILL.md) | 技能主入口（AI 读取的触发与执行规范） |
| [references/lesson-schema.md](./references/lesson-schema.md) | 课程 JSON 字段与内容写作规范 |
| [references/pipeline.md](./references/pipeline.md) | 渲染管线细节 + 踩坑清单（换机器必读） |
| [references/copywriting.md](./references/copywriting.md) | 抖音/小红书文案规范 |
| [CHANGELOG.md](./CHANGELOG.md) | 更新日志 |
| [examples/README.md](./examples/README.md) | 第 01 课「机场入境」完整复现实录 |

## 环境要求

Python 3.10+（`requests`、`imageio-ffmpeg`）· Node.js + Playwright · ffmpeg ·
MiMo API Key（语音，可回退系统 `say`）· ImageGen（配图）。详见 [使用说明 · 第三节](./使用说明.md#三前置依赖)。

## 特性

- **自动分页防重叠**：渲染前 Playwright 实测每页高度，超高自动拆页 + 等比缩放双保险
- **音频内容寻址缓存**：改几句讲解词只重合成那几条；短文三遍复用同一批音频
- **TTS 回退链**：MiMo-V2.5-TTS → edge-tts → macOS `say`，没有 Key 也能出片
- **零硬编码路径**：`SBL_ROOT` / `SBL_NODE` / `SBL_FFMPEG` 自适应，换机器开箱即用
- **数据化验收**：版面高度、音频时长、PDF 溢出全部实测，不靠"看着差不多"

## 许可

[MIT](./LICENSE) © 2026 felix
