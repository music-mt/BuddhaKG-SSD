"""
ssd/embed_usage.py — Usage 嵌入（包裝 BuddhaSSD embed_usage.py）

用法：
    python ssd/embed_usage.py
"""

import logging
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

ORIGINAL = Path(r"C:\buddhassd\embed_usage.py")


def main():
    log.info("=== Usage 嵌入 ===")
    cmd = [sys.executable, str(ORIGINAL)]
    log.info(f"  執行：{' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(ORIGINAL.parent))
    if result.returncode == 0:
        log.info("✅ 嵌入完成")
    else:
        log.error("❌ 嵌入失敗")


if __name__ == "__main__":
    main()
