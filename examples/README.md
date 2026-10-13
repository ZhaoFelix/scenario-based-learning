# 实例：第 01 课「机场入境与通关」

`assets/lesson.example.json` 就是这一课的完整内容，可以作为新课的模板直接改。
配套文件（易错点 / 文化 / 实战 / 复习）在 `examples/`。

## 复现步骤

```bash
# 1. 建项目
mkdir -p my-english/lessons my-english/assets && cd my-english
cp <SKILL>/assets/lesson.example.json lessons/01.json
cp <SKILL>/examples/01_*.json lessons/

# 2. 生成配图（交给 ImageGen，提示词必须强调「无任何文字/字母」）
#    assets/01_passage.png   1024x1536  短文插画
#    assets/01_cover_v.png   1024x1536  封面底图（上 1/4 留空）
#    assets/01_cover_h.png   1536x1024  封面底图（左 2/3 留空、主体在右）

# 3. 版面自检 → 全部产物
python3 <SKILL>/scripts/sbl.py lessons/01.json --stage check
python3 <SKILL>/scripts/sbl.py lessons/01.json --stage pdf
python3 <SKILL>/scripts/sbl.py lessons/01.json --stage cover

# 4. 视频（最慢，需要 MIMO_API_KEY；前台跑）
python3 <SKILL>/scripts/sbl.py lessons/01.json --stage render

# 5. 学习页
python3 <SKILL>/scripts/sbl.py lessons/01.json --stage page
```

## 实测产出（第 01 课）

| 产物 | 规格 |
|---|---|
| `out/01_机场入境与通关.mp4` | 7 分 02 秒 / 10.4 MB / 1920×1080 / 25fps / 9 页 |
| `out/01_机场入境与通关_资料卡片.pdf` | A4 竖版 6 页（封面/词汇/口语/短文对照/三遍听法/口袋卡） |
| `out/01_封面_3x4.png` | 1080×1440 |
| `out/01_封面_4x3.png` | 1440×1080 |
| `out/01_机场入境与通关_学习页.html` | 交互页，5 栏，0 JS 错误 |
| 分享文案 | 抖音 + 小红书，见 `assets/share-copy.template.md` |

## 内容设计回顾（为什么这么写）

- 词汇 10 个里只要求 4 个能说出口（purpose / visit / stay / declare），其余听懂即可——
  降低开口压力，这是场景化学习能不能坚持下来的关键。
- 短文把 10 个词全部嵌进去，且按真实对话轮次排列，等于让学员在"完整场景"里再遇一次全部生词。
- 三遍听法（纯英文 → 双语 → 盲听）对应三种加工深度，最后一遍不看书能听懂才算过。
- 口袋卡只留 5 组问答，答句都是"一个词或一个短语"——真实海关场景里，答得短才不出错。
