# 课程 JSON schema

主课文件 `lessons/NN.json` 是整套产物的唯一内容源：视频、PDF 卡片、学习页都读它。
完整可运行范例：`assets/lesson.example.json`（第 01 课 · 机场入境与通关）。

## 顶层结构

```json
{
  "meta": {
    "id": "01", "lesson": "01", "series": "美国生活英语",
    "scene": "机场入境与通关", "scene_en": "Airport Immigration & Customs", "day": 1,
    "cover": {
      "img_v": "assets/01_cover_v.png",
      "img_h": "assets/01_cover_h.png",
      "big1": "入境美国", "big2": "只用这 5 句", "sub": "海关问答 · 背完直接过"
    }
  },
  "slides": [ ... ]
}
```

- `id` 用于产物文件名前缀（`01_机场入境与通关.mp4`）。
- `cover` 只给封面图用；`big2` 里的数字会被自动加黄块强调。

## 页（slide）

```json
{ "name": "一、场景词汇", "layout": "vocab", "blocks": [...] }
```

| layout | 用途 | 布局要点 |
|---|---|---|
| `cover` | 封面页 | 居中大标题 |
| `vocab` | 词汇页 | 两列网格，10 个词一屏 |
| `stack` | 默认竖排 | 口语、回顾页 |
| `passage` | 短文页 | 左文右图，需 `image` + `image_caption` |
| `blind` | 盲听页 | 只图 + 徽章，无正文（由 `expand_passes` 自动生成） |

短文页额外写 `"passes": ["en","bi","blind"]`，引擎自动展开成三遍听法的三页
（纯英文 / 双语 / 盲听）。**展开后的英文文本相同，音频按内容去重只合成一次。**

## 块（block）类型

| type | 字段 | 说明 |
|---|---|---|
| `sub` | text | 小标（PART 1 · …） |
| `h` | text | 大标题 |
| `en` | text | 英文行，支持 `==高亮==` |
| `zh` | text | 中文行，支持 `**强调**` |
| `vocab` | w / ph / pos / cn / eg | 词汇卡：词、音标、词性、中文、例句 |
| `phrase` | en / cn / tip | 口语句卡 |
| `line` | who / text / cn | 短文句；`who` = 旁白 / OFFICER / YOU |
| `kv` | text | 口袋卡问答，用 `→` 分隔问与答 |
| `tip` | ic / text | 提示条（emoji + 文字） |
| `err` | bad / good / why | 易错点（**只在学习页**，不进视频/PDF） |
| `flow` | items[{t,d}] | 流程步骤 |

块通用字段：

- `batch`：同 `batch` 的块同时出现（默认按块序号逐个出现）。
- `wide`：在 `vocab` 网格里独占一行。
- `say`：**英文**朗读文本（TTS 用）。
- `say_zh`：**中文讲解**文本；纯翻译型的块（line/kv）不要写 `say_zh`，否则视频里会中英混说。

行内标记：`==文字==` → 荧光黄高亮（标出当天学的词）；`**文字**` → 加粗强调。

## 配套文件（只进学习页，不进视频/PDF）

```
lessons/NN_errors.json   [{"bad":"I am engineer.","good":"I'm a software engineer.","why":"..."}]
lessons/NN_culture.json  [{"ic":"🤐","tx":"**海关只问不聊。** 回答越短越好。"}]
lessons/NN_role.json     角色扮演实战（多轮对话）
lessons/NN_review.json   [{"i":1,"q":"默写：What's the ___ of your visit?","a":"..."}]
```

## 内容写作规范（关键）

1. **词汇 10 个**：必须覆盖场景最常出现的词；其中 4 个标为"必须能说出口"，其余"听懂即可"。
2. **口语 5 句**：就是对方最可能问的 5 个问题 + 最自然的一句应答；tip 写"答什么、怎么答、别答什么"。
3. **短文 ≤100 词**：**必须包含第一部分的全部 10 个词汇**，用 `==` 标出来；
   逐句逐轮（旁白 → OFFICER → YOU → …），最后一句收尾要有画面感。
4. **口袋卡 5 组**：一问一答，答案要短（一个词或一个短语最好）；最后加一条"今天立刻能做的动作"。
5. **易错点**：针对中国学习者典型错误（漏冠词、be+动词原形、疑问句语序、中式介词、名词顺序）。
6. **中文讲解**：口语化、有画面感，每条 ≤25 字，不要学术腔。
7. 每课的英文难度遵循 i+1：比上一课略高一点，但每个新结构都要在短文里复现。
