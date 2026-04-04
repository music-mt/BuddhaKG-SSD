"""
kg/gen_hidden_edges.py — 隱性邊生成（包裝 BuddhaNLP gen_hidden_edges.py）

用法：
    python kg/gen_hidden_edges.py
    python kg/gen_hidden_edges.py --top 100
"""

import argparse
import logging
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

ORIGINAL = Path(r"C:\buddha\gen_hidden_edges.py")


def main():
    parser = argparse.ArgumentParser(description="隱性邊生成")
    parser.add_argument("--top", type=int, default=100, help="取前 N 條候選")
    args = parser.parse_args()

    log.info(f"=== 隱性邊生成（top {args.top}）===")

    env = dict(os.environ)
    env["NEO4J_PASS"] = config.NEO4J_PASS

    cmd = [sys.executable, str(ORIGINAL)]
    log.info(f"  執行：{' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(ORIGINAL.parent), env=env)

    if result.returncode == 0:
        log.info("✅ 隱性邊生成完成")
    else:
        log.error("❌ 生成失敗")


if __name__ == "__main__":
    main()
