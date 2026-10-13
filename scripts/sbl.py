#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""场景化学习课件 · 统一入口

用法(在课程项目目录下执行, 项目结构见 references/lesson-schema.md):
  python3 <SKILL>/scripts/sbl.py lessons/01.json --stage check   # 版面自检(不合成语音)
  python3 <SKILL>/scripts/sbl.py lessons/01.json --stage render  # 出讲解视频(慢, 需 TTS)
  python3 <SKILL>/scripts/sbl.py lessons/01.json --stage pdf     # A4 资料卡片 PDF
  python3 <SKILL>/scripts/sbl.py lessons/01.json --stage cover   # 3:4 / 4:3 封面图
  python3 <SKILL>/scripts/sbl.py lessons/01.json --stage page    # 交互学习页 HTML
  python3 <SKILL>/scripts/sbl.py lessons/01.json --stage all     # check + 全部产物

说明: --stage all 不含 render(视频最慢), 需要视频时单独跑 render。
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("SBL_ROOT") or Path.cwd()).resolve()

STAGES = {
    "check": ["layout_check.py"],
    "render": ["render.py"],
    "pdf": ["make_pdf.py"],
    "cover": ["make_cover.py"],
    "page": ["make_page.py"],
}
ALL = ["check", "pdf", "cover", "page"]


def run(stage, lesson):
    script = STAGES[stage][0]
    cmd = [sys.executable, str(SCRIPT_DIR / script), lesson]
    print(f"\n=== [{stage}] {script} {lesson} ===", flush=True)
    env = dict(os.environ)
    env["SBL_ROOT"] = str(ROOT)
    r = subprocess.run(cmd, cwd=str(ROOT), env=env)
    if r.returncode != 0:
        raise SystemExit(f"[{stage}] 失败 (exit {r.returncode})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("lesson", nargs="?", default="lessons/01.json")
    ap.add_argument("--stage", default="all",
                    choices=list(STAGES) + ["all"])
    a = ap.parse_args()
    todo = ALL if a.stage == "all" else [a.stage]
    for s in todo:
        run(s, a.lesson)
    print(f"\n完成: {', '.join(todo)}   (项目根目录 {ROOT})")


if __name__ == "__main__":
    main()
